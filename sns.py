import sys
import socket, ssl
import random
import string

# ENVIA:

# Pra user e server: codigo quando alguem testa positivo
# COD:<sns_code>:\n

def get_sns_code():
    letters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(letters) for i in range(8))
    return code


if __name__ == "__main__":
    
    command = 0
    while command != 2:
        print("-=[ \'SNS\' Menu ]=-")
        print("1 - Send code to positive person")
        print("2 - Quit")
        command = int(input().split(' ')[0])

        if command < 1 or command > 2:
            print("Invalid command")
        elif command == 1:
            user_host = input("Infected IP: ")
            user_port = 60000

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client = ssl.wrap_socket(client, keyfile='sns.key', certfile='sns.crt')

            sns_code = get_sns_code()
            msg = 'COD:' + sns_code + ":\n"

            client.connect(("192.168.0.1", 60000))
            client.send(msg.encode("utf-8"))
            client.close()

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client = ssl.wrap_socket(client, keyfile='sns.key', certfile='sns.crt')
            
            client.connect((user_host, user_port))
            client.send(msg.encode("utf-8"))
            client.close()
            print("To (host,port): " + str(user_host) + "," + str(user_port) + ". Sent: " + msg)










