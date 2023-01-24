
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
import threading
from kivy.clock import Clock

from functools import partial
import ThreadTracing
import time

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

class CustomButton(Button):
    def __init__(self, name, addr, port, proto, **kwargs):
        super(CustomButton, self).__init__(**kwargs)
        # info paramters
        self.name = name
        self.addr = addr
        self.port = port
        self.proto = proto
        self.paired = False
        # button parameters
        self.text = "Name:  " + name + '\nHost:  ' + addr + '\nPort:  ' + port + '\nProtocol:  ' + proto
        self.size_hint_x = 1
        self.halign = "left"
        self.valign = "top"




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
                bt_client_sock.send("LM:" + str(args[1]) + '*')
            elif args[0] == self.ids.right_motor_control:
                print("this is right motor")
                bt_client_sock.send("RM:" + str(args[1]) + '*')
    
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
     
    def update_status(self):
        self.ids.PageStatus_LabelObj.text = "Scanning..."
        #self.ids.ScanDevice.disabled = True
        threading.Thread(target=self.scanService).start()
        #self.ids.PageStatus_LabelObj.text = "Ready"
    
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

        print("Completed Service Scan")
        print(len(services))


        Clock.schedule_once(partial(self.update_service_UI, services)) # run next part on main kivy thread so it can modify GUI


    def update_service_UI(self, services, dt):
        # clean out any prior widgets and data associated with them
        self.ids.grid1.clear_widgets()
        self.service_scan_results = []
        self.service_buttons = []

        # sets number and sizing of rows in grid widget 
        self.ids.grid1.rows = len(services)
        self.ids.grid1.height = self.ids.grid1.row_default_height * len(services)
        print(len(services) / self.num_elems_in_1screen)

        def resize(instance, value):
            print(self.ids.grid1.row_default_height)
            self.ids.grid1.height = self.ids.grid1.row_default_height * len(services)
        self.ids.grid1.bind(row_default_height = resize)

        # resize grid height and default height of rows when scrollview height changes
        def resize2(instance, value):
            self.ids.grid1.row_default_height = instance.height / self.num_elems_in_1screen
            self.ids.grid1.height = self.ids.grid1.row_default_height * len(services) # can probably be removed 
        self.ids.ScanResults_ScrollViewObj.bind(height = resize2)

        # for each service found create a custom button which stores info with it
        for x in range(len(services)):
            if services[x]['name'] != None:
                tmp_name = str(services[x]['name'])
                tmp_name = tmp_name[2:len(tmp_name) - 1]
            else:
                tmp_name = "Unset Name"
            
            tmp_addr = str(services[x]['host'])
            tmp_port = str(services[x]['port'])
            tmp_proto = str(services[x]['protocol'])

            self.service_buttons.append(-1)
            self.service_buttons[x] = CustomButton(tmp_name, tmp_addr, tmp_port, tmp_proto)
            self.service_buttons[x].bind(size = self.service_buttons[x].setter('text_size')) # not entirely sure how this works for adjusting font size
            self.service_buttons[x].bind(on_press = self.pair)

            # change the size of each button's text if the windows size changes
            def resize_button_text_if_window_changes(button, new_width):
                button.font_size = button.width / (5 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen == 1):
                    button.font_size = button.width / (8.5 * self.num_elems_in_1screen)
            self.service_buttons[x].bind(width=resize_button_text_if_window_changes) # when info.height changes run this routine

            self.ids.grid1.add_widget(self.service_buttons[x])

        # change the size of each button's text if the number of elements changes in the grid
        def resize_label_text_if_elements_changes(grid, new_width):
            for x in range(len(self.service_buttons)):
                self.service_buttons[x].font_size = self.service_buttons[x].width / (5 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen == 1):
                    self.service_buttons[x].font_size = self.service_buttons[x].width / (8.5 * self.num_elems_in_1screen)
        self.ids.grid1.bind(row_default_height = resize_label_text_if_elements_changes)
        self.ids.PageStatus_LabelObj.text = "Ready"



    def pair(self, button_inst):
        # disable all buttons
        self.ids.PageStatus_LabelObj.text = "Pairing..."
        for button_other in self.service_buttons:
            button_other.disabled = True
        threading.Thread(target=self.pair_logic, args = [button_inst]).start()
        #return
        #print(x)
        #Clock.schedule_once(partial(self.update_pair_UI))


    def pair_logic(self, button_inst):
        
        global bt_client_sock
        if button_inst.paired == False: # begin pair attempt
            if button_inst.proto == 'L2CAP':
                proto = bluetooth.L2CAP
            elif button_inst.proto == 'RFCOMM':
                proto = bluetooth.RFCOMM
            else:
                print("unsupported socket type")
            addr = button_inst.addr
            port = int(button_inst.port)

            try:
                bt_client_sock = bluetooth.BluetoothSocket(proto)

                connection_status = [] # use a list here because it is mutable (updates everywhere regardless of function/thread called in)
                def connect_attempt(aList, addr, port):
                    try:
                        bt_client_sock.connect((addr, port))
                        aList.append("Connected")
                    except:
                        aList.append("Unconnected")
                print(connection_status)
                killable_thread = ThreadTracing.thread_with_trace(target = connect_attempt, args=[connection_status, addr, port])
                killable_thread.start()
                
                connect_attempt_start_time = time.perf_counter()
                duration = 0
                while len(connection_status) == 0 and duration < 10: # essentially a busy wait but checking for change in connection status, probably change eventually           
                    duration = time.perf_counter() - connect_attempt_start_time
                    print(len(connection_status))
                    time.sleep(0.5)

                print(connection_status)
                if connection_status[0] == "Connected":
                    try:
                        # either send or recv can stall UI update indefinetaly (probably add another busy wait here)
                        bt_client_sock.send("SY: hello server")
                        message = bt_client_sock.recv(80)
                        print(message)
                        print("succesful connection to server")
                        Clock.schedule_once(partial(self.pair_success, button_inst))
                    except:
                        print("unsuccesful connection to server: couldn't confirm with message")
                        bt_client_sock.close()
                        bt_client_sock = None
                        Clock.schedule_once(self.pair_unsuccess)
                elif connection_status[0] == "Unconnected":
                    print("unsuccesful connection to server: invalid params")
                    bt_client_sock.close()
                    bt_client_sock = None
                    Clock.schedule_once(self.pair_unsuccess)
                else:
                    killable_thread.kill()
                    killable_thread.join()
                    print("unsuccesful connection to server: timeout")
                    bt_client_sock.close()
                    bt_client_sock = None
                    Clock.schedule_once(self.pair_unsuccess)
            except:
                print("unsuccesful connection to server: socket not created")
                bt_client_sock = None
                Clock.schedule_once(self.pair_unsuccess)


        else: # begin unpair
            self.ids.PageStatus_LabelObj.text = "Unpairing"
            try:
                bt_client_sock.close( )
                bt_client_sock = None
                print("succesful disconnection from server")
                Clock.schedule_once(partial(self.unpair_success, button_inst))
            except:
                print("unsuccesful disconnection from server")
                Clock.schedule_once(self.unpair_unsucess)


    def pair_success(self, button_inst, dt):
        button_inst.background_color= '#79f53b'
        button_inst.paired = True
        button_inst.disabled = False

        # redundant?
        for button_other in self.service_buttons:
            if button_other != button_inst:
                button_other.disabled = True

        self.ids.PageStatus_LabelObj.text = "Ready"

    def pair_unsuccess(self, dt):
        for button_other in self.service_buttons:
            button_other.disabled = False

        self.ids.PageStatus_LabelObj.text = "Ready"

    def unpair_success(self, button_inst, dt):
        button_inst.background_color = [1, 1, 1, 1]
        button_inst.paired = False

        for button in self.service_buttons:
            button.disabled = False

        self.ids.PageStatus_LabelObj.text = "Ready"

    def unpair_unsucess(self, dt):
        self.ids.PageStatus_LabelObj.text = "Ready"


    def increment_elem (self):
        self.num_elems_in_1screen = self.num_elems_in_1screen + 1
        self.ids.grid1.row_default_height = self.ids.ScanResults_ScrollViewObj.height / self.num_elems_in_1screen
        print (self.ids.grid1.row_default_height)

    def decrement_elem(self):
        if self.num_elems_in_1screen >= 2:
            self.num_elems_in_1screen = self.num_elems_in_1screen -1
            self.ids.grid1.row_default_height = self.ids.ScanResults_ScrollViewObj.height / self.num_elems_in_1screen
            print (self.ids.grid1.row_default_height)


class WindowManager(ScreenManager):
    pass

kv = Builder.load_file('UserInterface2.kv')

class AwesomeApp(App):
    def build(self):
        return kv

if __name__=="__main__":
    AwesomeApp().run()

