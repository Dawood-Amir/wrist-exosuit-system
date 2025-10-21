# mock_motor_controller.py
class MockMotorController:
    def __init__(self):
        print("Initializing Mock Motor Controller")
        self.md80s = [MockMd80(0), MockMd80(1)]  # Two mock motors
        self.candle = MockCandle()
        
    def set_only_motor_mode(self, motor_no, mode):
        print(f"Mock: Setting motor {motor_no} to mode {mode}")
        
    def set_impedance_controller_params(self, motor_no, kp, kd):
        print(f"Mock: Setting motor {motor_no} impedance params: kp={kp}, kd={kd}")
        
    def set_target_torque(self, motor_no, torque):
        print(f"Mock: Setting motor {motor_no} target torque: {torque}")
        
    def get_motor_status(self, motor_no):
        # Return mock status with some variation
        import random
        print(f"Mock: get_motor_status gets called  ")
        return {
            "position": random.uniform(-0.5, 0.5),
            "velocity": random.uniform(-0.1, 0.1),
            "torque": random.uniform(-0.5, 0.5)
        }
        
    def blink(self, motor_no):
        print(f"Mock: Blinking motor {motor_no}")
        
    def set_target_position(self, motor_no, position):
        print(f"Mock: Setting motor {motor_no} target position: {position}")
        
    def set_target_velocity(self, motor_no, velocity):
        print(f"Mock: Setting motor {motor_no} target velocity: {velocity}")
        
    def set_velocity_controller_params(self, motor_no, kp, ki, kd, iWindup):
        print(f"Mock: Setting motor {motor_no} velocity controller params: kp={kp}, ki={ki}, kd={kd}, iWindup={iWindup}")
        
    def set_position_controller_params(self, motor_no, kp, ki, kd, iWindup):
        print(f"Mock: Setting motor {motor_no} position controller params: kp={kp}, ki={ki}, kd={kd}, iWindup={iWindup}")
        
    def set_max_torque(self, motor_no, max_torque):
        print(f"Mock: Setting motor {motor_no} max torque: {max_torque}")
        # Remove the duplicate set_only_motor_mode method that was here

class MockMd80:
    def __init__(self, motor_id):
        self.motor_id = motor_id
        
    def getId(self):
        return self.motor_id

class MockCandle:
    def end(self):
        print("Mock: Candle end called")
    
    def begin(self):
        print("Mock: Candle begin called")