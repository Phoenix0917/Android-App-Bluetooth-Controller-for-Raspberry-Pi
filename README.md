# ECE495-SnrDes
Senior design search and rescue robot for Boeing.  Project reference number F22-21-BOE1.

Note the following requirements for the program to run as expected: 
Python 3.8.3
Pybluez 0.30 - commit 4d46ce1
Kivy 2.1.0


To get Pybluez functioning on Raspbian:
unzip Pybluez git folder
enter command 'sudo apt-get install libbluetooth-dev' - https://github.com/pybluez/pybluez/issues/236
enter command 'sudo python3 setup.py install' - https://pybluez.readthedocs.io/en/latest/install.html
follow commands at https://stackoverflow.com/questions/36675931/bluetooth-btcommon-bluetootherror-2-no-such-file-or-directory
follow commands at https://stackoverflow.com/questions/37913796/bluetooth-error-no-advertisable-device
run code as sudo python3 


Note also the pi must either be paired (or perhaps atleast in discovery mode) to connect via bluetooth.
