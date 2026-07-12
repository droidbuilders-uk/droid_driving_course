import socket
import sys
import fcntl
import struct
import time

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])

def test_broadcast(message, interface='wlan1'):
    print(f"--- Starting Broadcast Test ---")
    
    # 1. Discover the IP of the given interface
    try:
        ip = get_ip_address(interface)
        print(f"✅ Found IP for {interface}: {ip}")
    except Exception as e:
        print(f"❌ Error: Could not find IP for {interface}. Is the interface up?")
        print(f"   Details: {e}")
        return

    # 2. Calculate the broadcast IP (assuming /24 subnet for the hotspot)
    # E.g. 192.168.43.1 -> 192.168.43.255
    broadcast_ip = socket.inet_ntoa(socket.inet_aton(ip)[:3] + b'\xff')
    print(f"🎯 Target Broadcast IP: {broadcast_ip} (Port 8888)")

    # 3. Setup UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind((ip, 0))
        print(f"✅ Bound socket to source IP: {ip}")
    except Exception as e:
        print(f"❌ Error binding socket to {ip}: {e}")
        return

    # 4. Send the message multiple times just to be sure
    print(f"🚀 Sending '{message}' over UDP broadcast...")
    for i in range(3):
        try:
            sock.sendto(message.encode('utf-8'), (broadcast_ip, 8888))
            print(f"   -> Packet {i+1} sent successfully!")
        except Exception as e:
            print(f"   -> ❌ Packet {i+1} failed: {e}")
        time.sleep(0.5)

    print("--- Test Complete ---")

if __name__ == '__main__':
    msg = sys.argv[1] if len(sys.argv) > 1 else "rainbow"
    iface = sys.argv[2] if len(sys.argv) > 2 else "wlan1"
    test_broadcast(msg, iface)
