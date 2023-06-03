Bluetooth Raspberry Pi Controller
=================================
Project Concluded - See Final_Product_Documentation folder for information on the final results.  End product images and more on the android controller and autonomous codes found on this repo can be seen near the end of the presentationd pdf file. 

ECE495-Senior Design  
Project number F22-21-BOE1.  
Search and rescue Boeing sponsored robot.  


Software List
----------------

| Python | PyBluez | Kivy |
|------|------------|-----|
| 3.8.3 | 0.30 (use non LTS GIT commit 4d46ce1) | 2.1.0 |
| language | bluetooth module | GUI module |
| https://www.python.org/downloads/ | https://pybluez.readthedocs.io/en/latest/install.html | https://kivy.org/doc/stable/gettingstarted/installation.html |

Libraries Used
---------------

Bluetooth  
Functools  
Kivy  
Threading  
Time  
Trace  

Getting Pybluez on Raspbian:
----------------------------

unzip Pybluez git folder  
enter command 'sudo apt-get install libbluetooth-dev'- https://github.com/pybluez/pybluez/issues/236  
enter command 'sudo python3 setup.py install'- https://pybluez.readthedocs.io/en/latest/install.html  
follow commands at https://stackoverflow.com/questions/36675931/bluetooth-btcommon-bluetootherror-2-no-such-file-or-directory  
follow commands at https://stackoverflow.com/questions/37913796/bluetooth-error-no-advertisable-device  
run code as sudo python3   
