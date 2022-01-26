import sys
import socket, ssl
import random
import string
import threading

import datetime

import fcntl
import struct

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import os

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5 as PKCS_SIGN

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

my_IP = '192.168.0.4'
my_port = 60000

server_IP = '192.168.0.1'
server_port = 60000
users_port = 60000

verbose_mode = False

with open("public_server.key", "rb") as k:
    public_server_key = RSA.importKey(k.read())

with open("sns.key", "rb") as k:
    key_priv = RSA.importKey(k.read())

# function that print information when the program runs in verbose mode
def print_console(*argv):
    if verbose_mode:
        uniq = ""
        for arg in argv:
            uniq += str(arg) + " "
        uniq = uniq[:-1]
        print(uniq)

# encypt data with the server public key
def encrypt(data):
    cipher = PKCS1_v1_5.new(public_server_key)
    return cipher.encrypt(data)

# make a digital signature of msg with my private key
def digital_signature(msg):
    digest = SHA256.new()
    digest.update(msg)

    signer = PKCS_SIGN.new(key_priv)
    return signer.sign(digest)

names = {}

quit_program = False

# generate a sns_code
def get_sns_code():
    letters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(letters) for i in range(8))
    return code

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])

# check what type of message was received and handle it in the corresponding way
def treat_message(msg, client_address):
    global names

    # parse message
    msg_args = msg.split(':')

    if(msg_args[-1] != '\n'): # wrong formatting - ignore
        return

    # associate Username to ip
    if(msg_args[0] == 'NAME'): # NAME:<name>:\n
        name = ""
        ip = ""
        try:
            assert(len(msg_args) == 3)
            name = msg_args[1]
            ip = client_address[0]
        except:
            print("Wrong format in msg NAME")
            return
        if name not in names:
            names[name] = ip
        else:
            print("Name already exist")

# wait for connections on the port 60000
def listen(own_port):
    HOST = my_IP

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server = ssl.wrap_socket(server, keyfile='sns.key', certfile='sns.crt')
    server.bind((HOST, own_port))
    server.listen(5)

    threads_lst = []

    while not quit_program:
        server.settimeout(2)
        try:
            connection, client_address = server.accept()
        except:
            continue
        msg = ""
        while True:
            data = connection.recv(1024).decode('utf-8')
            if not data:
                break
            msg = msg + data
        
        print_console("--Received message--")
        print_console("From (host,port): " + str(client_address[0]) + "," + str(client_address[1]) + ". Sent: " + msg)
        
        connection.close()


        t1 = threading.Thread(target = treat_message, args = (msg,client_address,))    
        t1.start()

        idx_t = 0
        while idx_t < len(threads_lst):
            if(threads_lst[idx_t].is_alive()):
                idx_t += 1
            else:
                threads_lst[idx_t].join()
                threads_lst.pop(idx_t)

        threads_lst += [t1]
    
    for thr in threads_lst:
        thr.join()


def usage():
    sys.stderr.write('Usage: python3 sns.py\nFlag: [-v]\n')
    sys.exit(1)

if __name__ == "__main__":
    
    for arg in sys.argv:
        if arg == "-v":
            verbose_mode = True
            sys.argv.remove(arg)
            break
    
    if len(sys.argv) != 1:
        usage()

    t1 = threading.Thread(target = listen, args = (my_port,) )
    t1.start()
    
    command = 0
    while command != 2:
        print("-=[ \'SNS\' Menu ]=-")
        print("1 - Send code to positive person")
        print("2 - Quit")
        try:
            command = int(input().split(' ')[0])
        except:
            continue

        if command < 1 or command > 2:
            print("Invalid command")
        elif command == 1:
            # SEND:
            # to user and server: code when the user is positivie to covid19
            # COD:<sns_code>:\n
            user_name = input("Infected Name: ")
            if user_name not in names:
                print("Name doesn't exist")
                continue

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client = ssl.wrap_socket(client, keyfile='sns.key', certfile='sns.crt')

            sns_code = get_sns_code()
            msg = 'COD:' + sns_code + ":\n"

            print_console("--Send message--")
            print_console("To (host,port): " + str(server_IP) + "," + str(server_port) + ". Sent: " + msg)

            try:
                client.connect((server_IP, server_port))
            except socket.error:
                print("Server Unreachable")
                os._exit(1)
            
            #generating a symmetric key
            AES_key_length = 16
            secret_key = os.urandom(AES_key_length)
            aes_enc = AES.new(secret_key, AES.MODE_CBC)
            iv = aes_enc.iv  #get initialization vector

            secret = secret_key + b':INITIALVECTOR:' + iv
            secret_enc = encrypt(secret)

            # ensure freshness
            current_time = datetime.datetime.now()
            time_stamp = current_time.timestamp()
            fresh_msg = '' + str(time_stamp) + ':'
            fresh_msg_secret = fresh_msg.encode("utf-8") + msg.encode("utf-8")
            cipher_msg = aes_enc.encrypt(pad(fresh_msg_secret, AES.block_size))

            signature = digital_signature(fresh_msg_secret)

            packet = secret_enc + b':CIPHER_COD_MSG:' + cipher_msg + b':SIGNATURE:' + signature

            client.send(packet)
            client.close()

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client = ssl.wrap_socket(client, keyfile='sns.key', certfile='sns.crt')

            print_console("--Send message--")
            print_console("To (host,port): " + str(names[user_name]) + "," + str(users_port) + ". Sent: " + msg)
            
            try:
                client.connect((names[user_name], users_port))
            except socket.error:
                print("User Unreachable")
                continue
            client.send(msg.encode("utf-8"))
            client.close()
        
    quit_program = True
    t1.join()
    
