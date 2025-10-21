import asyncio
import json
import struct
import socket
import time

async def send_udp_message(host, port, message):
    """Send a UDP message to the given host and port."""
    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: asyncio.DatagramProtocol(),
        remote_addr=(host, port))
    try:
        transport.sendto(message)
        print(f"Sent message to {host}:{port}")
    finally:
        transport.close()

async def test_controller():
    host = '127.0.0.1'  
    
    # Use the ports from the controller's config.json
    motor_settings_port = 3350
    start_signal_port = 3352
    myo_reg_val_port = 3340   # This is the port for Myo regression values

    print("Starting test sequence...")
    
    # 1. Send motor settings
    motor_settings = {
        'kp': 10.0,
        'kd': 1.0,
        'maxTorque': 2.0,
        'extensionStrengthMax': 3.0,
        'flexionStrengthMax': 3.0,
        'extensionStrengthMin': 0.3,
        'flexionStrengthMin': 0.1,
        'maxVelocity': 11.0,
        'upperPositionLimit': 3.1415,
        'lowerPositionLimit': -3.1415,
        'baseTorque': 0.2,
        'alpha': 0.1
    }
    motor_settings_json = json.dumps(motor_settings).encode('utf-8')
    await send_udp_message(host, motor_settings_port, motor_settings_json)
    
    # Wait for confirmation
    await asyncio.sleep(1)
    
    # 2. Send start signal
    start_signal = {'command': 'start'}
    start_signal_json = json.dumps(start_signal).encode('utf-8')
    await send_udp_message(host, start_signal_port, start_signal_json)
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # 3. Send prediction data (simulate Myo predictions)
    print("Sending prediction data...")
    
    # Test different movement patterns
    movements = [
        [0.8, 0.1, 0.05, 0.05],  # Strong isometric
        [0.1, 0.8, 0.05, 0.05],  # Strong extension
        [0.1, 0.05, 0.8, 0.05],  # Strong flexion
        [0.1, 0.1, 0.1, 0.7],    # Rest
    ]
    
    for i, prediction in enumerate(movements):
        print(f"Sending prediction {i+1}: {prediction}")
        
        # Pack the prediction data as doubles (8 bytes each)
        prediction_data = struct.pack('<4d', *prediction)
        await send_udp_message(host, myo_reg_val_port, prediction_data)
        
        # Wait a bit between predictions
        await asyncio.sleep(3)
    
    print("Test sequence completed")

if __name__ == '__main__':
    asyncio.run(test_controller())