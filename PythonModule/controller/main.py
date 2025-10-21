# main.py
import asyncio
import atexit

# Check if we're in test mode (no Candle hardware)
TEST_MODE = True  # Set to False when using real hardware

if TEST_MODE:
    from mock_motor_controller import MockMotorController as MotorController
    print("Running in test mode with mock controller")
else:
    import pyCandle
    from motor_controller import MotorController

from exo_controller_ import WristExoController

async def main():
    # Initialize your motor controller here
    if TEST_MODE:
        motor_controller = MotorController()
        controller = WristExoController(motor_controller)
        atexit.register(controller.cleanup)
        
        # Set mock motors to impedance mode (no candle calls needed)
        controller.impedance_mode(0, 6, 2)
        controller.impedance_mode(1, 6, 2)

        await controller.start()
        await asyncio.Event().wait()
    else:
        # Real hardware initialization
        candle = pyCandle.Candle(pyCandle.CAN_BAUD_1M, True)
        motor_controller = MotorController(candle)
        controller = WristExoController(motor_controller)
        atexit.register(controller.cleanup)

        controller.mc.candle.end()  # Stop auto update

        # Set impedance mode
        controller.impedance_mode(0, 6, 2)
        controller.impedance_mode(1, 6, 2)

        controller.mc.candle.begin()  # Start auto update again

        # Start async control loop
        await controller.start()
        await asyncio.Event().wait()
if __name__ == '__main__':
    asyncio.run(main())



