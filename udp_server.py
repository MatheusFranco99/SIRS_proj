import socket
import time

def broadcast_loc(latitude, longitude, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    # Enable broadcasting mode
    server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    server.settimeout(0.2)
    s = "LOC:" + str(latitude) + ":" + str(longitude) + ":\n"
    se = s.encode("utf-8")
    server.sendto(se, ('<broadcast>', port))