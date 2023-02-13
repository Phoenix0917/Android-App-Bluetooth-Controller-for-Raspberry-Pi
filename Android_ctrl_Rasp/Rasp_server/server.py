from bluetooth import *
import RPi.GPIO as GPIO
import os
from gpiozero import Servo
from time import sleep

os.system("sudo hciconfig hci0 piscan")
os.system("echo changed bluetooth advertise setting")

LMspeed = 33 # PWM pin
LMdir = 37
RMspeed = 32 #PWM pin
RMdir = 36
CLAW_PIN = 16
ARM_PIN = 18





GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LMspeed, GPIO.OUT)
GPIO.setup(LMdir, GPIO.OUT)
GPIO.setup(RMspeed, GPIO.OUT)
GPIO.setup(RMdir, GPIO.OUT)
GPIO.setup(CLAW_PIN,GPIO.OUT) ##setup servo for claw
GPIO.setup(ARM_PIN,GPIO.OUT) ##setup servo for arm


arm=GPIO.PWM(ARM_PIN,50)
claw=GPIO.PWM(CLAW_PIN,50)
LMpwm = GPIO.PWM(LMspeed, 1000) # set up pwm on this pin with frequency 1000
RMpwm = GPIO.PWM(RMspeed, 1000) # set up pwm on this pin with frequency 1000
LMpwm.start(0)
RMpwm.start(0)
GPIO.output(LMdir, GPIO.LOW)
GPIO.output(RMdir, GPIO.LOW)
claw_i=5
claw_j=5


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

    elif command == 'CL':
        global claw_i
        global claw_j
        #If we go to far reset to default then do action.
        #For this, when we press the button to open/close it will open/close one unit so we will have to press button multiple times
        #This solves bug we would have when holding button bc it would be stuck in a while loop blocked from listening
        if(claw_i>1 and claw_i<15 and claw_j>1 and claw_j<15):
            pass
        elif not (claw_i>1 and claw_i<15):
            claw_i = 5
        else:
            claw_j = 5

        arm.ChangeDutyCycle(claw_j)
        claw.ChangeDutyCycle(claw_i)
        if(info=='close'): ##if button 1 is pressed close hand
            claw_i=claw_i+1
            print(claw_i)
        elif(info == 'open'): ## if button 2 is pressed open hand
            claw_i=claw_i-1
            print(claw_i)
        elif(info == 'raise'):
            claw_j=claw_j+1
            print(claw_j)
        elif(info == 'lower'):
            claw_j=claw_j-1
            print(claw_j)
        

            
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

