import sys
from geopy.geocoders import Nominatim
import socket, ssl

import threading
import random

import stdiomask

import datetime
import time

from math import radians, sin,cos,sqrt,asin

import fcntl
import struct

import os

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

import pickle

# globals

server_IP = '192.168.0.1'
server_port = 60000

proxy_IP = '192.168.0.4'
proxy_port = 60002

sns_IP = '192.168.0.4'
sns_port = 60000

own_port = 60000

quit_program = False
verbose_mode = False

with open("public_server.key", "rb") as k:
    public_server_key = RSA.importKey(k.read())

# function that print information when the program runs in verbose mode
def print_console(*argv):
    if verbose_mode:
        uniq = ""
        for arg in argv:
            uniq += str(arg) + " "
        uniq = uniq[:-1]
        print(uniq)

# receives two geometric coordinates and calculates the distance between them
def calc_distance(lat1,lon1,lat2,lon2):
    lat1,lon1 = radians(lat1),radians(lon1)
    lat2,lon2 = radians(lat2),radians(lon2)

    dlon = lon2-lon1
    dlat = lat2-lat2
    trig = pow(sin(dlat/2),2) + cos(lat1) * cos(lat2) * pow(sin(dlon/2),2)
    Radius = 6371
    return 2 * asin(sqrt(trig)) * Radius

# encrypt data with the server's public key
def encrypt(data):
    cipher = PKCS1_v1_5.new(public_server_key)
    return cipher.encrypt(data.encode())

# send a message to inform the existence of this user to the SNS
def informSns(user):
    msg = "NAME:" + user.name + ":\n"
    try:
        send_message(msg,sns_IP,sns_port,user)
    except socket.error:
        print("SNS Unreachable")
        os._exit(1)

# send message msg to host and port via ssl sockets (TLS)
def send_message(msg, host, port, user, encode = True):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile=user.key, certfile=user.cert)

    if encode:
        print_console("--Send message--")
        print_console("To (host,port): " + str(host) + "," + str(port) + ". Sent: " + msg)

    client.connect((host, port))
    
    if encode:
        client.send(msg.encode("utf-8"))
    else:
        client.send(msg)

    client.close()

# checks if we are in the vicinity of the user who sent the message
def treat_loc(client_address,lat,lon,user):
    if client_address[0] not in user.others_ips:
        user.appendIP(client_address[0])

    latitude = user.latitude
    longitude = user.longitude
    curr_token = user.actualToken
    dist = calc_distance(latitude,longitude,lat,lon)

    if dist <= 5:
        # send TOK
        sentTokens = user.sentTokens
        now = datetime.datetime.now()
        sentTokens[curr_token] = {'datetime':now}
        ans = 'TOK:' + str(curr_token) + ":\n"
        try:
            send_message(ans, client_address[0], own_port,user)
        except socket.error:
            print("User Unreachable")

# when receiving a token we will save it with current location and also send one to this user
def treat_tok(client_address,o_tok,user):
    curr_token = user.actualToken
    curr_loc = user.actualLoc
    recvTokens = user.recvTokens
    sentTokens = user.sentTokens

    now = datetime.datetime.now()
    recvTokens[o_tok] = {'location':curr_loc,'datetime':now}

    sentTokens[curr_token] = {'datetime':now}

    ans = "RTOK:" + str(curr_token) + ":\n"
    try:
        send_message(ans, client_address[0], own_port,user)
    except socket.error:
        print("User Unreachable")

# when receiving a token we will save it with current location
def treat_rtok(client_address, o_tok,user):
    curr_loc = user.actualLoc
    recvTokens = user.recvTokens

    now = datetime.datetime.now()
    recvTokens[o_tok] = {'location':curr_loc,'datetime':now}

# when receiving a code from the sns we will save it and send it to the server with the tokens sent in the last 14 days
def treat_cod(client_address,sns_code, user):
    sentTokens = user.sentTokens

    print("You received a code from SNS due to your positive COVID test: " + sns_code + ".")
    user.add_sns_code(sns_code)

    # filter sentTokens maintaining only the last 14 days
    now = datetime.datetime.now()
    for key in sentTokens:
        delta = now - sentTokens[key]['datetime']
        if(delta > datetime.timedelta(days = 14)):
            sentTokens.pop(key)

    # ans = "POS:" + str(sns_code) + ":" + (token:)* + ":\n"
    ans = "POS:" + sns_code + ":"
    for tok in sentTokens:
        ans += str(tok) + ':'
    ans = ans + "\n"
    cipher_ans = encrypt(ans)

    print_console("--Send message--")
    print_console("To (host,port): " + str(proxy_IP) + "," + str(proxy_port) + ". Sent encrypted message: " + ans)

    try:
        send_message(cipher_ans, proxy_IP, proxy_port, user, False)
    except socket.error:
        print("Proxy Unreachable")
        os._exit(1)

# send messages to the server in order to camouflage POS messages
def send_negative(user):
    itt = 0
    length = 0
    # split sleep into several so as not to delay the closure of the app
    while not quit_program:
        if itt == 0:
            ans = "NEG:\n"
            cipher_ans = encrypt(ans)

            print_console("--Send message--")
            print_console("To (host,port): " + str(proxy_IP) + "," + str(proxy_port) + ". Sent encrypted message: " + ans)

            try:
                send_message(cipher_ans, proxy_IP, proxy_port, user, False)
            except socket.error:
                print("Proxy Unreachable")
                os._exit(1)
            length = random.randint(1,15)/5
            itt = itt+1
        else:
            itt = (itt +1)%6
            time.sleep(length)

# check if infected tokens were received
def treat_con(client_address,server_tokens,user):
    recvTokens = user.recvTokens

    # filter recvTokens maintaining only the last 14 days
    now = datetime.datetime.now()
    for key in recvTokens:
        delta = now - recvTokens[key]['datetime']
        if(delta > datetime.timedelta(days = 14)):
            recvTokens.pop(key)

    positive_situations = []

    for pos_tok in server_tokens:
        if int(pos_tok) in recvTokens:
            positive_situations += [recvTokens[int(pos_tok)]] # stores dictionary {'location':, 'datetime':}
    
    if(len(positive_situations) != 0):
        print("You were in contact with someone with COVID-19. List of places/time:")
        for i in range(len(positive_situations)):
            dt = positive_situations[i]['datetime']
            print("\tLocation:" + positive_situations[i]['location'] + ". Hour - Day/Month/Year: " + str(dt.hour)+ " - " + str(dt.day) + "/" + str(dt.month) + "/" + str(dt.year) + ".")

# checks the type of message received to handle it properly
def treat_message(msg, client_address, user):
    # parse message
    msg_args = msg.split(':')

    if(msg_args[-1] != '\n'): # wrong formatting - ignore
        return

    if(msg_args[0] == 'LOC'): # LOC:<lat>:<lon>:\n
        o_lat, o_lon = 0, 0
        try:
            assert(len(msg_args) == 4)
            o_lat = float(msg_args[1])
            o_lon = float(msg_args[2])
        except:
            return
        treat_loc(client_address,o_lat,o_lon,user)

    if(msg_args[0] == 'TOK'): # TOK:<token>:\n
        o_tok = 0
        try:
            assert(len(msg_args) == 3)
            o_tok = int(msg_args[1])
        except:
            return
        treat_tok(client_address,o_tok,user)

    elif(msg_args[0] == 'RTOK'): # RTOK:<token>:\n
        o_tok = 0
        try:
            assert(len(msg_args) == 3)
            o_tok = int(msg_args[1])
        except:
            return
        treat_rtok(client_address,o_tok,user)

    elif(msg_args[0] == 'COD'): # COD:<sns_cod>:\n
        sns_code = 0
        try:
            assert(len(msg_args) == 3)
            sns_code = msg_args[1]
        except:
            return
        treat_cod(client_address,sns_code,user)


    elif(msg_args[0] == 'CON'): # CON:<token>*:\n
        server_tokens = []
        for i in range(1,len(msg_args)-1):
            server_tokens += [msg_args[i]]
        treat_con(client_address,server_tokens,user)

# wait for connections on the port 60000
def listen_all_tcp(own_port, user):
    HOST = get_ip_address('enp0s3')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server = ssl.wrap_socket(
        server, server_side=True, keyfile=user.key, certfile=user.cert
    )
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


        t1 = threading.Thread(target = treat_message, args = (msg,client_address,user,))    
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

# receive geographic coordinates and return information about the location
def location_by_coord(latitude, longitude):
        coord = str(latitude) + ", " + str(longitude)

        location = Nomi_locator.reverse(coord)

        locationInfo = ""
        if 'road' in location.raw['address'].keys():
            locationInfo += location.raw['address']['road'] + ", "
        if 'amenity' in location.raw['address'].keys():
            locationInfo += location.raw['address']['amenity'] + ", "
        if 'neighbourhood' in location.raw['address'].keys():
            locationInfo += location.raw['address']['neighbourhood'] + ", "
        if 'village' in location.raw['address'].keys():
            locationInfo += location.raw['address']['village'] + ", "
        if 'city' in location.raw['address'].keys():
            locationInfo += location.raw['address']['city'] + ", "
        if 'country' in location.raw['address'].keys():
            locationInfo += location.raw['address']['country'] + ", "
        
        if not locationInfo:
            return "Unknown"
        else:
            size = len(locationInfo)
            locationInfo = locationInfo[:size - 2]
            return locationInfo

class User:
    def __init__(self, name, sentTokens, recvTokens, latitude, longitude, key, crt):
        self.name = name
        self.createNewToken()
        self.sentTokens = sentTokens
        self.recvTokens = recvTokens
        self.latitude = latitude
        self.longitude = longitude
        self.actualLoc = location_by_coord(latitude,longitude)
        self.sns_codes = []
        self.others_ips = []
        self.registered = False
        self.key = key
        self.cert = crt
    def createNewToken(self):
        self.actualToken = random.randint(1,1000000000)
    def add_sns_code(self,code):
        self.sns_codes += [code]
    def list_sns_codes(self):
        print("SNS codes:")
        for code in self.sns_codes:
            print("\t" + code)
    def appendIP(self,ip):
        self.others_ips += [ip]
    def getOthersIPs(self):
        return self.others_ips
    
def set_loc(user):
    user.createNewToken()
    print("Set your actual location")
    user.latitude = float(input("Latitude: "))
    user.longitude = float(input("Longitude: "))

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', bytes(ifname[:15], 'utf-8'))
    )[20:24])

# register user on the server
def registerUser(user,passw):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile=user.key, certfile=user.cert)

    msg = "REG:" + user.name + ":" + passw + ":\n"

    print_console("--Send message--")
    print_console("To (host,port): " + str(server_IP) + "," + str(server_port) + ". Sent: " + msg)

    try:
        client.connect((server_IP, server_port))
    except socket.error:
        print("Server Unreachable")
        os._exit(1)

    HOST = get_ip_address('enp0s3')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server = ssl.wrap_socket(
        server, server_side=True, keyfile=user.key, certfile=user.cert
    )
    server.bind((HOST, own_port))
    server.listen(1)

    client.send(msg.encode("utf-8"))  # send REG msg after already listening to the answer
    client.close()

    connection, client_address = server.accept()
    msg = ""
    while True:
        data = connection.recv(1024).decode('utf-8')
        if not data:
            break
        msg = msg + data

    print_console("--Received message--")
    print_console("From (host,port): " + str(client_address[0]) + "," + str(client_address[1]) + ". Sent: " + msg)

    connection.close()
    server.close()
    
    msg_args = msg.split(":")
    if(msg_args[-1] != "\n"):
        print("Error: wrong format answer from server to register message.")
        os._exit(1)
    if(msg_args[0] == 'REF' and len(msg_args) == 3):
        print("Error: register refused.",msg_args[1])
        os._exit(1)
    elif (not (msg_args[0] == 'REA' and len(msg_args) == 2)):
        print("Error: wrong format answer from server to register message.")
        os._exit(1)

    user.registered = True
    informSns(user)
    
# login user on the server
def loginUser(user,passw):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile=user.key, certfile=user.cert)
    msg = "LOG:" + passw + ":\n"

    HOST = get_ip_address('enp0s3')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server = ssl.wrap_socket(
        server, server_side=True, keyfile=user.key, certfile=user.cert
    )
    server.bind((HOST, own_port))
    server.listen(1)

    print_console("--Send message--")
    print_console("To (host,port): " + str(server_IP) + "," + str(server_port) + ". Sent: " + msg)

    try:
        client.connect((server_IP, server_port))
    except socket.error:
        print("Server Unreachable")
        os._exit(1)

    client.send(msg.encode("utf-8"))
    client.close()

    connection, client_address = server.accept()
    msg = ""
    while True:
        data = connection.recv(1024).decode('utf-8')
        if not data:
            break
        msg = msg + data
    
    print_console("--Received message--")
    print_console("From (host,port): " + str(client_address[0]) + "," + str(client_address[1]) + ". Sent: " + msg)

    connection.close()
    server.close()
    
    msg_args = msg.split(":")
    
    if(msg_args[-1] != "\n"):
        print("Error: wrong format answer from server to login message.")
        os._exit(1)
    if(msg_args[0] == 'LOF' and len(msg_args) == 3):
        print("Error: login refused.",msg_args[1])
        os._exit(1)
    elif (not (msg_args[0] == 'LOA' and msg_args[-1] == '\n')):
        print("Error: wrong format answer from server to log in")
        os._exit(1)

    # get ips from other users
    user.others_ips = []
    for i in range(1,len(msg_args)-1):
        user.appendIP(msg_args[i])

# logout user on the server
def logoutUser(user):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile=user.key, certfile=user.cert)

    msg = "LGT:\n"

    print_console("--Send message--")
    print_console("To (host,port): " + str(server_IP) + "," + str(server_port) + ". Sent: " + msg)

    try:
        client.connect((server_IP, server_port))
    except socket.error:
        print("Server Unreachable")
        os._exit(1)

    client.send(msg.encode("utf-8"))
    client.close()
    
# send current geolocation to all users
def send_loc(user: User, others_port):
    msg = "LOC:" + str(user.latitude) + ":" + str(user.longitude) + ":\n"

    unreachable_users = []

    for ip in user.getOthersIPs():
        try:
            send_message(msg,ip,others_port,user)
        except:
            unreachable_users += [ip]
    
    for ip in unreachable_users:
        user.others_ips.remove(ip)

def usage():
    sys.stderr.write('Usage: python3 app.py\nor\nUsage: python3 app.py user_pickle\nFlag: [-v]\n')
    sys.exit(1)

if __name__ == '__main__':

    for arg in sys.argv:
        if arg == "-v":
            verbose_mode = True
            sys.argv.remove(arg)
            break

    if len(sys.argv) != 1 and len(sys.argv) != 2:
        usage()

    Nomi_locator = Nominatim(user_agent="http")

    print("Welcome to the app \'Covid Contacts Trace\'")
    sentTokens = {}
    recvTokens = {}
    latitude = 0
    longitude = 0
    
    user = None

    password = ""

    if len(sys.argv) == 1:
        print("Register as first time user -> ")

        name = input("Username: ")
        while(not name or name.isspace() or ":" in name):
            print("Username can't be empty and can't use the character \':\'")
            name = input("Username: ")

        password = stdiomask.getpass(prompt="Password (at least 10 characters, with at least one capital letter, one small and one number): ")
        while(":" in password):
            print("Sorry, you can't use the character \':\' in your password")
            password = stdiomask.getpass(prompt="Password: ")

        print("Set your actual location")
        latitude = float(input("Latitude: "))
        longitude = float(input("Longitude: "))
        
        key = name + ".key"
        public_key = name + "_public.key"
        cert = name + ".crt"

        os.system("openssl genrsa -out " + key + " > /dev/null 2>&1")
        os.system("openssl rsa -in "+ key + " -pubout > " + public_key + " > /dev/null 2>&1")
        os.system("echo -e \"\n\n\n\n\n\n\n\n\n\" | openssl req -new -key " + key + " -out " + cert + " > /dev/null 2>&1")
        os.system("openssl x509 -req -days 365 -in " + cert + " -signkey " + key + " -out " + cert + " > /dev/null 2>&1")

        user = User(name, sentTokens, recvTokens, latitude, longitude, key, cert)

    
    if len(sys.argv) == 2:
        #get info
        filename = sys.argv[1]
        picklefile = open(filename,'rb')
        # LOAD user
        user = pickle.load(picklefile)
        picklefile.close()

        print("Login ->")
        password = stdiomask.getpass(prompt="Password: ")
        while(":" in password):
            print("Invalid password, try again ...")
            password = stdiomask.getpass(prompt="Password: ")

    # register in server
    if(not user.registered):
        registerUser(user, password)
    loginUser(user, password)


    # listen should run in background
    t1 = threading.Thread(target = listen_all_tcp, args = (own_port,user,) )
    t1.start()
    # every user starts in a negative state
    t2 = threading.Thread(target = send_negative, args = (user,) )
    t2.start()

    # we have to be listening before sending the location because we can receive a token
    time.sleep(1)

    send_loc(user,own_port)

    command = 0
    while command != 4:
        print("-=[ \'Covid Contacts Trace\' Menu ]=-")
        print("1 - Set actual location")
        print("2 - Show actual location")
        print("3 - Check codes sent by SNS")
        print("4 - Quit")
        
        try:
            command = int(input().split(' ')[0])
        except:
            continue

        if command < 1 or command > 4:
            print("Invalid command")
        elif command == 1:
            set_loc(user)
            send_loc(user,own_port)
        elif command == 2:
            print("Actual location")
            print("Latitude: " + str(user.latitude))
            print("Longitude: " + str(user.longitude))
        elif command == 3:
            user.list_sns_codes()

    quit_program = True

    print_console("Sent Tokens: ")
    print_console(user.sentTokens)
    print_console("Recv Tokens: ")
    print_console(user.recvTokens)
    t1.join()
    t2.join()
    
    logoutUser(user)

    # STORES user
    print_console("Stores user pickle")
    pickle_out_file = open(user.name,'wb')
    pickle.dump(user,pickle_out_file)
    pickle_out_file.close()