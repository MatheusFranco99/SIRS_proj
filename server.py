import sys
import socket, ssl
import threading
import datetime
import pickle
import hashlib

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5 as PKCS_SIGN

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import os


# Global variables 
sns_DB = [] # sns codes
proxy_IP = '192.168.0.4'
sns_IP = '192.168.0.4'
users = ['192.168.0.2', '192.168.0.3']  # address of all active users

users_reg = []
users_logged = []
users_password = {} # ip : password

quit_program = False

with open("server.key", "rb") as k:
    key_priv = RSA.importKey(k.read())

with open("public_sns.key", "rb") as k:
    sns_public_key = RSA.importKey(k.read())


def decrypt_data(data):
    global key_priv
    print(data)
    decipher = PKCS1_v1_5.new(key_priv)
    return decipher.decrypt(data, None)

def validate_signature(msg, signature):
    global sns_public_key

    digest = SHA256.new()
    digest.update(msg)

    verifier = PKCS_SIGN.new(sns_public_key)
    verified = verifier.verify(digest, signature)

    if verified:
        #check freshness
        timestamp1 = datetime.datetime.now().timestamp()
        timestamp2 = float(msg.split(b":")[0])
        if timestamp1 - timestamp2 < 5:     #5 segundos
            return True
    
    return False



# RECEBE:
# do SNS quando user esta positivo pra covid19
# COD:<sns_code>:\n"
def received_cod(sns_code):
    print("Handling sns code")
    global sns_DB
    # Adds the sns_code generated by the sns to a list with all sns codes received
    sns_DB.append(sns_code)
    print("----")
    
# RECEBE:
# De um user positivo
# POS:<sns_code>:(<encrypt_token>:)*\n

# ENVIA:
# do server quando alguem tem covid
# CON:(<token>:)*\n
def received_pos(sns_code, tokens):
    print("Handling positive user")
    global sns_DB, users

    if sns_code not in sns_DB:
        print("Error: Invalid sns_code")

    msg = 'CON:' + ":".join(tokens) + ":\n"
    print("msg: " + msg)

    print(users)

    for ip in users:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client = ssl.wrap_socket(client, keyfile='server.key', certfile='server.crt')

        client.connect((ip, 60000))
        client.send(msg.encode("utf-8"))
        client.close()
    
    print("----")



# RECEBE:
# De um user que quer se registar
# REG:\n

# ENVIA:
# lista de ips logados
# REA:\n
def received_reg(ip_user,passw):
    print("Registering user")
    global users, users_logged, users_reg, users_password

    msg = ""

    if ip_user in users_reg:
        msg = 'REF:User already registered:\n'
    elif len(passw) < 10:
        msg = 'REF:Password must have at least 10 characters:\n'
    else:
        # check password strongness
        contains_digit = False
        contains_capital = False
        contains_small = False
        invalid_char = False
        for ch in passw:
            if('a' <= ch and ch <= 'z'):
                contains_small = True
            elif('A' <= ch and ch <= 'Z'):
                contains_capital = True
            elif('0' <= ch and ch <= '9'):
                contains_digit = True
            else:
                invalid_char = True
        
        if(invalid_char or (not contains_capital) or (not contains_digit) or (not contains_small)):
            msg = 'REF:Password must have at least one capital letter, one small letter and one digit:\n'
        else:
            users.append(ip_user)
            users_reg.append(ip_user)

            hash_object = hashlib.sha512(passw.encode("utf-8"))
            hex_dig = hash_object.hexdigest()
            users_password[ip_user] = hex_dig
        
            msg = 'REA:'
            msg += '\n'

    print("msg: " + msg)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client = ssl.wrap_socket(client, keyfile='server.key', certfile='server.crt')

    client.connect((ip_user, 60000))
    client.send(msg.encode("utf-8"))
    client.close()
    
    print("----")

# RECEBE:
# De um user que quer fazer login
# LOG:\n

# ENVIA:
# lista de ips logados
# LOA:(<ips>:)*\n
def received_log(ip_user,passw):
    print("Logging in user")
    global users, users_logged, users_reg, users_password

    msg = ""

    if(ip_user not in users_reg):
        msg = 'LOF:User not registered:\n'
    else:
        hash_object = hashlib.sha512(passw.encode("utf-8"))
        hex_dig = hash_object.hexdigest()

        if(hex_dig != users_password[ip_user]):
            msg = 'LOF:Wrong password:\n'
        else:
            msg = 'LOA:'
            for ip in users_logged:
                msg = msg + ip + ":"
            msg += '\n'
            if ip_user not in users_logged:
                users_logged.append(ip_user)

    print("msg: " + msg)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client = ssl.wrap_socket(client, keyfile='server.key', certfile='server.crt')

    client.connect((ip_user, 60000))
    client.send(msg.encode("utf-8"))
    client.close()
    
    print("----")


# RECEBE:
# De um user que fez logout
# LGT:\n
def received_lgt(ip_user):
    print("Logging out user")
    global users, users_logged, users_reg

    users_logged.remove(ip_user)
    
    print("----")


    
def handle_message(msg, client_addr, ciphertext = False):

    if ciphertext:
        cod_msg = b':CIPHER_COD_MSG:'
        if cod_msg in msg:
            ciphered_args = msg.split(cod_msg)

            secret_enc = ciphered_args[0]
            cipher_msg = ciphered_args[1].split(b':SIGNATURE:')[0]
            signature = ciphered_args[1].split(b':SIGNATURE:')[1]

            secret = decrypt_data(secret_enc)
            secret_key = secret.split(b':INITIALVECTOR:')[0]
            iv = secret.split(b':INITIALVECTOR:')[1]

            aes_dec = AES.new(secret_key, AES.MODE_CBC, iv)
            message = unpad(aes_dec.decrypt(cipher_msg), AES.block_size)

            if not validate_signature(message, signature):
                return
            
            msg = (message.split(b":", 1)[1]).decode("utf-8")
            print("Received secure msg: " + msg)

        else:
            msg = decrypt_data(msg).decode()
            print("Received: " + msg)

    # parse message
    msg_args = msg.split(':')

    if(msg_args[-1] != '\n'): # wrong formatting - ignore
        return

    # check what type of message was received and handle it in the corresponding way
    if(msg_args[0] == 'COD'):
        sns_code = ""
        try:
            assert(len(msg_args) == 3)
            sns_code = msg_args[1]
        except:
            return
        received_cod(sns_code)

    elif(msg_args[0] == 'POS'):
        sns_code = ""
        tokens = []
        try:
            assert(len(msg_args) >= 4)
            sns_code = msg_args[1]
            msg_args.pop(0) # delete POS
            msg_args.pop(0) # delete sns_code
            msg_args.pop(-1) # delete \n
            # only the tokens left
            tokens = msg_args
        except:
            return
        received_pos(sns_code, tokens)
    
    elif(msg_args[0] == 'REG'):
        user_ip = ''
        passw = ""
        try:
            assert(len(msg_args) == 3)
            user_ip = client_addr[0]
            passw = msg_args[1]
        except:
            return
        received_reg(user_ip,passw)
    
    elif(msg_args[0] == 'LOG'):
        user_ip = ''
        passw = ""
        try:
            assert(len(msg_args) == 3)
            user_ip = client_addr[0]
            passw = msg_args[1]
        except:
            return
        received_log(user_ip,passw)
    elif(msg_args[0] == 'LGT'):
        user_ip = ''
        try:
            assert(len(msg_args) == 2)
            user_ip = client_addr[0]
        except:
            return
        received_lgt(user_ip)
    elif(msg_args[0] == 'NEG'):
        print("Negative message received")
    else:
        # message not in the server's protocol
        print("Message received unknown: " + msg)



def listen(server_port):
    global proxy_IP, quit_program
    print("Server listening...")

    HOST = "192.168.0.1"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    

    server = ssl.wrap_socket(
        server, server_side=True, keyfile="server.key", certfile="server.crt"
    ) 
    
    server.bind((HOST, server_port))
    server.listen(5)

    threads_lst = []
    
    while not quit_program:
        server.settimeout(2)
        clientConnection = None
        clientAddress = None
        try:
            (clientConnection, clientAddress) = server.accept()
        except:
            continue

        if clientAddress[0] == proxy_IP or clientAddress[0] == sns_IP:  #proxy sends ciphertext, can't decode
            msg = b''
            while True:
                data = clientConnection.recv(1024)
                if not data:
                    break
                msg = msg + data
            t1 = threading.Thread(target = handle_message, args = (msg, clientAddress, True,))
        else:
            msg = ""
            while True:
                data = clientConnection.recv(1024)
                data = data.decode('utf-8')
                if not data:
                    break
                msg = msg + data
            print("Received: " + msg)
            t1 = threading.Thread(target = handle_message, args = (msg, clientAddress, False,))
        
        clientConnection.close()    
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



if __name__ == "__main__":
    print("Server turned on!")

    
    if (len(sys.argv) == 2):
        #get info
        filename = sys.argv[1]
        picklefile = open(filename,'rb')

        # LOAD sns_DB/users/users_reg/users_logged/users_password
        sns_DB = pickle.load(picklefile)
        users = pickle.load(picklefile)
        users_reg = pickle.load(picklefile)
        users_logged = pickle.load(picklefile)
        users_password = pickle.load(picklefile)
        picklefile.close()

    SERVER_PORT =  60000
    
    # cria thread listen
    t1 = threading.Thread(target = listen, args = (SERVER_PORT,) )
    t1.start()

    input("Enter anything to quit:")
    quit_program = True


    t1.join()

    picklefile = open('server_pickle','wb')

    # STORES sns_DB/users/users_reg/users_logged/users_password
    pickle.dump(sns_DB,picklefile)
    pickle.dump(users,picklefile)
    pickle.dump(users_reg,picklefile)
    pickle.dump(users_logged,picklefile)
    pickle.dump(users_password,picklefile)
    picklefile.close()