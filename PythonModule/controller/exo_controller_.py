import asyncio
import socket
import numpy as np
import pandas as pd
import json
import math
import time
import random
import os
from utils import *
from networking_utils import Utilities
from parameter_registry_ import PARAMETER_REGISTRY
from validation_utils import validate_parameter, get_parameter_config_key

# ---------------------- Test Mode / Motor Controller ----------------------
TEST_MODE = True  # True for MockMotorController, False for real hardware

if TEST_MODE:
    from mock_motor_controller import MockMotorController as MotorController
    print("Running in TEST MODE with mock controller")
else:
    import pyCandle
    from motor_controller import MotorController

# ---------------------- UDP Protocol ----------------------
class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, message_handler):
        self.message_handler = message_handler

    def datagram_received(self, data, addr):
        asyncio.create_task(self.message_handler(data, addr))

# ---------------------- WristExoController ----------------------
class WristExoController:
    def __init__(self, motor_controller):
        self.loop = asyncio.get_event_loop()
        self.mc = motor_controller  

        self.utils = Utilities()
        self.motor_settings_received = False
        self.system_initialized = False

        # Load safety config
        with open("config.json") as f:
            self.safety_config = json.load(f)
        self.config = self.safety_config
        self.dynamic_config = self.initialize_dynamic_config()

        # Motor mapping
        self.extendingMotorNo = self.config["extendingMotorNo"]
        self.flexingMotorNo = self.config["flexingMotorNo"]

        # UDP ports & addresses
        self.motor_settings_port = self.config["motor_settings_port"]
        self.confirmation_port = self.config["confirmation_port"]
        self.start_signal_port = self.config["start_signal_port"]
        self.myo_reg_val_port = self.config["myo_reg_val_port"]
        self.disconnect_port = self.config["disconnect_port"]  # Make sure this is in your config
        self.motors_connected = True  # Track motor connection state

        # Position control parameters (with defaults from config)
        self.max_velocity = self.config.get("max_velocity", 4.0)
        self.upper_position_limit = self.config.get("upper_position_limit", 1.8)
        self.lower_position_limit = self.config.get("lower_position_limit", -1.8)
        self.position_kp = self.config.get("position_kp", 8.0)
        self.position_kd = self.config.get("position_kd", 0.8)
        self.movement_speed = self.config.get("movement_speed", 0.8)
        self.extension_strength_scale = self.config.get("extension_strength_scale", 1.0)
        self.flexion_strength_scale = self.config.get("flexion_strength_scale", 1.0)
        self.min_movement_threshold = self.config.get("min_movement_threshold", 0.1)
        self.smoothing_factor = self.config.get("smoothing_factor", 0.05)
        self.deadzone_threshold = self.config.get("deadzone_threshold", 0.05)
        
        self.control_period = self.config["control_period"]

        # Calibration CSV placeholders
        self.calib = None
        self.rest_ext = 0.0
        self.rest_flex = 0.0
        #self.load_calibration("wrist_recordings.csv")

        # Internal state
        self.current_mov = None
        self.current_strength = 0.0
        self.last_mov = None
        self.target_position_ext = 0.0
        self.target_position_flex = 0.0
        self.smoothed_position_ext = 0.0
        self.smoothed_position_flex = 0.0
        
        # Removed torque-related variables
        self.udp_sessions = {}
        self.loop = asyncio.get_event_loop()

    def initialize_dynamic_config(self):
        config = {}
        for param_name, meta in PARAMETER_REGISTRY.items():
            config_key = meta.get('config_key', param_name)

            # Use safety config value if available, otherwise registry default
            if config_key and config_key in self.safety_config:
                config[param_name] = self.safety_config[config_key]
            else:
                config[param_name] = meta['default']
        return config
  
    #Load Hand Position recorded with hand_movement_recorder.py. 
    #Note please record the hand movement saperatly then use this funciton. 
    def load_calibration(self, csv_path):
        if not os.path.exists(csv_path):
            print(f"Calibration file {csv_path} not found.")
            self.calib = None
            return

        df = pd.read_csv(csv_path, header=0)
        df.columns = [c.strip() for c in df.columns]

        movements = df['movement'].unique()
        calib = {}
        for m in movements:
            sub = df[df['movement'] == m]
            if sub.empty:
                continue
            ext_vals = sub['motor_ext_pos'].values
            flex_vals = sub['motor_flex_pos'].values
            calib[m] = {
                'ext_min': np.min(ext_vals),
                'ext_max': np.max(ext_vals),
                'ext_mean': np.mean(ext_vals),
                'flex_min': np.min(flex_vals),
                'flex_max': np.max(flex_vals),
                'flex_mean': np.mean(flex_vals)
            }
        self.calib = calib
        print("Calibration loaded:", list(calib.keys()))
        if 'rest' in calib:
            self.rest_ext = calib['rest']['ext_mean']
            self.rest_flex = calib['rest']['flex_mean']
        else:
            self.rest_ext = np.mean(df['motor_ext_pos'])
            self.rest_flex = np.mean(df['motor_flex_pos'])
        print(f"Rest baseline ext={self.rest_ext:.3f}, flex={self.rest_flex:.3f}")

    def map_prediction_to_targets(self, pred_values):
        # if self.calib is None:
        #     return None, None, None, 0.0

        vals = np.array(pred_values, dtype=float)
        exps = np.exp(vals - np.max(vals))
        probs = exps / np.sum(exps)
        idx = int(np.argmax(probs))
        strength = float(probs[idx])

        if idx == 0:
            mov = 'isometric'
        elif idx == 1:
            mov = 'extension'
        elif idx == 2:
            mov = 'flexion'
        else:
            mov = 'rest'

        # if mov not in self.calib:
        #     mov = 'rest'

        # c = self.calib[mov]

        # if mov == 'extension':
        #     theta_des_ext = self.rest_ext + strength * (c['ext_max'] - self.rest_ext)
        #     theta_des_flex = self.rest_flex
        # elif mov == 'flexion':
        #     theta_des_ext = self.rest_ext
        #     theta_des_flex = self.rest_flex + strength * (c['flex_max'] - self.rest_flex)
        # elif mov == 'isometric':
        #     theta_des_ext = self.rest_ext
        #     theta_des_flex = self.rest_flex
        # else:
        #     theta_des_ext = self.rest_ext
        #     theta_des_flex = self.rest_flex

        #print(f"[DEBUG] Mapping predictions mov: {mov}, strength: {strength:.3f}")

        #return float(theta_des_ext), float(theta_des_flex), mov, strength
        return  mov, strength

    # ---------------------- Simple wrist exo controller ----------------------
    async def simple_wrist_exo_controller(self, data, addr):
        try:
            message = simpleDecodeiMBlocksDoubleMessage(data)
            if message and hasattr(message, 'values') and len(message.values) == 4:
                pred = list(message.values)
                # Mapping Prediction from android to target hand positon
                mov, strength = self.map_prediction_to_targets(pred)
                self.current_mov = mov
                self.current_strength = strength
                print(f"EMG: {mov} (strength: {strength:.3f})")
            else:
                print(f"Invalid prediction data: {data}")
        except Exception as e:
            print(f"Error in controller: {e}")
        await asyncio.sleep(self.control_period)

    # ---------------------- Motor & UDP setup ----------------------
    async def start_udp_client(self, port, handler):
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: UDPProtocol(handler),
            local_addr=('0.0.0.0', port)
        )
        self.udp_sessions[port] = (transport, protocol)
        return transport, protocol

    def stop_udp_client(self, port=None):
        if port is not None:
            if port in self.udp_sessions:
                transport, _ = self.udp_sessions[port]
                transport.close()
                del self.udp_sessions[port]
        else:
            for t, _ in self.udp_sessions.values():
                t.close()
            self.udp_sessions.clear()

    async def handle_motor_settings(self, data, addr):
        try:
            # Parse JSON data
            raw_settings = json.loads(data.decode('utf-8'))
            validated_settings = {}

            # Validate each setting
            for android_key, value in raw_settings.items():
                registry_key = self.map_android_to_registry(android_key)
                
                if registry_key in PARAMETER_REGISTRY:
                    validated_value = validate_parameter(registry_key, value)
                    validated_settings[registry_key] = validated_value

                    # Update dynamic config
                    config_key = get_parameter_config_key(registry_key)
                    if config_key:
                        self.dynamic_config[config_key] = validated_value
                else:
                    print(f"Warning: Unknown parameter {android_key}, skipping")
            
            # Apply validated settings
            await self.apply_validated_settings(validated_settings)
            await self.send_confirmation(addr)
            
            # Only set this flag if not already set for initial handshake
            if not self.motor_settings_received:
                self.motor_settings_received = True
                print("Initial motor settings applied and confirmed")
            else:
                print("Motor settings updated during operation")

        except Exception as e:
            print(f"Error handling motor settings: {e}")

    async def handle_start_signal(self, data, addr):
        try:
            message = json.loads(data.decode('utf-8'))
            if message.get("command") == "start":
                self.system_initialized = True
                self.motors_connected = True
                print("System started")
                ack_data = json.dumps({"status": "success", "message": "System started"}).encode('utf-8')
                udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    udp_socket.sendto(ack_data, (addr[0], self.confirmation_port))
                finally:
                    udp_socket.close()
        except Exception as e:
            print(f"Error handling start signal: {e}")

 # ---------------------- Disconnect Handler ----------------------
    async def handle_disconnect_signal(self, data, addr):
        """Handle disconnect command from Android"""
        try:
            message = json.loads(data.decode('utf-8'))
            if message.get("command") == "disconnect":
                print("Disconnect command received. Stopping motors...")
                
                # Set motors to disconnected state
                self.motors_connected = False
                
                # Stop motors by setting target position to 0
                await self.loop.run_in_executor(
                    None, 
                    lambda: self.mc.set_target_position(self.extendingMotorNo, 0.0)
                )
                await self.loop.run_in_executor(
                    None, 
                    lambda: self.mc.set_target_position(self.flexingMotorNo, 0.0)
                )
                
                # Reset internal state
                self.current_mov = 'rest'
                self.current_strength = 0.0
                self.target_position_ext = 0.0
                self.target_position_flex = 0.0
                self.smoothed_position_ext = 0.0
                self.smoothed_position_flex = 0.0
                
                print("Motors disconnected and stopped")
                
                # Not implemented 
                ack_data = json.dumps({
                    "status": "success", 
                    "message": "Motors disconnected"
                }).encode('utf-8')
                
                udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    #udp_socket.sendto(ack_data, (addr[0], self.confirmation_port))
                    #print(f" Sent disconnect confirmation to {addr[0]}:{self.confirmation_port}")
                    print(f" disconnected")

                finally:
                    udp_socket.close()
                    
        except Exception as e:
            print(f"Error handling disconnect signal: {e}")

    def map_android_to_registry(self, android_key):
        android_to_registry = {
            # Position control parameters
            'positionKp': 'position_kp',
            'positionKd': 'position_kd', 
            'movementSpeed': 'movement_speed',
            
            # Safety parameters
            'maxVelocity': 'max_velocity',
            'upperPositionLimit': 'upper_position_limit',
            'lowerPositionLimit': 'lower_position_limit',
            
            # Strength scaling
            'extensionStrengthScale': 'extension_strength_scale',
            'flexionStrengthScale': 'flexion_strength_scale',
            'minMovementThreshold': 'min_movement_threshold',
            
            # Comfort parameters
            'smoothingFactor': 'smoothing_factor',
            'deadzoneThreshold': 'deadzone_threshold'
        }
        return android_to_registry.get(android_key, android_key)

    async def apply_validated_settings(self, validated_settings):
        # --- Position control parameters ---
        if 'position_kp' in validated_settings:
            self.position_kp = validated_settings['position_kp']
            print(f"Updated position_kp: {self.position_kp}")

        if 'position_kd' in validated_settings:
            self.position_kd = validated_settings['position_kd']
            print(f"Updated position_kd: {self.position_kd}")

        if 'movement_speed' in validated_settings:
            self.movement_speed = validated_settings['movement_speed']
            print(f"Updated movement_speed: {self.movement_speed}")

        # --- Safety limits ---
        if 'max_velocity' in validated_settings:
            self.max_velocity = validated_settings['max_velocity']
            print(f"Updated max_velocity: {self.max_velocity}")

        if 'upper_position_limit' in validated_settings:
            self.upper_position_limit = validated_settings['upper_position_limit']
            print(f"Updated upper_position_limit: {self.upper_position_limit}")

        if 'lower_position_limit' in validated_settings:
            self.lower_position_limit = validated_settings['lower_position_limit']
            print(f"Updated lower_position_limit: {self.lower_position_limit}")

        # --- Strength scaling ---
        if 'extension_strength_scale' in validated_settings:
            self.extension_strength_scale = validated_settings['extension_strength_scale']
            print(f"Updated extension_strength_scale: {self.extension_strength_scale}")

        if 'flexion_strength_scale' in validated_settings:
            self.flexion_strength_scale = validated_settings['flexion_strength_scale']
            print(f"Updated flexion_strength_scale: {self.flexion_strength_scale}")

        if 'min_movement_threshold' in validated_settings:
            self.min_movement_threshold = validated_settings['min_movement_threshold']
            print(f"Updated min_movement_threshold: {self.min_movement_threshold}")

        # --- Comfort parameters ---
        if 'smoothing_factor' in validated_settings:
            self.smoothing_factor = validated_settings['smoothing_factor']
            print(f"Updated smoothing_factor: {self.smoothing_factor}")

        if 'deadzone_threshold' in validated_settings:
            self.deadzone_threshold = validated_settings['deadzone_threshold']
            print(f"Updated deadzone_threshold: {self.deadzone_threshold}")

    async def send_confirmation(self, addr):
        confirmation_data = json.dumps({"status": "success", "message": "Motor settings applied"}).encode('utf-8')
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_socket.sendto(confirmation_data, (addr[0], self.confirmation_port))
            print(f"✅ Sent confirmation to {addr[0]}:{self.confirmation_port}")
        finally:
            udp_socket.close()

    async def master_control_loop(self):
        """Main control loop for position control"""
        while True:
            # This loop can be used for any periodic tasks needed
            await asyncio.sleep(self.control_period)

    async def motorControlWithEmgResult(self):
        """Main EMG-controlled position assistance function"""
        print("Running EMG-controlled position assistance with Android safety parameters")
        
        while True:
            
            if not self.motors_connected:
                await asyncio.sleep(self.control_period) # optional already applying self.control_period later
                continue



            current_mov = getattr(self, 'current_mov', 'rest')
            raw_strength = getattr(self, 'current_strength', 0.0)
            
            # Apply minimum threshold
            effective_strength = raw_strength if raw_strength >= self.min_movement_threshold else 0.0
            
            # FIXED: Correct direction logic
            if current_mov == 'flexion':
                # Flexion: POSITIVE target (motor moves to positive position)
                target = self.upper_position_limit * effective_strength * self.flexion_strength_scale * self.movement_speed
            elif current_mov == 'extension':
                # Extension: NEGATIVE target (motor moves to negative position)  
                target = self.lower_position_limit * effective_strength * self.extension_strength_scale * self.movement_speed
            elif current_mov == 'isometric':
                target = 0.0
            else:  # rest
                target = 0.0
            
            # Apply deadzone around neutral
            if abs(target) < self.deadzone_threshold:
                target = 0.0
            
            # Smooth position transition
            self.smoothed_position_ext = (1 - self.smoothing_factor) * self.smoothed_position_ext + self.smoothing_factor * target
            self.smoothed_position_flex = -self.smoothed_position_ext  # Opposite direction
            
            # Apply position limits for safety
            final_ext = max(min(self.smoothed_position_ext, self.upper_position_limit), self.lower_position_limit)
            final_flex = max(min(self.smoothed_position_flex, self.upper_position_limit), self.lower_position_limit)
            
            # Send position commands to motors
            await self.loop.run_in_executor(
                None, 
                lambda: self.mc.set_target_position(self.extendingMotorNo, final_ext)
            )
            await self.loop.run_in_executor(
                None, 
                lambda: self.mc.set_target_position(self.flexingMotorNo, final_flex)
            )
            
            # Logging
            if current_mov != getattr(self, 'last_mov', None) or effective_strength > 0:
                print(f"Movement: {current_mov.upper():10} | Strength: {effective_strength:.2f} | "
                    f"Position: [{final_ext:.2f}, {final_flex:.2f}] rad")
                self.last_mov = current_mov
            
            await asyncio.sleep(self.control_period)

    # ---------------------- Start Controller ----------------------
    async def start(self):
      
        
        
        print(f"Listening on ports: {self.motor_settings_port}, {self.start_signal_port}, {self.myo_reg_val_port}")
        await self.start_udp_client(self.motor_settings_port, self.handle_motor_settings)
        await self.start_udp_client(self.start_signal_port, self.handle_start_signal)
        await self.start_udp_client(self.disconnect_port, self.handle_disconnect_signal)  

        # Wait for motor settings & start signal
        while not self.motor_settings_received:
            await asyncio.sleep(0.1)
        while not self.system_initialized:
            await asyncio.sleep(0.1)

        # Start UDP listeners
        await self.start_udp_client(self.myo_reg_val_port, self.simple_wrist_exo_controller)
        # Start motor control task
        asyncio.create_task(self.motorControlWithEmgResult())
        # Start master control loop
        asyncio.create_task(self.master_control_loop())
        
        print("Controller fully initialized and running")

    def cleanup(self):
        self.stop_udp_client()
        if not TEST_MODE:
            try:
                self.mc.candle.end()
            except:
                pass
        print("Controller cleaned up.")

    
    def impedance_mode(self, motor_no, kp, kd):
        """
        set motor to impedance mode (position tracking via Kp/Kd)
        """
        print(f"Motor {motor_no}: Impedance mode with Kp={kp}, Kd={kd}")
        if TEST_MODE:
        # For test mode, just call the method without pyCandle reference
            self.mc.set_only_motor_mode(motor_no, "IMPEDANCE")
        else:
            self.mc.set_only_motor_mode(motor_no, pyCandle.IMPEDANCE)
        self.mc.set_impedance_controller_params(motor_no, kp, kd)


