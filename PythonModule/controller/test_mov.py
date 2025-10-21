# test_udp_listener.py
import socket
import struct
# Use this file to test if the udp_relay_for_wsl is working fine.
def simple_test_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 3340))
    print("Listening for UDP packets on port 3340...")
    
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received {len(data)} bytes from {addr}")
        print(f"Raw hex: {data.hex()}")
        
        # Try to decode as 4 doubles (32 bytes)
        if len(data) == 32:
            try:
                values = struct.unpack('<4d', data)  # 4 little-endian doubles
                print(f"Decoded doubles: {[f'{v:.3f}' for v in values]}")
                
                # Find max index
                max_idx = values.index(max(values))
                movements = ['isometric', 'extension', 'flexion', 'rest']
                print(f"Predicted movement: {movements[max_idx]} (index {max_idx})")
                print("-" * 50)
            except Exception as e:
                print(f"Decode error: {e}")
        else:
            print(f"Unexpected data length: {len(data)} bytes")

if __name__ == "__main__":
    simple_test_listener()