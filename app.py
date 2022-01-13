import sys
from geopy.geocoders import Nominatim
import socket, ssl

import threading
import comm
import random

import udp_server
import udp_client

import datetime
import time

from math import radians, sin,cos,sqrt,asin

import fcntl
import struct

# globals

server_IP = '192.168.0.1'
server_port = 60000

I_14_DAYS_IN_SECONDS = 60 * 60 * 24 * 14

own_port = 60000
other_port = 60000
own_port_b = 60001
other_port_b = 60001

key = ""
cert = ""

def calc_distance(lat1,lon1,lat2,lon2):
    lat1,lon1 = radians(lat1),radians(lon1)
    lat2,lon2 = radians(lat2),radians(lon2)

    dlon = lon2-lon1
    dlat = lat2-lat2
    trig = pow(sin(dlat/2),2) + cos(lat1) * cos(lat2) * pow(sin(dlon/2),2)
    Radius = 6371
    return 2 * asin(sqrt(trig)) * Radius

def send_message(msg, host, port):
    global key, cert
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile=key, certfile=cert)

    client.connect((host, port))
    client.send(msg.encode("utf-8"))
    client.close()

    print("To (host,port): " + str(host) + "," + str(port) + ". Sent: " + msg)

def treat_loc(client_address,lat,lon,user):
    latitude = user.latitude
    longitude = user.longitude
    curr_token = user.actualToken
    dist = calc_distance(latitude,longitude,lon,lat)
    if dist <= 5:
        # send TOK
        ans = 'TOK:' + str(curr_token) + ":\n"
        #send_message(ans, client_address[0], client_address[1])
        send_message(ans, client_address[0], 60000)

def treat_tok(client_address,o_tok,user):
    
    curr_token = user.actualToken
    curr_loc = user.actualLoc
    recvTokens = user.recvTokens

    now = datetime.datetime.now()
    recvTokens[o_tok] = {'location':curr_loc,'datetime':now}

    
    sentTokens[curr_token] = {'datetime':now}

    ans = "RTOK:" + str(curr_token) + ":\n"
    #send_message(ans, client_address[0], client_address[1])
    send_message(ans, client_address[0], 60000)

def treat_rtok(client_address, o_tok,user):
    curr_loc = user.actualLoc
    recvTokens = user.recvTokens

    now = datetime.datetime.now()
    recvTokens[o_tok] = {'location':curr_loc,'datetime':now}

def treat_cod(client_address,sns_code, user):
    global I_14_DAYS_IN_SECONDS, server_IP, server_port

    sentTokens = user.sentTokens

    print("You received a code from SNS due to your positive COVID test: " + sns_code + ".")
    user.add_sns_code(sns_code)

    # filter sentTokens maintaining only the last 14 days
    now = datetime.datetime.now()
    for key in sentTokens:
        delta = now - sentTokens[key]['datetime']

        """if(delta > I_14_DAYS_IN_SECONDS):
            sentTokens.pop(key)"""
        if(delta > datetime.timedelta(days = 14)):
            sentTokens.pop(key)


    #ans = "POS:" + str(sns_code) + ":"
    ans = "POS:" + sns_code + ":"
    for tok in sentTokens:
        ans += str(tok) + ':'
    ans = ans + "\n"
    print("send cod")
    send_message(ans, server_IP, server_port)

def treat_con(client_address,server_tokens,user):

    global I_14_DAYS_IN_SECONDS

    
    recvTokens = user.recvTokens

    # filter recvTokens maintaining only the last 14 days
    now = datetime.datetime.now()
    for key in recvTokens:
        delta = now - recvTokens[key]['datetime']

        """if(delta > I_14_DAYS_IN_SECONDS):
            recvTokens.pop(key)"""

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

def treat_message(msg, client_address, user):

    # parse message
    msg_args = msg.split(':')

    if(msg_args[-1] != '\n'): # wrong formatting - ignore
        return

    # LOC E RECEBIDO NO PORTO 60001 POR LIGACOES UDP 
    # if(msg_args[0] == 'LOC'): # LOC:<lat>:<lon>:\n
    #     o_lat, o_lon = 0, 0
    #     try:
    #         assert(len(msg_args) == 4)
    #         o_lat = float(msg_args[1])
    #         o_lon = float(msg_args[2])
    #     except:
    #         return
    #     treat_loc(client_address,o_lat,o_lon,user)

    if(msg_args[0] == 'TOK'):
        o_tok = 0
        try:
            assert(len(msg_args) == 3)
            o_tok = int(msg_args[1])
        except:
            return
        treat_tok(client_address,o_tok,user)

    elif(msg_args[0] == 'RTOK'):
        o_tok = 0
        try:
            assert(len(msg_args) == 3)
            o_tok = int(msg_args[1])
        except:
            return
        treat_rtok(client_address,o_tok,user)
    elif(msg_args[0] == 'COD'):
        sns_code = 0
        try:
            assert(len(msg_args) == 3)
            #sns_code = int(msg_args[1])
            sns_code = msg_args[1]
        except:
            return

        treat_cod(client_address,sns_code,user)


    elif(msg_args[0] == 'CON'):
        server_tokens = []
        for i in range(1,len(msg_args)-1):
            server_tokens += [msg_args[i]]
        

        treat_con(client_address,server_tokens,user)

def listen_all_tcp(own_port, user):
    global key, cert

    HOST = get_ip_address('enp0s3')

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server = ssl.wrap_socket(
        server, server_side=True, keyfile=key, certfile=cert
    )
    server.bind((HOST, own_port))
    server.listen(5)

    threads_lst = []

    while True:
        connection, client_address = server.accept()
        msg = ""
        while True:
            data = connection.recv(1024).decode('utf-8')
            if not data:
                break
            msg = msg + data
        print("Received: ")
        print(msg)
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


def listen_loc(own_port_b, user):
    port = own_port_b
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    # Enable broadcasting mode
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    client.bind(("", port))

    
    threads_lst = []

    while True:
        data, addr = client.recvfrom(1024)

        if addr[0] == get_ip_address('enp0s3'):
            continue

        data = data.decode('utf-8')
        print("received message: %s"%data)

        data_args = data.split(':')

        if(len(data_args) != 4 or data_args[-1] != '\n' or data_args[0] != 'LOC'): # invalid format
            continue
        
        lat, lon = 0,0
        try:
            lat = float(data_args[1])
            lon = float(data_args[2])
        except:
            continue # invalid format


        t1 = threading.Thread(target= treat_loc, args=(addr,lat,lon,user,))
        t1.start()

        idx_t = 0
        while idx_t < len(threads_lst):
            if(threads_lst[idx_t].is_alive()):
                idx_t += 1
            else:
                threads_lst[idx_t].join()
                threads_lst.pop(idx_t)

        threads_lst += [t1]


        




def location_by_coord(latitude, longitude):
        return ""
        """coord = str(latitude) + ", " + str(longitude)

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
            return locationInfo"""

class User:
    def __init__(self, name, sentTokens, recvTokens, latitude, longitude):
        self.name = name
        self.createNewToken()
        self.sentTokens = sentTokens
        self.recvTokens = recvTokens
        self.latitude = latitude
        self.longitude = longitude
        self.actualLoc = location_by_coord(latitude,longitude)
        self.sns_codes = []
    def createNewToken(self):
        self.actualToken = random.randint(1,1000000000)
    def add_sns_code(self,code):
        self.sns_codes += [code]
    def list_sns_codes(self):
        print("SNS codes:")
        for code in self.sns_codes:
            print("\t" + code)

    
def usage():
    sys.stderr.write('Usage: python3 app.py\nor\nUsage: python3 app.py user.txt\n')
    sys.exit(1)

def set_loc(user):
    #user.createNewToken()
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


if __name__ == '__main__':

    if len(sys.argv) != 1 and len(sys.argv) != 2:
        usage()



    Nomi_locator = Nominatim(user_agent="My App")

    print("Helcome to the app \'Covid Contacts Trace\'")
    sentTokens = {}
    recvTokens = {}
    latitude = 0
    longitude = 0
    
    if len(sys.argv) == 1:
        name = input("Username: ")
        print("Set your actual location")
        latitude = float(input("Latitude: "))
        longitude = float(input("Longitude: "))
        key = input("Key: ")
        cert = input("Cert: ")

    
    if len(sys.argv) == 2:
        #get info
        pass
    
    user = User(name, sentTokens, recvTokens, latitude, longitude)
    
    #own_port = int(input("own port: "))
    #other_port = int(input("other port: "))

    #own_port_b = int(input("own port for broadcast: "))
    #other_port_b = int(input("other port for broadcast: "))

    own_port = 60000
    other_port = 60000
    own_port_b = 60001
    other_port_b = 60001


    # listen should run in background
    t1 = threading.Thread(target = listen_all_tcp, args = (own_port,user) )
    t1.start()
    t2 = threading.Thread(target = listen_loc, args = (own_port_b,user) )
    t2.start()

    time.sleep(1)

    udp_server.broadcast_loc(user.latitude, user.longitude, other_port_b)

    command = 0
    while command != 6:
        print("-=[ \'Covid Contacts Trace\' Menu ]=-")
        print("1 - Set user name")
        print("2 - Set actual loaction")
        print("3 - Show actual location")
        print("4 - Insert SNS code")
        print("5 - Check codes sent by SNS")
        print("6 - Quit")
        command = int(input().split(' ')[0])

        if command < 1 or command > 6:
            print("Invalid command")
        elif command == 1:
            user.name = input("Insert new name: ")
        elif command == 2:
            set_loc(user)
            udp_server.broadcast_loc(user.latitude, user.longitude, other_port_b)
        elif command == 3:
            print("Actual location")
            print("Latitude: " + str(user.latitude))
            print("Longitude: " + str(user.longitude))
        elif command == 4:
            pass
        elif command == 5:
            user.list_sns_codes()
        
    """print("Sent: ")
    print(user.sentTokens)
    print("Recv: ")
    print(user.recvTokens)"""
    t1.join()
    t2.join()