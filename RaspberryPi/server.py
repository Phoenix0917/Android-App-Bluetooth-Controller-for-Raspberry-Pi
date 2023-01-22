from bluetooth import *

def data_interpreter(val):
    command = val[0:2]
    print(command)
    return



server_sock=BluetoothSocket( RFCOMM )
server_sock.bind(("", PORT_ANY))
server_sock.listen(1)
advertise_service( server_sock , "SampleServer" , service_classes = [ SERIAL_PORT_CLASS ] , profiles = [SERIAL_PORT_PROFILE ] )

client_sock , client_info = server_sock.accept( )
print ("Accepted connection from " , client_info)
client_sock.send( "Hello Client" )

while True:
    data = client_sock.recv(1024)
    print ("received: " , data)
    data_interpreter(data)



#client_sock.close( )
#server_sock.close( )

