#udp_relay_for_wsl.py
#This file is important for relaying the udps to android from wsl and vice versa. 

import socket
import threading
import time

PORTS = [3350, 3352, 3351, 3340]
WSL_IP = "172.31.186.17" #Change it according to your wsl ip.

android_ip = None

def bidirectional_relay_simple(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(1.0)
    
    print(f"[+] Relay port {port} <-> WSL {WSL_IP}")

    def relay_loop():
        global android_ip
        while True:
            try:
                data, addr = sock.recvfrom(2048)
                
                if addr[0] == WSL_IP:
                    # From WSL → Forward to Android
                    if android_ip:
                        sock.sendto(data, (android_ip, port))
                        print(f"[WSL→A][{port}] {len(data)} bytes")
                    else:
                        print(f"[WARN] No Android IP for WSL→Android on port {port}")
                else:
                    # From Android → Forward to WSL and store IP
                    if android_ip != addr[0]:
                        android_ip = addr[0]
                        print(f"[+] Android IP: {android_ip}")
                    
                    sock.sendto(data, (WSL_IP, port))
                    print(f"[A→WSL][{port}] {len(data)} bytes")
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[ERROR][{port}] {e}")
                time.sleep(0.1)

    threading.Thread(target=relay_loop, daemon=True).start()

for port in PORTS:
    bidirectional_relay_simple(port)

print("[+] Simple bidirectional relay running. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[+] Exiting relay.")
