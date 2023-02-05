from bluetooth import *
import RPi.GPIO as GPIO
import os

os.system("sudo hciconfig hci0 piscan")
os.system("echo changed bluetooth advertise setting")

LMspeed = 33 # PWM pin
LMdir = 37
RMspeed = 32 #PWM pin
RMdir = 36

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LMspeed, GPIO.OUT)
GPIO.setup(LMdir, GPIO.OUT)
GPIO.setup(RMspeed, GPIO.OUT)
GPIO.setup(RMdir, GPIO.OUT)

LMpwm = GPIO.PWM(LMspeed, 1000) # set up pwm on this pin with frequency 1000
RMpwm = GPIO.PWM(RMspeed, 1000) # set up pwm on this pin with frequency 1000
LMpwm.start(0)
RMpwm.start(0)
GPIO.output(LMdir, GPIO.LOW)
GPIO.output(RMdir, GPIO.LOW)



def data_interpreter(val):
    val = val.decode('ascii')
    command = val[0:2]
    info = val[3: val.find('*')]
    print(command)
    print(info)
    if command == 'LM':
        velocity = float(info)
        if velocity <= 0:
            GPIO.output(LMdir, GPIO.LOW) # going reverse
            speed = velocity * -1
        elif velocity > 0:
            GPIO.output(LMdir, GPIO.HIGH) # going forward
            speed = velocity
        LMpwm.ChangeDutyCycle(speed)

    elif command == 'RM':
        velocity = float(info)
        if velocity <= 0:
            GPIO.output(RMdir, GPIO.LOW) # going reverse
            speed = velocity * -1
        elif velocity > 0:
            GPIO.output(RMdir, GPIO.HIGH) # going forward
            speed = velocity
        RMpwm.ChangeDutyCycle(speed)
        
    elif command == 'SY':
        if info == 'hello':
            print("successful BT connection")
        elif info == 'kill':
            try:
                server_sock.close()
                os.system("sudo shutdown -h now")
            except:
                os.system("sudo shutdown -h now")
                
    return



server_sock = BluetoothSocket(RFCOMM)
server_sock.bind(("", PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]
uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"


while True:
    advertise_service(server_sock, "TestPiServer",
                      service_id = uuid,
                      service_classes = [uuid, SERIAL_PORT_CLASS],
                      profiles = [SERIAL_PORT_PROFILE],
                      #protocols = [OBEX_UUID]
                      )
    print("Waiting for connection")
    client_sock , client_info = server_sock.accept( )
    print ("Accepted connection from " , client_info)

    while True:
        try:
            data = client_sock.recv(1024)
        except:
            break
        print ("received: " , data)
        data_interpreter(data)
        

    #client_sock.close( )
    stop_advertising(server_sock)
    LMpwm.ChangeDutyCycle(0)
    RMpwm.ChangeDutyCycle(0)
    GPIO.output(LMdir, GPIO.LOW)
    GPIO.output(RMdir, GPIO.LOW)


