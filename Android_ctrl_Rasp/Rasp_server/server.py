from bluetooth import *
import RPi.GPIO as GPIO
import os
from gpiozero import Servo
from time import sleep
import pigpio

#imports for object detection
from detecto import core, utils, visualize
from detecto.visualize import show_labeled_image, plot_prediction_grid
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
from datetime import datetime
from picamera import PiCamera

os.system("sudo hciconfig hci0 piscan")
os.system("echo changed bluetooth advertise setting")

LMspeed = 33 # PWM pin
LMdir = 37
RMspeed = 32 #PWM pin
RMdir = 36
CLwidth = 23
ARangle = 24
os.system("sudo pigpiod")

pwm=pigpio.pi()


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LMspeed, GPIO.OUT)
GPIO.setup(LMdir, GPIO.OUT)
GPIO.setup(RMspeed, GPIO.OUT)
GPIO.setup(RMdir, GPIO.OUT)

pwm.set_mode(CLwidth,pigpio.OUTPUT) ##setup servo for claw
pwm.set_PWM_frequency(CLwidth,50)
pwm.set_mode(ARangle,pigpio.OUTPUT) ##setup servo for arm
pwm.set_PWM_frequency(ARangle,50)

LMpwm = GPIO.PWM(LMspeed, 1000) # set up pwm on this pin with frequency 1000
RMpwm = GPIO.PWM(RMspeed, 1000) # set up pwm on this pin with frequency 1000
LMpwm.start(0)
RMpwm.start(0)
GPIO.output(LMdir, GPIO.LOW)
GPIO.output(RMdir, GPIO.LOW)
model = core.Model.load('/content/drive/MyDrive/ECE495/objdetector.pth', ['can', 'sphere', 'cube', 'log'])


#Modifying code from detecto so can save image onto pi
def show_labeled_image_modified(image, boxes, labels=None, path=None):
    """Show the image along with the specified boxes around detected objects.
    Also displays each box's label if a list of labels is provided.
    :param image: The image to plot. If the image is a normalized
        torch.Tensor object, it will automatically be reverse-normalized
        and converted to a PIL image for plotting.
    :type image: numpy.ndarray or torch.Tensor
    :param boxes: A torch tensor of size (N, 4) where N is the number
        of boxes to plot, or simply size 4 if N is 1.
    :type boxes: torch.Tensor
    :param labels: (Optional) A list of size N giving the labels of
            each box (labels[i] corresponds to boxes[i]). Defaults to None.
    :type labels: torch.Tensor or None
    **Example**::
        >>> from detecto.core import Model
        >>> from detecto.utils import read_image
        >>> from detecto.visualize import show_labeled_image
        >>> model = Model.load('model_weights.pth', ['tick', 'gate'])
        >>> image = read_image('image.jpg')
        >>> labels, boxes, scores = model.predict(image)
        >>> show_labeled_image(image, boxes, labels)
    """

    fig, ax = plt.subplots(1)
    # If the image is already a tensor, convert it back to a PILImage
    # and reverse normalize it
    ax.imshow(image)
    

    # Show a single box or multiple if provided
    if boxes.ndim == 1:
        boxes = boxes.view(1, 4)

    if labels is not None and len(labels) ==1:
        labels = [labels]

    # Plot each box
    for i in range(boxes.shape[0]):
        box = boxes[i]
        width, height = (box[2] - box[0]).item(), (box[3] - box[1]).item()
        initial_pos = (box[0].item(), box[1].item())
        rect = patches.Rectangle(initial_pos,  width, height, linewidth=1,
                                 edgecolor='r', facecolor='none')
        if labels:
            ax.text(box[0] + 5, box[1] - 5, '{}'.format(labels[i]), color='red')

        ax.add_patch(rect)
    
    if path is not None:
      plt.savefig(path)
    
    plt.show()



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
        width = float(info)
        pwm.set_servo_pulsewidth(CLwidth,width)
            
    elif command == 'AR':
        angle = float(info)
        pwm.set_servo_pulsewidth(ARangle,angle)
        
    elif command == 'SY':
        if info == 'hello':
            print("successful BT connection")
        elif info == 'kill':
            try:
                server_sock.close()
                os.system("sudo shutdown -h now")
            except:
                os.system("sudo shutdown -h now")

    elif command == 'OD':
        #Take picture
        camera = PiCamera()
        sleep(.5)
        camera.capture("./picture.jpg")
        sleep(.5)
        camera.close()
        #Read image and output objects in image. Saves picture to folder
        image = utils.read_image('./picture.jpg') 
        predictions = model.predict(image)
        labels, boxes, scores = predictions

        thresh=0.6
        filtered_indices=np.where(scores>thresh)
        filtered_scores=scores[filtered_indices]
        filtered_boxes=boxes[filtered_indices]
        num_list = filtered_indices[0].tolist()
        filtered_labels = [labels[i] for i in num_list]
        
        #add for loop here to light up LEDs based on what objects are in labels list
        print(filtered_labels)
        path = './' +datetime.now().strftime("%d_%m_%Y_%H_%M_%S") + '.png'
        show_labeled_image_modified(image, filtered_boxes, filtered_labels,path)

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
    pwm.set_PWM_dutycycle(CLwidth,0)
    pwm.set_PWM_frequency(CLwidth,0)
    pwm.set_PWM_dutycycle(ARangle,0)
    pwm.set_PWM_frequency(ARangle,0)
    os.system("sudo killall pigpiod")
