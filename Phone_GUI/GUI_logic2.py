from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.graphics import *
from kivy.core.window import Window
import bluetooth

bt_client_sock = None



# found class written by someone on git but this is how I think it may work?
class ModifiedSlider(Slider):
    def __init__(self, **kwargs):
        self.register_event_type('on_release')
        super(ModifiedSlider, self).__init__(**kwargs) # runs parent class init

    def on_release(self):
        self.value = ((self.max - self.min) / 2) + self.min

    def on_touch_up(self, touch): # gets called twice - once by the slider and once by the screen?
        super(ModifiedSlider, self).on_touch_up(touch) # runs parent classes on touch up function and stores it the touch it recieved 
        if touch.grab_current == self: # checks if the current touch is the one that was dispatched for this widget
            self.dispatch('on_release') # starts on_release event
            return True



class ServiceInfo:
    def __init__(self, name, addr, port, proto, button):
        self.name = name
        self.addr = addr
        self.port = port
        self.proto = proto
        self.button = button
        self.paired = False


# Defines different screens
class ControlWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)

    def slide_it(self, *args):
        print(args)
        global bt_client_sock 
        if bt_client_sock != None:
            if args[0] == self.ids.left_motor_control:
                print("this is left motor")
                bt_client_sock.send("LM:" + str(args[1]))
            elif args[0] == self.ids.right_motor_control:
                print("this is right motor")
                bt_client_sock.send("RM:" + str(args[1]))
    
    def on_enter(self, *args):
        if self.manager.current == '': # first entry on program start seems to not update this
            return
        elif bt_client_sock == None:
            self.manager.get_screen("control").ids.status_indicator.text = "Unpaired"
        else:
            self.manager.get_screen("control").ids.status_indicator.text = "Paired"

    
class BluetoothWindow(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.info = []
        self.service_scan_results = []
        self.num_elems_in_1screen = 4
    '''
    def __init__(self, **kw):
        super().__init__(**kw)
        self.current_scroller_population = []
    '''
    def populate_scroller(self, devices):
        print(self.ids.grid1.rows)
        self.ids.grid1.rows = len(devices)
        print(self.ids.grid1.rows)
        for x in range(len(devices)):
            info = Label(
                text = str(devices[x][1]) + '\n' + str(devices[x][0]) + '\n' + str(devices[x][2])
            )
            self.ids.grid1.add_widget(info)

    
    def scanDevice(self):
        #self.ids.grid1.rows = None
        print("Scanning for bluetooth devices:")
        devices = bluetooth.discover_devices(lookup_names = True, lookup_class = True)
        number_of_devices = len(devices)
        print(number_of_devices,"devices found")
        for addr, name, device_class in devices:
            print("")
            print("Device:")
            print("Device Name: %s" % (name))
            print("Device MAC Address: %s" % (addr))
            print("Device Class: %s" % (device_class))
        self.populate_scroller(devices)
     
    
    def scanService(self):
        print(self.ids.Name.text)
        print(self.ids.Address.text)
        print("Scanning for bluetooth services:")

        if self.ids.Name.text != '' and self.ids.Address.text != '':
            tmp = bytes(self.ids.Name.text, 'ISO-8859-1')
            tmp2 = tmp.decode('unicode_escape').encode('raw_unicode_escape')
            try:
                services = bluetooth.find_service(name = tmp2, address=self.ids.Address.text)
            except:
                print("invalid MAC Addr format")
                return

        elif self.ids.Name.text != '':
            tmp = bytes(self.ids.Name.text, 'ISO-8859-1')
            tmp2 = tmp.decode('unicode_escape').encode('raw_unicode_escape')
            services = bluetooth.find_service(name=tmp2)

        elif self.ids.Address.text != '':
            try:
                services = bluetooth.find_service(address=self.ids.Address.text)
            except:
                print("invalid MAC Addr format")
                return

        else:
            services = bluetooth.find_service()
        
        print("hi")
        print(len(services))

        # clean out any prior widgets and data associated with them
        self.ids.grid1.clear_widgets()
        self.service_scan_results = []
        #for x in range(len(self.ids.grid1.rows))

        self.ids.grid1.rows = len(services)
        self.ids.grid1.height = self.ids.grid1.row_default_height * len(services)
        print(len(services) / self.num_elems_in_1screen)


        def resize(instance, value):
            #print('My callback is call from', instance)
            #print('and the a value changed to', value)
            #self.ids.grid1.height = self.ids.scrollie.height * len(services) / self.num_elems
            print(self.ids.grid1.row_default_height)
            self.ids.grid1.height = self.ids.grid1.row_default_height * len(services)
        #self.ids.scrollie.bind(height = resize)
        self.ids.grid1.bind(row_default_height = resize)

        def resize2(instance, value):
            self.ids.grid1.row_default_height = instance.height / self.num_elems_in_1screen
            self.ids.grid1.height = self.ids.grid1.row_default_height * len(services)
        self.ids.scrollie.bind(height = resize2)

        for x in range(len(services)):
            if services[x]['name'] != None:
                tmp_name = str(services[x]['name'])
                tmp_name = tmp_name[2:len(tmp_name) - 2]
            else:
                tmp_name = "Unset Name"
            
            tmp_addr = str(services[x]['host'])
            tmp_port = str(services[x]['port'])
            tmp_proto = str(services[x]['protocol'])

            tmp_button = Button(
                text= "Name:  " + tmp_name + '\nHost:  ' + tmp_addr + '\nPort:  ' + tmp_port + '\nProtocol:  ' + tmp_proto,
                size_hint_x = 1,
                halign= "left",
                valign= "top"
            )




            self.service_scan_results.append(-1)
            self.service_scan_results[x] = ServiceInfo(tmp_name, tmp_addr, tmp_port, tmp_proto, tmp_button)

            self.service_scan_results[x].button.bind(size=self.service_scan_results[x].button.setter('text_size')) 
            

            def pair(instance):
                global bt_client_sock
                for paired_service_index in range(len(self.service_scan_results)):
                    if self.service_scan_results[paired_service_index].button == instance: # found index corresponding with this button
                        break

                if self.service_scan_results[paired_service_index].paired == False: # begin pair attempt
                    if self.service_scan_results[paired_service_index].proto == 'L2CAP':
                        proto = bluetooth.L2CAP
                    elif self.service_scan_results[paired_service_index].proto == 'RFCOMM':
                        proto = bluetooth.RFCOMM
                    else:
                        print("unsupported socket type")
                    addr = self.service_scan_results[paired_service_index].addr
                    port = int(self.service_scan_results[paired_service_index].port)
                    try:
                        bt_client_sock = bluetooth.BluetoothSocket(proto)
                        bt_client_sock.connect((addr, port))
                        bt_client_sock.send("SY: hello server")
                        message = bt_client_sock.recv(80)
                        print(message)
                        print("succesful connection to server")
                    except: 
                        print("unsuccesful connection to server")
                        return
                    instance.background_color= '#79f53b'
                    self.service_scan_results[paired_service_index].paired = True
                    for unpaired_service_index in range(len(self.service_scan_results)):
                        if unpaired_service_index != paired_service_index:
                            self.service_scan_results[unpaired_service_index].button.disabled = True

                else: # begin unpair
                    try:
                        bt_client_sock.close( )
                        bt_client_sock = None
                        print("succesful disconnection from server")
                        self.ids.status_indicator.text = "Unpaired"
                    except:
                        print("unsuccesful disconnection from server")
                        return

                    instance.background_color= [1, 1, 1, 1]
                    self.service_scan_results[paired_service_index].paired = False
                    for unpaired_service_index in range(len(self.service_scan_results)):
                        if unpaired_service_index != paired_service_index:
                            self.service_scan_results[unpaired_service_index].button.disabled = False
            self.service_scan_results[x].button.bind(on_press = pair)





            def resize_label_text_if_window_changes(button, new_width):
                button.font_size = button.width / (5 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen == 1):
                    button.font_size = button.width / (8.5 * self.num_elems_in_1screen)
            self.service_scan_results[x].button.bind(width=resize_label_text_if_window_changes) # when info.height changes run this routine
            self.ids.grid1.add_widget(self.service_scan_results[x].button)

        def resize_label_text_if_elements_changes(grid, new_width):
            for x in range(len(self.service_scan_results)):
                self.service_scan_results[x].button.font_size = self.service_scan_results[x].button.width / (5 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen == 1):
                    self.service_scan_results[x].button.font_size = self.service_scan_results[x].button.width / (8.5 * self.num_elems_in_1screen)
                print("hi")
        self.ids.grid1.bind(row_default_height = resize_label_text_if_elements_changes)


    def pair(instance, value):
        # unpair any previous pair
        instance.color=(1, 0, 0, 1)

        
    '''
    def change_window(instance, value):
        instance.ids.grid1.row_default_height = instance.height / instance.num_elems_in_1screen
    BluetoothWindow.bind(height = change_window)
    '''

    def increment_elem (self):
        self.num_elems_in_1screen = self.num_elems_in_1screen + 1
        self.ids.grid1.row_default_height = self.height / self.num_elems_in_1screen
        print (self.ids.grid1.row_default_height)

    def decrement_elem(self):
        if self.num_elems_in_1screen >= 2:
            self.num_elems_in_1screen = self.num_elems_in_1screen -1
            self.ids.grid1.row_default_height = self.height / self.num_elems_in_1screen
            print (self.ids.grid1.row_default_height)


class WindowManager(ScreenManager):
    pass

kv = Builder.load_file('UserInterface2.kv')

class AwesomeApp(App):
    def build(self):
        return kv

if __name__=="__main__":
    AwesomeApp().run()

