#For nic dev only: before running, in terminal activate venv by doing snrdsn\Scripts\activate

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.graphics import *
from kivy.core.window import Window
from kivy.clock import Clock

import threading
from functools import partial
import ThreadTracing
import time

# defines classes that can now be declared which are from Java/Android library
from jnius import autoclass
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
BluetoothSocket = autoclass('android.bluetooth.BluetoothSocket')
UUID = autoclass('java.util.UUID')


# can set default window size (for developing when not on final device)
#from kivy.core.window import Window
#Window.size = (555, 270)

bt_client_sock = None
bt_send_stream = None


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

# defines a custom button which stores bluetooth device and UUID data with a button
class CustomButton(Button):
    def __init__(self, device_with_service, service_uuid, **kwargs):
        super(CustomButton, self).__init__(**kwargs)
        # info paramters
        self.device_with_service = device_with_service # android/java bluetooth device object
        self.service_uuid = service_uuid # android/java UUID object
        self.paired = False
        self.connected = False
        # kivy button parameters
        self.text = "    Name:  " + device_with_service.getName() + '\n    Host:  ' + device_with_service.getAddress() + '\n    Service:  ' + service_uuid.toString()
        self.size_hint_x = 1
        self.halign = "left"
        self.valign = "top"



# Defines different screens

class UserWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.killable_thread_claw_movement = None
        self.claw_PWM = 0
        self.killable_thread_arm_movement = None
        self.arm_PWM = 0

    def on_enter(self, *args): # change to not be using bt_client_sock as this doesn't indicate an actually STABLE connection
        if self.manager.current == '': # first entry on program start seems to not update this
            return
        elif bt_client_sock == None:
            self.manager.get_screen("userWindow").ids.status_indicator.text = "Unconnected"
            self.manager.get_screen("userWindow").ids.KillPi_ButtonObj.disabled = True
        else:
            self.manager.get_screen("userWindow").ids.status_indicator.text = "Connected"
            self.manager.get_screen("userWindow").ids.KillPi_ButtonObj.disabled = False

    def adjust_motor_voltage(*args):
        print(args)

    def kill_pi_power(self):
        global bt_send_stream
        print("sending kill command")
        bt_send_stream.write(bytes("SY:kill*", 'utf-8'))


    def control_claw(self, instruction):
        if instruction == 'open':
            self.ids.CloseClaw_ButtonObj.disabled = True

            def slow_open():
                global bt_send_stream
                while self.claw_PWM < 14.8: # prevents value from ever getting above 15
                    if bt_send_stream != None:
                        self.claw_PWM = self.claw_PWM + 0.1
                        bt_send_stream.write(bytes("CL:" + str(self.claw_PWM ) + '*', 'utf-8'))
                        time.sleep(1/30) 
                    else:
                        self.claw_PWM = self.claw_PWM + 0.1
                        print(str(self.claw_PWM))
                        time.sleep(1/30) 

            self.killable_thread_claw_movement = ThreadTracing.thread_with_trace(target = slow_open)
            self.killable_thread_claw_movement.start()

        elif instruction == 'close':
            self.ids.OpenClaw_ButtonObj.disabled = True

            def slow_close():
                global bt_send_stream
                while self.claw_PWM > 0.2: # prevents value from ever dropping below zero
                    if bt_send_stream != None:
                        self.claw_PWM = self.claw_PWM - 0.1
                        bt_send_stream.write(bytes("CL:" + str(self.claw_PWM ) + '*', 'utf-8'))
                        time.sleep(1/30) 
                    else:
                        self.claw_PWM = self.claw_PWM - 0.1
                        print(str(self.claw_PWM))
                        time.sleep(1/30) 

            self.killable_thread_claw_movement = ThreadTracing.thread_with_trace(target = slow_close)
            self.killable_thread_claw_movement.start()

        elif instruction == 'stop':
            self.killable_thread_claw_movement.kill()
            self.killable_thread_claw_movement.join()
            self.ids.OpenClaw_ButtonObj.disabled = False
            self.ids.CloseClaw_ButtonObj.disabled = False

        else:
            print("Invalid instruction passed")


    def control_arm(self, instruction):
        if instruction == 'raise':
            self.ids.LowerArm_ButtonObj.disabled = True

            def slow_raise():
                global bt_send_stream
                while self.arm_PWM < 14.8: # prevents value from ever getting above 15
                    if bt_send_stream != None:
                        self.arm_PWM = self.arm_PWM + 0.1
                        bt_send_stream.write(bytes("AR:" + str(self.arm_PWM ) + '*', 'utf-8'))
                        time.sleep(1/30) 
                    else:
                        self.arm_PWM = self.arm_PWM + 0.1
                        print(str(self.arm_PWM))
                        time.sleep(1/30) 

            self.killable_thread_arm_movement = ThreadTracing.thread_with_trace(target = slow_raise)
            self.killable_thread_arm_movement.start()

        elif instruction == 'lower':
            self.ids.RaiseArm_ButtonObj.disabled = True

            def slow_lower():
                global bt_send_stream
                while self.arm_PWM > 0.2: # prevents value from ever dropping below zero
                    if bt_send_stream != None:
                        self.arm_PWM = self.arm_PWM - 0.1
                        bt_send_stream.write(bytes("AR:" + str(self.arm_PWM ) + '*', 'utf-8'))
                        time.sleep(1/30) 
                    else:
                        self.arm_PWM = self.arm_PWM - 0.1
                        print(str(self.arm_PWM))
                        time.sleep(1/30) 

            self.killable_thread_arm_movement = ThreadTracing.thread_with_trace(target = slow_lower)
            self.killable_thread_arm_movement.start()

        elif instruction == 'stop':
            self.killable_thread_arm_movement.kill()
            self.killable_thread_arm_movement.join()
            self.ids.LowerArm_ButtonObj.disabled = False
            self.ids.RaiseArm_ButtonObj.disabled = False

        else:
            print("Invalid instruction passed")


    def move_robot(self, direction):
        print(direction)
        if direction == 'up':
            rm = '10'
            lm = '10'
        
        elif direction == 'left':
            rm = '10'
            lm = '10'
        
        elif direction == 'right':
            rm = '10'
            lm = '10'
        
        elif direction == 'down':
            rm = '10'
            lm = '10'
        
        elif direction == 'up_left':
            rm = '10'
            lm = '10'
        
        elif direction == 'up_right':
            rm = '10'
            lm = '10'
        
        elif direction == 'down_left':
            rm = '10'
            lm = '10'

        elif direction == 'down_right':
            rm = '10'
            lm = '10'
        
        else:
            rm = '0'
            lm = '0'

        global bt_send_stream 
        if bt_send_stream != None:
            bt_send_stream.write(bytes("LM:" + lm + '*', 'utf-8'))
            bt_send_stream.write(bytes("RM:" + rm + '*', 'utf-8'))

class CalibrationWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
    
    def on_enter(self, *args): # change to not be using bt_client_sock as this doesn't indicate an actually STABLE connection
        if self.manager.current == '': # first entry on program start seems to not update this
            return
        elif bt_client_sock == None:
            self.manager.get_screen("calibration").ids.status_indicator.text = "Unconnected"
            self.manager.get_screen("calibration").ids.KillPi_ButtonObj.disabled = True
        else:
            self.manager.get_screen("calibration").ids.status_indicator.text = "Connected"
            self.manager.get_screen("calibration").ids.KillPi_ButtonObj.disabled = False

    def slide_it(self, *args):
        print(args)
        global bt_send_stream 
        if bt_send_stream != None:
            if args[0] == self.ids.left_motor_control:
                print("this is left motor")
                bt_send_stream.write(bytes("LM:" + str(args[1]) + '*', 'utf-8'))
            elif args[0] == self.ids.right_motor_control:
                print("this is right motor")
                bt_send_stream.write(bytes("RM:" + str(args[1]) + '*', 'utf-8'))

    def kill_pi_power(self):
        global bt_send_stream
        print("sending kill command")
        bt_send_stream.write(bytes("SY:kill*", 'utf-8'))

    
class BluetoothWindow(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.service_buttons = []
        self.num_elems_in_1screen = 3
            

    def scan_paired(self):
        # searches saved paired devices and the services available on when it was paired
        
        number_of_uuids = 0 # used to determine how many rows to create in gridLayout
        print("    *** Starting BT Paired Scan")
        paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
        print("    *** Finished BT Paired Scan")
        print("   *** ")
        for paired_device in paired_devices:
            print("    *** " + str(paired_device.getName()))
            IDs = paired_device.getUuids()
            for ID in IDs:
                print("    ***" + str(ID.toString()))
                number_of_uuids = number_of_uuids + 1
        print("   *** ")        

        # clean out any prior widgets and data associated with them
        self.ids.grid1.clear_widgets()
        self.service_buttons = []

        # sets number and sizing of rows in grid widget 
        self.ids.grid1.rows = number_of_uuids
        self.ids.grid1.height = self.ids.grid1.row_default_height * number_of_uuids

        def resize(instance, value):
            print(self.ids.grid1.row_default_height)
            self.ids.grid1.height = self.ids.grid1.row_default_height * number_of_uuids
        self.ids.grid1.bind(row_default_height = resize)

        # resize grid height and default height of rows when scrollview height changes
        def resize2(instance, value):
            self.ids.grid1.row_default_height = instance.height / self.num_elems_in_1screen
            self.ids.grid1.height = self.ids.grid1.row_default_height * number_of_uuids # can probably be removed 
        self.ids.ScanResults_ScrollViewObj.bind(height = resize2)

        # for each service found create a custom button which stores bluetooth device/uuid info with it
        button_itr = 0
        for paired_device in paired_devices:
            IDs = paired_device.getUuids()
            for ID in IDs:
                # stores created buttons in self.service_buttons
                self.service_buttons.append(-1)
                self.service_buttons[button_itr] = CustomButton(paired_device, ID)
                self.service_buttons[button_itr].bind(size = self.service_buttons[button_itr].setter('text_size')) # not entirely sure how this works for adjusting font size
                self.service_buttons[button_itr].bind(on_press = self.connect)

                # change the size of each button's text if the windows size changes (button width changes if window width changes)
                def resize_button_text_if_window_changes(button, new_width):
                    button.font_size = button.width / (7 * self.num_elems_in_1screen)
                    if (self.num_elems_in_1screen <= 2 ):
                        button.font_size = button.width / (10 * self.num_elems_in_1screen)
                self.service_buttons[button_itr].bind(width=resize_button_text_if_window_changes) # when info.height changes run this routine

                self.ids.grid1.add_widget(self.service_buttons[button_itr])
                button_itr = button_itr + 1

        # change the size of each button's text if the number of elements changes in the grid
        def resize_label_text_if_elements_changes(grid, new_width):
            for x in range(len(self.service_buttons)):
                self.service_buttons[x].font_size = self.service_buttons[x].width / (7 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen <= 2):
                    self.service_buttons[x].font_size = self.service_buttons[x].width / (10 * self.num_elems_in_1screen)
        self.ids.grid1.bind(row_default_height = resize_label_text_if_elements_changes)
        
        self.ids.PageStatus_LabelObj.text = "Ready"
        self.ids.ScanDevice_ButtonObj.disabled = False


    def connect(self, button_inst):
        global bt_client_sock
        # disable all buttons
        if bt_client_sock == None:
            self.ids.PageStatus_LabelObj.text = "Connecting..."
        else:
            self.ids.PageStatus_LabelObj.text = "Disconnecting..."

        for service_button in self.service_buttons:
            service_button.disabled = True

        def connect_logic(button_inst):
            global bt_client_sock
            global bt_send_stream

            if button_inst.connected == False: # attempt connect to server
                try: 
                    print(str(button_inst.device_with_service))
                    print(str(button_inst.service_uuid))
                    bt_client_sock = button_inst.device_with_service.createRfcommSocketToServiceRecord(button_inst.service_uuid.getUuid())
                    print("    *** Socket Created")
                    print(str(bt_client_sock))
                    bt_client_sock.connect()
                    print("    *** Socket Connected")
                    bt_send_stream = bt_client_sock.getOutputStream()
                    print("    *** Stream Created")
                    print(str(bt_send_stream))
                    print("    *** Connect Complete")
                    Clock.schedule_once(partial(self.connect_success, button_inst))
                except:
                    print("    *** Unsuccessful Socket/Stream Creation/Connection")
                    try:
                        bt_client_sock.close()
                        bt_send_stream.close()
                    except:
                        pass
                    bt_client_sock = None
                    bt_send_stream = None
                    Clock.schedule_once(self.connect_unsuccess)

            else: # attempt disconnect from server
                print("    *** Attempting Disconnect")
                try:
                    bt_client_sock.close()
                    bt_send_stream.close()
                    bt_client_sock = None
                    bt_send_stream = None
                    print("    *** Successful Socket/Stream Close/Disconnection")
                    Clock.schedule_once(partial(self.disconnect_success, button_inst))
                except:
                    print("    *** Unsuccessful Socket/Stream Close/Disconnection")

        threading.Thread(target=connect_logic, args = [button_inst]).start()
        
    def connect_success(self, button_inst, dt):
        button_inst.background_color= '#79f53b'
        button_inst.connected = True
        button_inst.disabled = False

        # redundant?
        for service_button in self.service_buttons:
            if service_button != button_inst:
                service_button.disabled = True

        self.ids.PageStatus_LabelObj.text = "Ready"

    def connect_unsuccess(self, dt):
        for service_button in self.service_buttons:
            service_button.disabled = False

        self.ids.PageStatus_LabelObj.text = "Ready"

    def disconnect_success(self, button_inst, dt):
        button_inst.background_color = [1, 1, 1, 1]
        button_inst.connected = False

        for service_button in self.service_buttons:
            service_button.disabled = False
        
        self.ids.PageStatus_LabelObj.text = "Ready"



    def increment_elem (self):
        self.num_elems_in_1screen = self.num_elems_in_1screen + 1
        self.ids.grid1.row_default_height = self.ids.ScanResults_ScrollViewObj.height / self.num_elems_in_1screen
        self.ids.NumResults_LabelObj.text = "(" + str(self.num_elems_in_1screen) + " per page)"
        print (self.ids.grid1.row_default_height)

    def decrement_elem(self):
        if self.num_elems_in_1screen >= 2:
            self.num_elems_in_1screen = self.num_elems_in_1screen -1
            self.ids.grid1.row_default_height = self.ids.ScanResults_ScrollViewObj.height / self.num_elems_in_1screen
            self.ids.NumResults_LabelObj.text = "(" + str(self.num_elems_in_1screen) + " per page)"
            print (self.ids.grid1.row_default_height)


class WindowManager(ScreenManager):
    pass

kv = Builder.load_file('UI_build.kv')

class AwesomeApp(App):
    def build(self):
        return kv

if __name__=="__main__":
    AwesomeApp().run()

