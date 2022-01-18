import sys
import socket, ssl
import threading


# Global variables 
server_IP = '192.168.0.1'
server_port = 60000
    

def send_pos(msg):
    global server_IP, server_port

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile="proxy.key", certfile="proxy.crt")

    client.connect((server_IP, server_port))
    client.send(msg)
    client.close()

    #print("To (host,port): " + str(server_IP) + "," + str(server_port) + ". Sent: " + msg)


def listen(HOST, PORT):
    print("Proxy listening...")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server = ssl.wrap_socket(
        server, server_side=True, keyfile="proxy.key", certfile="proxy.crt"
    ) 
    
    server.bind((HOST, PORT))
    server.listen(5)

    threads_lst = []
    
    while True:
        (clientConnection, clientAddress) = server.accept()
        msg = b''
        while True:
            data = clientConnection.recv(1024)
            if not data:
                break
            msg = msg + data
        #print("Received: " + msg)
        clientConnection.close()

        t1 = threading.Thread(target = send_pos, args = (msg,))    
        t1.start()

        idx_t = 0
        while idx_t < len(threads_lst):
            if(threads_lst[idx_t].is_alive()):
                idx_t += 1
            else:
                threads_lst[idx_t].join()
                threads_lst.pop(idx_t)

        threads_lst += [t1]



if __name__ == "__main__":
    print("Proxy turned on!")

    HOST = "192.168.0.2"
    PORT = 60002

    # cria thread listen
    t1 = threading.Thread(target = listen, args = (HOST, PORT) )
    t1.start()

    t1.join()