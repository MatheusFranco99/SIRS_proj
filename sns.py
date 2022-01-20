import sys
import socket, ssl
import random
import string

import hashlib
import datetime

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import os

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5 as PKCS_SIGN

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

with open("public_server.key", "rb") as k:
    public_server_key = RSA.importKey(k.read())

with open("sns.key", "rb") as k:
    key_priv = RSA.importKey(k.read())

def encrypt(data):
    cipher = PKCS1_v1_5.new(public_server_key)
    return cipher.encrypt(data)

def digital_signature(msg):
    digest = SHA256.new()
    digest.update(msg)

    signer = PKCS_SIGN.new(key_priv)
    return signer.sign(digest)

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
            
            #generating a symmetric key
            AES_key_length = 16
            secret_key = os.urandom(AES_key_length)
            aes_enc = AES.new(secret_key, AES.MODE_CBC)
            iv = aes_enc.iv  #get initialization vector

            secret = secret_key + b':INITIALVECTOR:' + iv
            secret_enc = encrypt(secret)

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
            
            client.connect((user_host, user_port))
            client.send(msg.encode("utf-8"))
            client.close()
            print("To (host,port): " + str(user_host) + "," + str(user_port) + ". Sent: " + msg)


