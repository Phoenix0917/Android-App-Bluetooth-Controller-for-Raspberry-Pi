# Same as before, with a kivy-based UI

'''
Bluetooth/Pyjnius example
=========================

This was used to send some bytes to an arduino via bluetooth.
The app must have BLUETOOTH and BLUETOOTH_ADMIN permissions (well, i didn't
tested without BLUETOOTH_ADMIN, maybe it works.)

Connect your device to your phone, via the bluetooth menu. After the
pairing is done, you'll be able to use it in the app.
'''

from jnius import autoclass
#import logging




BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
#logging.info("Inside LOG BT")
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
BluetoothSocket = autoclass('android.bluetooth.BluetoothSocket')
UUID = autoclass('java.util.UUID')
#writer = autoclass('java.io.OutputStreamWriter')


#hello = autoclass('java.string')

def get_socket_stream(name):
    print("		*** Starting BT search")
    paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
    print("		***" + str(paired_devices))
    print("		*** Finished BT search")
    my_sock = None
    
    for device in paired_devices:
        print(str(device))
        print("		***" + str(device.getName()))
        print("		***" + str(device.getAddress()))
        print("		***" + str(device.getUuids()))
        IDs = device.getUuids()
        for ID in IDs:
           print("		***" + str(ID.getUuid()))
           
        if device.getName() == 'hacksi-2019-15':
            piUUID = UUID.fromString("94F39D29-7D6D-437D-973B-FBA39E49D4EE")
            my_sock = device.createRfcommSocketToServiceRecord(piUUID)
            print("		*** Socket created")
            my_sock.connect()
            print("		*** Socket connected")
            send_stream = my_sock.getOutputStream()
            print("		***" + str(type(send_stream)))
            break
            
            #my_sock.connect()
            #print("		*** Socket connected")
            
    
        #if device.getName() == name:
            #socket = device.createRfcommSocketToServiceRecord(
                #UUID.fromString("00001101-0000-1000-8000-00805F9B34FB"))
            #recv_stream = socket.getInputStream()
            #send_stream = socket.getOutputStream()
            #break
    #socket = device.createRFcommSocketToServiceRecord()
    #socket.connect()
    #return recv_stream, send_stream
    return 1, send_stream

if __name__ == '__main__':
    kv = '''
BoxLayout:
    Button:
        text: '0'
        on_release: app.reset([b1, b2, b3, b4, b5])

    ToggleButton:
        id: b1
        text: '1'
        on_release: app.send(self.text)

    ToggleButton:
        id: b2
        text: '2'
        on_release: app.send(self.text)

    ToggleButton:
        id: b3
        text: '3'
        on_release: app.send(self.text)

    ToggleButton:
        id: b4
        text: '4'
        on_release: app.send(self.text)

    ToggleButton:
        id: b5
        text: '5'
        on_release: app.send(self.text)
    '''
    from kivy.lang import Builder
    from kivy.app import App

    class Bluetooth(App):
        def build(self):
            self.recv_stream, self.send_stream = get_socket_stream('linvor')
            print("		***" + str(type(self.send_stream)))
            return Builder.load_string(kv)

        def send(self, cmd):
            i = [27, 64]
            pre = bytearray(i)
            cmd2 = 'hello server\n'.encode('UTF-8')
            pre.extend(cmd2)

            print("		*** sending message")
            print("======================================")
            print(dir(self.send_stream))
            print(self.send_stream)
            self.send_stream.write(b'my binary string')
            #self.send_stream.write("my string")
            #self.send_stream.write(cmd2)
            #self.send_stream.write('{}\n'.format(cmd))
            self.send_stream.flush()

        def reset(self, btns):
            for btn in btns:
                btn.state = 'normal'
            self.send('0\n')

    Bluetooth().run()

