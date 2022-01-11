import sys
from geopy.geocoders import Nominatim


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
    def __init__(self, name, actualToken, sentTokens, recvTokens):
        self.name = name
        self.actualToken = actualToken
        self.sentTokens = sentTokens
        self.recvTokens = recvTokens
    
def usage():
    sys.stderr.write('Usage: python3 app.py\nor\nUsage: python3 app.py user.txt\n')
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 1 and len(sys.argv) != 2:
        usage()

    Nomi_locator = Nominatim(user_agent="My App")

    print("Helcome to the app \'Covid Contacts Trace\'")
    sentTokens = {}
    recvTokens = {}
    if len(sys.argv) == 1:
        name = input("Username: ")
    
    if len(sys.argv) == 2:
        #get info
        pass
    
    #getToken()
    user = User(name, 0, sentTokens, recvTokens)
    
    latitude = input("Latitude: ")
    longitude = input("Longitude: ")

    recvtkn = RecvToken(10, latitude, longitude)
    print(recvtkn.token)
    print(recvtkn.location)
    