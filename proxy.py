import sys
import socket, ssl
import threading


# Global variables 
server_IP = '192.168.0.1'
server_port = 60000

my_IP = '192.168.0.4'
my_port = 60002

quit_program = False
    
# Forward all messages received
def send_msg(msg):
    global server_IP, server_port

    print("Passo aqui")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile="proxy.key", certfile="proxy.crt")

    try:
        client.connect((server_IP, server_port))
    except socket.error:
        print("Server Unreachable")
        exit(0)
    client.send(msg)
    client.close()


# wait for connections on the port 60002 and forward all messages to server
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
    
    while not quit_program:
        server.settimeout(2)
        try:
            clientConnection, clientAddress = server.accept()
        except:
            continue
        msg = b''
        while True:
            data = clientConnection.recv(1024)
            if not data:
                break
            msg = msg + data
        clientConnection.close()

        t1 = threading.Thread(target = send_msg, args = (msg,))    
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

    HOST = my_IP
    PORT = my_port

    # create thread listen
    t1 = threading.Thread(target = listen, args = (HOST, PORT) )
    t1.start()

    input("Enter anything to quit:")
    quit_program = True

    t1.join()