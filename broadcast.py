import socket
import ipaddress
import time
import json
import threading
import logging

logger = logging.getLogger(__name__)

class BroadCaster(object):

    def __init__(self):
        super(BroadCaster, self).__init__()
        self.enabled = False
        try:
            import fcntl
            import struct
            def get_ip_address(ifname):
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                return socket.inet_ntoa(fcntl.ioctl(
                    s.fileno(),
                    0x8915,  # SIOCGIFADDR
                    struct.pack('256s', bytes(ifname[:15], 'utf-8'))
                )[20:24])

            # Try wlan1 (Hotspot) first, then wlan0, then fallback
            try:
                self.IPADDRESS = get_ip_address('wlan1')
            except:
                try:
                    self.IPADDRESS = get_ip_address('wlan0')
                except:
                    # Fallback: get IP by connecting to a public address
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        s.connect(("8.8.8.8", 80))
                        self.IPADDRESS = s.getsockname()[0]
                    except:
                        self.IPADDRESS = "127.0.0.1"
                    finally:
                        s.close()

            self.UDP_IP = socket.inet_ntoa(socket.inet_aton(self.IPADDRESS)[:3] + b'\xff' )
            self.UDP_PORT = 8888
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to bind once, don't loop forever
            try:
                self.sock.bind((self.IPADDRESS, 0))
                self.enabled = True
                logger.info(f"Broadcaster initialized on {self.IPADDRESS}")
            except Exception as e:
                logger.warning(f"Could not bind broadcaster: {e}")

        except Exception as e:
            logger.error(f"Broadcaster initialization failed: {e}")

    def broadcast_message(self, message):
        if not self.enabled:
            logger.debug(f"MOCK BROADCAST: {message}")
            return
            
        try:
            self.sock.sendto(message, (self.UDP_IP, self.UDP_PORT))
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
