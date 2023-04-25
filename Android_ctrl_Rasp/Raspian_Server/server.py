from bluetooth import *
import RPi.GPIO as GPIO
import os
from gpiozero import Servo
from time import sleep
from picamera import PiCamera
#import pigpio
import ThreadTracing

os.system("sudo hciconfig hci0 piscan")
os.system("echo changed bluetooth advertise setting")
os.system("sudo pigpiod")
sleep(.5)
#pwm=pigpio.pi()
LMspeed = 32 # PWM pin
LMdir = 36
RMspeed = 33 #PWM pin
RMdir = 37
CLwidth = 23
ARangle = 24
MDsig = 11
ASangle=4


camera=PiCamera()
camera.rotation=180
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LMspeed, GPIO.OUT)
GPIO.setup(LMdir, GPIO.OUT)
GPIO.setup(RMspeed, GPIO.OUT)
GPIO.setup(RMdir, GPIO.OUT)
#pwm.set_mode(CLwidth,pigpio.OUTPUT) ##setup servo for claw and arm
#pwm.set_PWM_frequency(CLwidth,50)
#pwm.set_mode(ARangle,pigpio.OUTPUT)
#pwm.set_PWM_frequency(ARangle,50)
#pwm.set_mode(ASangle,pigpio.OUTPUT)
#pwm.set_PWM_frequency(ASangle,50)
GPIO.setup(MDsig, GPIO.OUT)

LMpwm = GPIO.PWM(LMspeed, 1000) # set up pwm on this pin with frequency 1000
RMpwm = GPIO.PWM(RMspeed, 1000) # set up pwm on this pin with frequency 1000
LMpwm.start(0)
RMpwm.start(0)
GPIO.output(LMdir, GPIO.LOW)
GPIO.output(RMdir, GPIO.LOW)
#pwm.set_servo_pulsewidth(CLwidth,2500)
sleep(1)
#pwm.set_servo_pulsewidth(ARangle,750)
#pwm.set_servo_pulsewidth(ASangle,1900)
GPIO.output(MDsig, GPIO.LOW)



def image_sender_start():
    global image_sender_sock
    global image_reciever_info
    global image_reciever_sock
    global image_sender_sock
    global uuid2
    
    advertise_service(image_sender_sock, "ImageSender",
          service_id = uuid2,
          service_classes = [uuid2, SERIAL_PORT_CLASS],
          profiles = [SERIAL_PORT_PROFILE],
          #protocols = [OBEX_UUID]
          )
    
    print("Waiting for image reciever client")
    image_reciever_sock , image_reciever_info = image_sender_sock.accept( )
    print ("Accepted image reciever connection from " , image_reciever_info)


def data_interpreter(recv_bin):
    recv_str = recv_bin.decode('ascii')
    instrs = recv_str.split("*")
    for instr in instrs:
        command = instr[0:2]
        info = instr[3:len(instr)]
        print(command)
        print(info)
        if command == 'LM':
            try:
               
            
                velocity = float(info)
                if velocity <= 0:
                    GPIO.output(LMdir, GPIO.LOW) # going reverse
                    speed = velocity * -1
                elif velocity > 0:
                    GPIO.output(LMdir, GPIO.HIGH) # going forward
                    speed = velocity
                LMpwm.ChangeDutyCycle(speed)
            except:
                print(info)
                
        elif command == 'RM':
            try:
                velocity = float(info)
            
                if velocity <= 0:
                    GPIO.output(RMdir, GPIO.LOW) # going reverse
                    speed = velocity * -1
                elif velocity > 0:
                    GPIO.output(RMdir, GPIO.HIGH) # going forward
                    speed = velocity
                RMpwm.ChangeDutyCycle(speed)
            except:
                print(info)
        elif command == 'CL':
            width = float(info)
            pwm.set_servo_pulsewidth(CLwidth,width)
                
        elif command == 'AR':
            angle = float(info)
            pwm.set_servo_pulsewidth(ARangle,angle)
            
        elif command == 'AS':
            angle = float(info)
            pwm.set_servo_pulsewidth(ASangle,angle)    
        
        elif command == "OD":
            # create thread to handle entire command anytime it is recieved
            global image_reciever_info
            global image_reciever_sock
            global image_sender_sock
            global await_image_reciever_thread
            
            camera.capture("/home/dylan/Pictures/random.jpg")
            sleep(.1)
            print('done')
            
            if image_reciever_sock == None: # only not none if socket setup finished in thread
                print("Socket not setup to recieve image")
            else:
                try:
                    file = open('/home/dylan/Pictures/random.jpg', 'rb')
                    print('opened')
                    image_data = file.read(2048)
                    while image_data:
                        image_reciever_sock.send(image_data)
                        image_data = file.read(2048)
                        
                    image_reciever_sock.send("***")
                    
                except:
                    print("Socket became unavailable since connecting")
                    stop_advertising(image_sender_sock)
                    image_reciever_sock.close( )
                    image_reciever_sock = None
                    await_image_reciever_thread.kill()
                    await_image_reciever_thread.join()
                    await_image_reciever_thread = ThreadTracing.thread_with_trace(target = image_sender_start)
                    await_image_reciever_thread.start()
            
            
        elif command == 'MD':
            status = info
            print(info)
            if info == '1':
                print("setting high")
                GPIO.output(MDsig, GPIO.HIGH)
            else:
                GPIO.output(MDsig, GPIO.LOW)
                print("setting low")
            
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

image_sender_sock = BluetoothSocket(RFCOMM)
image_sender_sock.bind(("", PORT_ANY))
image_sender_sock.listen(1)


port = server_sock.getsockname()[1]
uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"


uuid2 = "94f39d29-7d6d-437d-973b-fba39e49d4ef"
await_image_reciever_thread = None
image_reciever_sock = None
image_reciever_info = None
await_image_reciever_thread = ThreadTracing.thread_with_trace(target = image_sender_start)


# fork and create thread for running image_sender thread
await_image_reciever_thread.start()

while True:
    advertise_service(server_sock, "TestPiServer",
                      service_id = uuid,
                      service_classes = [uuid, SERIAL_PORT_CLASS],
                      profiles = [SERIAL_PORT_PROFILE],
                      #protocols = [OBEX_UUID]
                      )
                      
    
                  
    print("Waiting for controller connection")
    client_sock , client_info = server_sock.accept( )
    print ("Accepted controller connection from " , client_info)

    while True:
        try:
            data = client_sock.recv(1024)
        except:
            break
        print ("received: " , data)
        data_interpreter(data)
        

    client_sock.close( )
    stop_advertising(server_sock)
    #stop_advertising(image_sender_sock)
    #await_image_reciever_thread.kill()
    #await_image_reciever_thread.join()
    LMpwm.ChangeDutyCycle(0)
    RMpwm.ChangeDutyCycle(0)
    GPIO.output(LMdir, GPIO.LOW)
    GPIO.output(RMdir, GPIO.LOW)
    #pwm.set_PWM_dutycycle(CLwidth,0)
    #pwm.set_PWM_frequency(CLwidth,0)
    #pwm.set_PWM_dutycycle(ARangle,0)
    #pwm.set_PWM_frequency(ARangle,0)
    GPIO.output(MDsig, GPIO.LOW)
    #os.system("sudo killall pigpiod")
    

