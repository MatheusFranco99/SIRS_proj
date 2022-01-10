# communication functions


import socket

def send_tls():
    pass

def listen_tls():
    pass


def get_IPs():
    interfaces = socket.getaddrinfo(host = socket.gethostname(), port=None, family=socket.AF_INET)

    ans = []
    for ip in interfaces:
        ans = ans + [ip[-1][0]]
    return ans

