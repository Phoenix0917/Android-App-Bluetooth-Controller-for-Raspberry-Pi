import sys
from bluetooth import *
import time
from detecto import core, utils, visualize
from detecto.visualize import show_labeled_image, plot_prediction_grid
#from torchvision import transforms
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
from datetime import datetime


os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

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
        input("Enter any character to recieve image - Prevents opening file which means user can't view")
        file = open('new.jpg', 'wb')
        image_chunk = sock.recv(2048)
        while image_chunk:
            if b'***' in image_chunk: # end of file indicator for jpg files
                break
            file.write(image_chunk)
            image_chunk = sock.recv(2048)
        file.close()
        model = core.Model.load('C:/DEV/objdet/ECE495-SnrDes/Android_ctrl_Rasp/Windows_ImageAnalyzer/objdetector.pth', ['can', 'sphere', 'cube', 'log'])
        image = utils.read_image('C:/DEV/objdet/ECE495-SnrDes/new.jpg') 
=       predictions = model.predict(image)
        labels, boxes, scores = predictions

        thresh=0.6
        filtered_indices=np.where(scores>thresh)
        filtered_scores=scores[filtered_indices]
        filtered_boxes=boxes[filtered_indices]
        num_list = filtered_indices[0].tolist()
        filtered_labels = [labels[i] for i in num_list]

        path = './test_png' +datetime.now().strftime("%d_%m_%Y_%H_%M_%S") +'.jpg'
        show_labeled_image_modified(image, filtered_boxes, filtered_labels,path)
except:
    sock.close( )


