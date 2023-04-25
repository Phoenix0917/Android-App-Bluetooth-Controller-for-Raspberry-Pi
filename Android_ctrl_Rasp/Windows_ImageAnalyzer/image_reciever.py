import sys
from bluetooth import *
import time

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ef"
service_matches = find_service(uuid= uuid)
#service_matches = find_service()
#devices = discover_devices(lookup_names= True, lookup_class= True)

if len(service_matches) == 0:
    print ("couldn’t find the service!")
    time.sleep(5)
    sys.exit(0)

image_sender = service_matches[0]

port = image_sender[ "port" ]
name = image_sender[ "name" ]
host = image_sender[ "host" ]

print ("connecting to " , host)
sock=BluetoothSocket( RFCOMM )
sock.connect( (host , port) )
#data = sock.recv(1024)
#print ("received: ", data)

try: 
    while True:
        file = open('new.jpg', 'wb')
        image_chunk = sock.recv(2048)
        while image_chunk:
            if b'\xff\xd9' in image_chunk: # end of file indicator for jpg files
                break
            file.write(image_chunk)
            print(image_chunk)
            image_chunk = sock.recv(2048)
        file.close()

except KeyboardInterrupt:
    sock.close( )


