#hand_movement_recorder.
#This file is important to record the flexion and extension wrt to motor position. You can change this file as per your need.

import csv
import time
import pyCandle
import atexit
import sys
import threading

# --- CONFIGURATION ---
USE_MOCK = False
# Use RAW_TORQUE for pure current control; 0.0 target torque = 0.0 current
SOFT_CONTROL_MODE = pyCandle.RAW_TORQUE 
SOFT_TORQUE_LIMIT = 0.05  # Lowest possible max torque
SOFT_MODE_LOOP_SLEEP = 0.01  

# Globals for motor control and threading
running_soft_mode = False
original_max_torque_0 = None
original_max_torque_1 = None
# --- END CONFIGURATION ---

if USE_MOCK:
    from mock_motor_controller import MockMotorController as MotorController
else:
    from motor_controller import MotorController

if 'MotorController' not in locals():
    sys.exit("Error: MotorController class not found.")


# ---------- Initialize CANdle and Motor Controller ----------
try:
    candle = pyCandle.Candle(pyCandle.CAN_BAUD_1M, True)
    mc = MotorController(candle)
    mc.candle.end()
    mc.set_only_motor_mode(0, SOFT_CONTROL_MODE) 
    mc.set_only_motor_mode(1, SOFT_CONTROL_MODE)  

    mc.candle.begin()
except Exception as e:
    sys.exit(f"Failed to initialize CANdle/MotorController: {e}")

# ---------- Motor Control State & Threading Functions ----------

def set_soft_mode_params_minimal(motor_no):
    """
    MINIMAL FUNCTION: Only asserts zero target torque (to minimize current). 
    """
    mc.set_target_torque(motor_no, 0.0)

def keep_motors_soft():
    """Function to run in a separate thread, continuously asserting zero torque."""
    print(f"  -> SOFT MODE THREAD STARTED (Asserting Zero Torque @ {1/SOFT_MODE_LOOP_SLEEP} Hz).")
    while running_soft_mode:
        set_soft_mode_params_minimal(0)
        set_soft_mode_params_minimal(1)
        time.sleep(SOFT_MODE_LOOP_SLEEP)
    print("  -> SOFT MODE THREAD STOPPED.")


def soft_release_and_start_thread():
    """Initial setup. Will print messages ONCE for mode, then only during loop."""
    global original_max_torque_0, original_max_torque_1, running_soft_mode

    print("\n[SOFT MODE SETUP] (Expect printing during the loop)")

    # 1. Set the Max Torque and store original value
    for motor_no in [0, 1]:
        prev_torque = mc.set_max_torque(motor_no, SOFT_TORQUE_LIMIT)
        if motor_no == 0 and original_max_torque_0 is None:
            original_max_torque_0 = prev_torque
        elif motor_no == 1 and original_max_torque_1 is None:
            original_max_torque_1 = prev_torque
        print(f"  -> Motor {motor_no}: Max Torque temporarily set to {SOFT_TORQUE_LIMIT}.")
        
    # 2. Start the continuous background thread
    running_soft_mode = True
    soft_thread = threading.Thread(target=keep_motors_soft, daemon=True)
    soft_thread.start()
    return soft_thread


def shutdown_all_motors(soft_thread=None):
    """Stops the soft mode thread and restores settings."""
    global running_soft_mode
    print("\n🛑 Shutting down motors safely...")

    # 1. Stop the soft mode assertion thread
    running_soft_mode = False
    if soft_thread and soft_thread.is_alive():
        soft_thread.join()

    # 2. RESTORE ORIGINAL MAX TORQUE LIMITS
    if original_max_torque_0 is not None:
        restore_torque_0 = max(original_max_torque_0, 1.0)
        mc.set_max_torque(0, restore_torque_0)
    if original_max_torque_1 is not None:
        restore_torque_1 = max(original_max_torque_1, 1.0)
        mc.set_max_torque(1, restore_torque_1)

    # 3. Ensure final compliant state (using the standard Impedance mode for cleanup)
    mc.set_only_motor_mode(0, pyCandle.IMPEDANCE)
    mc.set_only_motor_mode(1, pyCandle.IMPEDANCE)
    mc.set_impedance_controller_params(0, 0.0, 0.0)
    mc.set_impedance_controller_params(1, 0.0, 0.0)
    mc.set_target_torque(0, 0.0)
    mc.set_target_torque(1, 0.0)

    print("✅ Motors are now compliant and safe.")

# --- MAIN EXECUTION ---

# 1. Setup the soft mode thread and register shutdown
soft_thread = soft_release_and_start_thread()
atexit.register(lambda: shutdown_all_motors(soft_thread))

# ---------- Movement Recording ----------
movements = ["isometric", "extension", "flexion", "rest"]
record_time = 5  # seconds per movement
csv_file = "wrist_recordings.csv"

# Open CSV and write headers
try:
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "movement", "motor_ext_pos", "motor_flex_pos"])

        for mov in movements:
            print("\n------------------------------------------------------------")
            # The printing will resume here due to the background thread
            input(f"💬 Get ready for '{mov}'. Press Enter to start recording...")
            print("------------------------------------------------------------")

            start_time = time.time()
            sample_period = 0.01  # 100 Hz
            print(f"  -> Recording '{mov}' for {record_time} seconds...")
            
            # --- THE RECORDING LOOP ---
            while time.time() - start_time < record_time:
                timestamp = time.time()
                ext_pos = mc.get_motor_status(0)["position"]
                flex_pos = mc.get_motor_status(1)["position"]
                writer.writerow([timestamp, mov, ext_pos, flex_pos])
                time.sleep(sample_period)
            # --- END RECORDING LOOP ---

            print(f"  -> '{mov}' recording finished.")

    print(f"\n📁 Recording finished! Saved to '{csv_file}'")

finally:
    pass