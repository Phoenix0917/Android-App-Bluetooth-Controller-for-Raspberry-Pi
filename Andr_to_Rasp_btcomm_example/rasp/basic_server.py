from bluetooth import *
import os

os.system("sudo hciconfig hci0 piscan")
os.system("echo changed bluetooth advertise setting")


server_sock = BluetoothSocket(RFCOMM)
server_sock.bind(("", PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

advertise_service(server_sock, "TestPiServer",
                  service_id = uuid,
                  service_classes = [uuid, SERIAL_PORT_CLASS],
                  profiles = [SERIAL_PORT_PROFILE],
                  #protocols = [OBEX_UUID]
                  )

while True:
    print("Waiting for connection")
    client_sock, client_info = server_sock.accept()
    print("Accepted a Client")

    while True:
        try:
            data = client_sock.recv(1024)
            print("recieved: " + str(data))
        except:
            break
        





'''
while True:
    print("Waiting for connection")
    client_sock, client_info = server_sock.accept()
    print("Accepted a Client")
'''


