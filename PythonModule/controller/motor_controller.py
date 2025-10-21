# motor_controller.py
import pyCandle
import sys

class MotorController:
    def __init__(self, candle, motor_no=0, upper_limit=0, lower_limit=0, kd=0, kp=0, max_torque=0):
        try:
            self.candle = candle
            self.motor_no = int(motor_no)
            self.control_signal = 0.0
            self.upper_limit = upper_limit
            self.lower_limit = lower_limit
            self.kd = kd
            self.kp = kp
            self.max_torque = max_torque
            self.init_motor()
        except ModuleNotFoundError:
            print("Motor controls are only available on Linux machines.")
            sys.exit("Exiting due to lack of motor control hardware.")

    # md80s is a array containing pyCandle.Md80 objects
    # motor_no equals index in md80s array 
    # motorId is attribute of pyCandle.Md80 object and can be accessed by it's method motor.getId()

    def init_motor(self):
        ids = self.candle.ping()
        if not ids:
            sys.exit("No motors found. Exiting.")
        for motor_no in ids:
            self.candle.addMd80(int(motor_no))

    def set_motor_mode(self, motor_no, mode):
        motor = self.candle.md80s[motor_no]
        self.candle.end()  # Beendet den Auto-Update-Modus
        self.candle.controlMd80SetEncoderZero(motor.getId())
        self.candle.controlMd80Mode(motor, mode)
        self.candle.controlMd80Enable(motor, True)
        self.candle.begin()  # Startet den Auto-Update-Modus erneut

    def set_only_motor_mode(self, motor_no, mode):
        motor = self.candle.md80s[motor_no]
        self.candle.controlMd80SetEncoderZero(motor.getId())
        self.candle.controlMd80Mode(motor, mode)
        self.candle.controlMd80Enable(motor, True)

    def get_motor_status(self, motor_no):
        motor = self.candle.md80s[int(motor_no)]
        if motor:
            position = motor.getPosition() or 0.0
            velocity = motor.getVelocity() or 0.0
            torque = motor.getTorque() or 0.0
            return {
                "position": position,
                "velocity": velocity,
                "torque": torque
            }
        #print("torque: ", torque)
        return {"position": 0.0, "velocity": 0.0, "torque": 0.0}

    
    def get_motor_mode(self, motor_no):
        motor = self.candle.md80s[int(motor_no)]
        if motor:
            return motor.getControlMode()  # Returns an enum or int
        return None
        


    def get_position_limits(self, upper_limit, lower_limit):
        self.upper_limit = upper_limit
        self.lower_limit = lower_limit
        return {"upperLimit": upper_limit, "lowerLimit": lower_limit}

    # Wrapper methods for motor settings
    def set_velocity_controller_params(self, motor_no, kp, ki, kd, iWindup):
        motor = self.candle.md80s[int(motor_no)]
        motor.setVelocityControllerParams(kp, ki, kd, iWindup)

    def set_target_velocity(self, motor_no, velocity_target):
        motor = self.candle.md80s[int(motor_no)]
        motor.setTargetVelocity(velocity_target)

    def set_max_torque(self, motor_no, max_torque):
        motor = self.candle.md80s[int(motor_no)]
        motor.setMaxTorque(max_torque)

    def set_max_velocity(self, motor_no, max_velocity): # note: has no effect in Position PID, Velocity PID, Raw Torque or Impedance modes.
        motor = self.candle.md80s[int(motor_no)]
        motor.setProfileVelocity(max_velocity)

    def set_max_acceleration(self, motor_no, max_acceleration):
        motor = self.candle.md80s[int(motor_no)]
        motor.setProfileAcceleration(max_acceleration)

    def set_position_controller_params(self, motor_no, kp, ki, kd, iWindup):
        motor = self.candle.md80s[int(motor_no)]
        motor.setPositionControllerParams(kp, ki, kd, iWindup)

    def set_target_position(self, motor_no, target_position):
        motor = self.candle.md80s[int(motor_no)]
        motor.setTargetPosition(target_position)

    def set_impedance_controller_params(self, motor_no, kp, kd):
        motor = self.candle.md80s[int(motor_no)]
        motor.setImpedanceControllerParams(kp, kd)

    def set_target_torque(self, motor_no, torque): # should be torque FF (feed forward) since it does not set the final torque output
        motor = self.candle.md80s[int(motor_no)]
        print(f"[DEBUG] Actually sending torque {torque} to motor {motor_no}")
        motor.setTargetTorque(torque)

    def blink(self, motor_no):
        motor = self.candle.md80s[int(motor_no)]
        self.candle.configMd80Blink(motor.getId())
