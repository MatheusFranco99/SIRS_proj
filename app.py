import sys
from geopy.geocoders import Nominatim
import socket, ssl

import threading
import comm
import random

import udp_server
import udp_client

# RECEBE:

# do SNS quando user esta positivo pra covid19
# COD:<sns_code>:\n"

# de outro user quando muda de posicao
# LOC:<latitude>:<longitude>:\n

# de outro user quando percebe que esta proximo de si
# TOK:<mytoken>:\n

# de outro user em resposta a mensagem TOK enviada
# RTOK:<mytoken>:\n

# do server quando alguem tem covid
# CON:(<token>:)*\n


# ENVIA:

# Pra outros utilizadores: Sempre que altera a sua localizacao
# LOC:<latitude>:<longitude>:\n

# Pra outro utilizador: Sempre que recebe uma localizacao da qual esta proximo
# TOK:<mytoken>:\n

# Pra outro utilizador: Sempre que recebe "TOK:<token>:\n"
# RTOK:<mytoken>:\n


# Pro servidor: Sempre que recebe "COD:<sns_code>:\n" do sns
# POS:<sns_code>:(<encrypt_token>:)*\n


def listen(own_port):

    HOST = "127.0.0.1" #"192.168.1.254"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server = ssl.wrap_socket(
        server, server_side=True, keyfile="server.key", certfile="server.crt"
    )
    server.bind((HOST, own_port))
    server.listen(5)

    while True:
        connection, client_address = server.accept()
        msg = ""
        while True:
            data = connection.recv(1024).decode('utf-8')
            if not data:
                break
            msg = msg + data
            print("Received: ")
            print(data)
        
        # parse message
        #msg = msg.split(':')


class RecvToken:
    def __init__(self, token, latitude, longitude):
        self.token = token

        coord = latitude + ", " + longitude

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
            self.location = "Unknown"
        else:
            size = len(locationInfo)
            self.location = locationInfo[:size - 2]

class User:
    def __init__(self, name, actualToken, sentTokens, recvTokens, latitude, longitude):
        self.name = name
        self.actualToken = actualToken
        self.sentTokens = sentTokens
        self.recvTokens = recvTokens
        self.latitude = latitude
        self.longitude = longitude

    
def usage():
    sys.stderr.write('Usage: python3 app.py\nor\nUsage: python3 app.py user.txt\n')
    sys.exit(1)

def set_loc(user):
    print("Set your actual location")
    user.latitude = input("Latitude: ")
    user.longitude = input("Longitude: ")

def send_loc(lat,long,other_port):

    HOST = "127.0.0.1" #"192.168.1.1"

    #ips = comm.get_IPs()


    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = ssl.wrap_socket(client, keyfile="client.key", certfile="client.crt")

    client.connect((HOST, other_port))

    while True:
        from time import sleep
        s = "LOC:" + str(lat) + ":" + str(long) + ":\n"
        se = s.encode("utf-8")
        client.send(se)
        sleep(1)

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
    
    if len(sys.argv) == 2:
        #get info
        pass
    
    #getToken()
    user = User(name, 0, sentTokens, recvTokens, latitude, longitude)
    
    own_port = int(input("own port: "))
    other_port = int(input("other port: "))

    own_port_b = int(input("own port for broadcast: "))
    other_port_b = int(input("other port for broadcast: "))
    # listen should run in background
    t1 = threading.Thread(target = listen, args = (own_port,) )
    t1.start()
    t2 = threading.Thread(target = udp_client.recv_loc, args = (own_port_b,) )
    t2.start()

    set_loc(user)
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
            pass
        
    #recvtkn = RecvToken(10, latitude, longitude)
    #print(recvtkn.token)
    #print(recvtkn.location)

    #send_loc(latitude, longitude, other_port)



    # wait in loop for command line inputs (as position shift)
        # send LOK in case of new position

    #while True:
    #    cmd = input("> ")
        #move:<lat>:<long>

    t1.join()
    te.join()