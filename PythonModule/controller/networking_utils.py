import struct
import numpy as np
from types import SimpleNamespace
import warnings
import math
import pandas as pd
import socket
from typing import Optional

class Utilities:
    def __init__(self):
        pass

    def simpleDecodeiMBlocksDoubleMessage(self, msg):
        try:
            format_string = '<' + (int(len(msg) / 8) * 'd')
            unpacked_data = struct.unpack(format_string, msg)
            #print(unpacked_data)
            return SimpleNamespace(
                candle_mode=1,
                motor_no=0,
                values=unpacked_data
            )        
        
        except Exception as e:
            print(f"Decoding error: {e}")
            return None
    
    def simpleDecodeiMBlocksFloatMessage(self, msg):
        try:
            format_string = '<' + (int(len(msg) / 4) * 'f')
            unpacked_data = struct.unpack(format_string, msg)
            return SimpleNamespace(
                candle_mode=1,
                motor_no=0,
                values=unpacked_data
            )        

        except Exception as e:
            print(f"Decoding error: {e}")
            return None

    def handleBroadcastValues(self, address, port, *args):
        values = [val for val in args]

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        data = struct.pack(f'<{len(values)}d', *values) # Little-endian Double-Werte
        try:
            udp_socket.sendto(data, (address, port))
        finally:
            udp_socket.close()

    def handleBroadcastCurrentAngle(self, address, ui_port, imblocks_port, *args):
        values = [val for val in args]

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        data = struct.pack(f'<{len(values)}d', *values) # Little-endian Double-Werte
        try:
            udp_socket.sendto(data, (address, ui_port))
            udp_socket.sendto(data, (address, imblocks_port))
        finally:
            udp_socket.close()

    def processIMUs(self, IMU_message):
        return IMU_message.values[0:4], IMU_message.values[4:8]

    def handle_process_sensors(
            self, 
            motor_controller, 
            myo_message, 
            current_avg_emg,
            ext_table, 
            flex_table, 
            iso_table,
            current_angle, 
            max_torque_extension, 
            max_torque_flexion, 
            base_torque, 
            min_torque_extension, 
            min_torque_flexion, 
            max_kp_iso, 
            max_kd_iso,
            kp_min,
            kd_min,
            max_ext_angle, 
            max_flex_angle, 
            extendingMotorNo, 
            flexingMotorNo, 
            k, 
            non_linear_center_ext,
            non_linear_center_flex,
            non_linear_center_iso,
            filt_tau_ext, 
            filt_tau_flex, 
            alpha,
            min_rel_emg_ext,
            min_rel_emg_flex,
            min_confidence,
            min_confidence_dif
            ):
        torque_ext_motor = motor_controller.get_motor_status(extendingMotorNo)["torque"]
        torque_flex_motor = motor_controller.get_motor_status(flexingMotorNo)["torque"]
        mov = self.classify_mov(min_confidence, min_confidence_dif, myo_message)
        #print(mov)
        if mov == "isometric":
            if torque_ext_motor < min_torque_extension or torque_flex_motor < min_torque_flexion:
                filt_tau_ext = self.apply_IIR_filter(min_torque_extension, filt_tau_ext, base_torque, alpha)
                filt_tau_flex = self.apply_IIR_filter(min_torque_flexion, filt_tau_flex, base_torque, alpha)
                return "isometric", filt_tau_ext, filt_tau_flex, 0, 0
            kp_iso, kd_iso = self.isometric(current_avg_emg, iso_table, current_angle, max_flex_angle, max_ext_angle, max_kp_iso, max_kd_iso, non_linear_center_iso)
            return mov, filt_tau_ext, filt_tau_flex, kp_iso, kd_iso, kp_iso, kd_iso

        elif mov == "extension":
            target_tau_ext = self.extension(current_avg_emg, ext_table, current_angle, max_flex_angle, max_ext_angle, max_torque_extension, min_torque_extension, non_linear_center_ext, min_rel_emg_ext)
            filt_tau_ext = self.apply_IIR_filter(target_tau_ext, filt_tau_ext, base_torque, alpha)
            filt_tau_flex = base_torque
            return mov, filt_tau_ext, filt_tau_flex, 0, kd_min, 0, 0

        elif mov == "flexion":
            target_tau_flex = self.flexion(current_avg_emg, flex_table, current_angle, max_flex_angle, max_ext_angle, max_torque_flexion, min_torque_flexion, non_linear_center_flex, min_rel_emg_flex)
            filt_tau_flex = self.apply_IIR_filter(target_tau_flex, filt_tau_flex, base_torque, alpha)
            filt_tau_ext = base_torque
            return mov, filt_tau_ext, filt_tau_flex, 0, 0, 0, kd_min

        else:
            mov = "rest"
            filt_tau_rest_ext = self.apply_IIR_filter(base_torque, filt_tau_ext, base_torque, alpha)
            filt_tau_rest_flex = self.apply_IIR_filter(base_torque, filt_tau_flex, base_torque, alpha)
            return mov, filt_tau_rest_ext, filt_tau_rest_flex, 0, 0, 0, 0

    def isometric(self, current_avg_emg, iso_table, current_angle, max_flex_angle, max_ext_angle, max_kp, max_kd, non_linear_center):
        try: 
            a = current_avg_emg /iso_table[current_angle+max_flex_angle]
            kp = self.nonlinear(a, max_kp, non_linear_center, 0)
            kd = self.nonlinear(a, max_kd, non_linear_center, 0)            
        except: 
            warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
            kp = 0
            kd = 0
        return kp, kd

    # def extension(self, current_avg_emg, ext_table, current_angle, max_flex_angle, max_ext_angle, max_torque_extension, min_torque_extension, k, min_rel_emg_ext):
    #     try: 
    #         a = current_avg_emg / ext_table[current_angle+abs(max_flex_angle)]
    #         if a < min_rel_emg_ext:
    #             target_tau_ext = min_torque_extension
    #         else: 
    #             target_tau_ext = self.nonlinear_torque(a, min_rel_emg_ext, max_torque_extension, min_torque_extension, k=k)#
    #     except:
    #         warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
    #         target_tau_ext = min_torque_extension
    #     return target_tau_ext
    
    def extension(self, current_avg_emg, ext_table, current_angle, max_flex_angle, max_ext_angle, max_torque_extension, min_torque_extension, non_linear_center, min_rel_emg_ext):
        try: 
            a = current_avg_emg / ext_table[current_angle+abs(max_flex_angle)] 
            #print(a)
            if a < min_rel_emg_ext:
                return min_torque_extension           
        except:
            warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
            return min_torque_extension  
        return self.nonlinear_torque(a, min_rel_emg_ext, max_torque_extension, non_linear_center, min_torque_extension)

    # def flexion(self, current_avg_emg, flex_table, current_angle, max_flex_angle, max_ext_angle, max_torque_flexion, min_torque_flexion, k, min_rel_emg_flex):
    #     try: 
    #         a = current_avg_emg / flex_table[current_angle+abs(max_flex_angle)]
    #         if a < min_rel_emg_flex:
    #             target_tau_flex = min_torque_flexion
    #         else: 
    #             target_tau_flex = self.nonlinear_torque(a, min_rel_emg_flex, max_torque_flexion, min_torque_flexion, k=k)
    #     except:
    #         warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
    #         target_tau_flex = min_torque_flexion
    #     return target_tau_flex

    def flexion(self, current_avg_emg, flex_table, current_angle, max_flex_angle, max_ext_angle, max_torque_flexion, min_torque_flexion, non_linear_center, min_rel_emg_flex):
        try: 
            a = current_avg_emg / flex_table[current_angle+abs(max_flex_angle)]
            #print(a)
            if a < min_rel_emg_flex:
                return min_torque_flexion
        except:
            warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
            return min_torque_flexion        
        return self.nonlinear_torque(a, min_rel_emg_flex, max_torque_flexion, non_linear_center, min_torque_flexion)

    def classify_mov(self, min_confidence, min_confidence_dif, myo_message):
        exp_values = np.exp(myo_message.values)
        softmax_values = list(exp_values/np.sum(exp_values))
        sorted_softmax = sorted(softmax_values, reverse=True)
        arg_max = sorted_softmax[0]
        dif = arg_max - sorted_softmax[1]
        index = softmax_values.index(arg_max)        
        string = (f"iso: {softmax_values[0]}, ext: {softmax_values[1]}, flex: {softmax_values[2]}, rest: {softmax_values[3]}")
        if arg_max > min_confidence and dif > min_confidence_dif:
            match index:
                case 0:
                    #print(string, "isometric")
                    return "isometric"
                case 1:
                    #print(string, "extension")
                    return "extension"
                case 2:
                    #print(string, "flexion")
                    return "flexion"
                case _:
                    #print(string, "rest")
                    return "rest"    
        else:
            #print(string, "rest")
            return "rest"

    def nonlinear_torque(self, a, a_min, tau_max, non_linear_center=0.5, tau_min=0.0):
        """
        Logistic-based torque mapping:
        - a: relative EMG (normalized to [0, 1])
        """
        if a_min >= non_linear_center:
            raise ValueError("a_min must be less than non_linear_center to ensure a valid logistic ramp-up.")
        
        a = np.clip(a, 0, 1)
        k = -1/(a_min-non_linear_center) * math.log((tau_max/tau_min)-1)
        # Logistic curve centered at non_linear_center
        f = 1.0 / (1.0 + np.exp(-k * (a - non_linear_center)))
        return tau_max * f

    # def nonlinear_torque(self, a, a_min, tau_max, tau_kick, k=4):
    #     """
    #     k = 1 → gently convex
    #     k = 3 → mid-range boost
    #     k = 6 → rapidly rising near a=0.7, minimal output for small efforts
    #     (check Geogebra visualization)
    #     """
    #     # Ensure a is clipped to [0, 1]
    #     a = np.clip(a, 0, 1)
    #     a_dot = (a - a_min)/(1 - a_min)
    #     # Exponential nonlinearity
    #     f = ((np.exp(k * a_dot)-1)/(np.exp(k) - 1))
    #     # f = (np.exp(k * a) - 1) / (np.exp(k) - 1)
    #     return tau_kick + (tau_max - tau_kick) * f
    
    # def nonlinear(self, a, x_max, x_kick, k=4):
    #     """
    #     k = 1 → gently convex
    #     k = 3 → mid-range boost
    #     k = 6 → rapidly rising near a=0.7, minimal output for small efforts
    #     (check Geogebra visualization)
    #     """
    #     # Ensure a is clipped to [0, 1]
    #     a = np.clip(a, 0, 1)
    #     # Exponential nonlinearity
    #     f = (np.exp(k * a) - 1) / (np.exp(k) - 1)
    #     return x_kick + x_max * f

    def nonlinear(self, a, outp_max, non_linear_center=0.5, outp_min=0.0):
        """
        Logistic-based torque mapping:
        - a: relative EMG (normalized to [0, 1])
        """
        a = np.clip(a, 0, 1)
        k = 1/(non_linear_center) * math.log((outp_max/outp_min)-1)
        # Logistic curve centered at non_linear_center
        f = 1.0 / (1.0 + np.exp(-k * (a - non_linear_center)))
        return outp_max * f

    def apply_IIR_filter(self, target_value, filtered_value, floor, alpha=0.1):
        filtered_value = alpha * target_value + (1-alpha) * filtered_value
        # print(filtered_value)
        return max(filtered_value, floor)

    def normalize_quat(q):
        """Normalize a quaternion to unit length."""
        w, x, y, z = map(float, q)
        n = math.hypot(w, x, y, z)
        if n == 0:
            raise ValueError("Zero-norm quaternion")
        return (w/n, x/n, y/n, z/n)

    def quat_conjugate(q):
        """Return the conjugate of a unit quaternion."""
        w, x, y, z = q
        return (w, -x, -y, -z)

    def quat_multiply(q1, q2):
        """Hamilton product of two quaternions."""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return (
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        )

        # ---------- angle post-processing helpers ----------
    def wrap_180(angle_deg: float) -> float:
        """Map any angle to (-180, +180]."""
        return (angle_deg + 180.0) % 360.0 - 180.0

    def unwrap_angle(angle_deg: float, prev_deg: Optional[float]) -> float:
        """
        Continuously unwrap a stream of angles so that successive differences
        are never larger than 180° in magnitude.
        """
        if prev_deg is None:
            return angle_deg
        diff = angle_deg - prev_deg
        if diff > 180.0:
            angle_deg -= 360.0
        elif diff < -180.0:
            angle_deg += 360.0
        return angle_deg

    # ---------- main API ----------
    def signed_wrist_tilt(
        self,
        q_ref,
        q,
        tilt_axis="y",
        degrees=False,
        wrap=False,
        prev_unwrapped=None,
        log_all=False,
        ):
        """
        Compute signed wrist flexion (+) / extension (–) about a single local axis.
        Roll and yaw rotations do NOT affect the result.

        Parameters
        ----------
        q_ref : tuple of 4 floats (w, x, y, z)
            Reference quaternion. Will be normalized, and its scalar part forced ≥ 0.
        q : tuple of 4 floats (w, x, y, z)
            Current quaternion. Will be normalized.
        tilt_axis : 'x'/'y'/'z' or 3‐tuple of floats, default 'y'
            Local axis about which to compute signed tilt. If a string, one of
            'x', 'y', 'z' is used; otherwise a 3‐element vector is interpreted directly.
        degrees : bool, default False
            If True, return angle in degrees; otherwise, in radians.
        wrap : bool, default False
            If True, constrain output to (−180, +180] (if degrees) or (−π, +π] (if radians).
        prev_unwrapped : float or None, default None
            If provided, unwrap this angle relative to the previous value. Ignored if None.
        log_all : bool, default False
            If True, also return a DataFrame with ['w_rel', 'd'] for debugging.

        Returns
        -------
        float
            The signed tilt angle (in radians or degrees).
        (float, pandas.DataFrame)
            If log_all=True, returns (angle, DataFrame) where DataFrame has columns ['w_rel', 'd'].
        """

        # 1) Normalize reference quaternion, force scalar ≥ 0
        qr = self.normalize_quat(q_ref)
        if qr[0] < 0:
            qr = tuple(-comp for comp in qr)

        # 2) Inverse of reference quaternion
        q_ref_inv = self.quat_conjugate(qr)

        # 3) Normalize current quaternion
        qn = self.normalize_quat(q)

        # 4) Relative quaternion q_rel = q_ref_inv ⊗ qn (and normalize)
        q_rel = self.normalize_quat(self.quat_multiply(q_ref_inv, qn))
        w_rel, vx, vy, vz = q_rel

        # 5) Choose local axis
        if isinstance(tilt_axis, str):
            axis_map = {
                "x": (1.0, 0.0, 0.0),
                "y": (0.0, 1.0, 0.0),
                "z": (0.0, 0.0, 1.0),
            }
            unit_axis = axis_map[tilt_axis.lower()]
        else:
            unit_axis = tilt_axis  # expecting a 3‐element tuple

        # 6) Project vector part onto axis → d = sin(θ/2) * sign
        d = unit_axis[0] * vx + unit_axis[1] * vy + unit_axis[2] * vz

        # 7) Recover signed angle: θ = 2 * atan2(d, w_rel)
        theta = 2.0 * math.atan2(d, w_rel)

        # 8) Convert to degrees if requested
        if degrees:
            theta = math.degrees(theta)

        # 9) Optional wrap to (−π, +π] or (−180, +180]
        if wrap:
            theta = self.wrap_180(theta)

        # 10) Optional unwrap relative to prev_unwrapped
        if prev_unwrapped is not None:
            theta = self.unwrap_angle(theta, prev_unwrapped)

        # 11) If logging, return DataFrame as well
        if log_all:
            df = pd.DataFrame({"w_rel": [w_rel], "d": [d]})
            return theta, df

        return theta

    def handleCheckMotorLimits(motor_controller, motor_no, lowerLimit, upperLimit):
        status = motor_controller.get_motor_status(motor_no)

        if status["position"] >= upperLimit:
            pass
        else:
            motor_controller.set_target_position(motor_no, upperLimit)
            motor_controller.set_impedance_controller_params(motor_no, 5, 0)
            print(f"Motor limit failure at motor {motor_no}")    

        if status["position"] <= lowerLimit:
            pass
        else:
            motor_controller.set_target_position(motor_no, lowerLimit)
            motor_controller.set_impedance_controller_params(motor_no, 5, 0)
            print(f"Motor limit failure at motor {motor_no}")

