import socket
import ssl

from server_tls import HOST as SERVER_HOST
from server_tls import PORT as SERVER_PORT

HOST = "192.168.0.10"
PORT = 60002

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

client = ssl.wrap_socket(client, keyfile="client.key", certfile="client.crt")

if __name__ == "__main__":
    client.bind((HOST, PORT))
    client.connect(("192.168.0.100", 60000))

    while True:
        from time import sleep

        client.send("Hello World!".encode("utf-8"))
        sleep(1)