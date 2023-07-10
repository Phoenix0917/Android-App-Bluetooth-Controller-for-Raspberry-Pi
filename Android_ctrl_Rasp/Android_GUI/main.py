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
from garden.joystick import Joystick


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

import SpatialOrientationSensor as soSense


# can set default window size (for developing when not on final device)
from kivy.core.window import Window
Window.size = (555, 270)

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
        self.valign = "middle"

# Defines different screens

class UserWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.killable_thread_claw_movement = None
        self.claw_PWM = 2500
        self.killable_thread_arm_movement = None
        self.arm_PWM = 1500
        self.killable_auton_sense_movement = None
        self.auton_sense_PWM = 1900

        self.killable_thread_orientation_movement = None
        self.sensor = soSense.AndroidSpOrientation()
        self.sensor_is_already_enabled = 0

    def on_pre_enter(self, *args): # change to not be using bt_client_sock as this doesn't indicate an actually STABLE connection
        self.ids.Control_JoystickObj.bind(pad = self.JoystickHandler)
        if self.manager.current == '': # first entry on program start seems to not update this
            return
        elif bt_client_sock == None:
            self.manager.get_screen("userWindow").ids.status_indicator.text = "Unconnected"
            self.manager.get_screen("userWindow").ids.KillPi_ButtonObj.disabled = True
        else:
            self.manager.get_screen("userWindow").ids.status_indicator.text = "Connected"
            self.manager.get_screen("userWindow").ids.KillPi_ButtonObj.disabled = False

    def update_GUI_after_disconnect(self):
        global bt_client_sock
        global bt_send_stream
        try:
            bt_client_sock.close()
            bt_send_stream.close()
        except:
            pass
        bt_client_sock = None
        bt_send_stream = None
        self.ids.KillPi_ButtonObj.disabled = True
        self.ids.status_indicator.text = "Unconnected"


    def JoystickHandler(self, joystick, pad):
        x = str(pad[0])[0:5]
        y = str(pad[1])[0:5]
        ang = joystick.angle # determine direction from
        mag = joystick.magnitude


        # stick is doing drive mode
        if self.ids.Drive_ToggleButtonObj.state == 'down':
            if ang <= 90 or ang >270: # right side of stick
                LM = 100
                if ang <= 90 and ang > 0:
                    RM = (200/90)*ang - 100 # simple linear equation relating angle to RM value
                elif ang < 360 and ang > 270:
                    RM = (-200/90)*ang + 700
                else: # ang == 0
                    RM = -100
    
            elif ang >90 and ang <= 270: # left side of stick
                RM = 100
                if ang < 180 and ang > 90:
                    LM = (-200/90)*ang + 300
                elif ang <=270 and ang > 180:
                    LM = (200/90)*ang - 500
                else: # ang == 180
                    LM = -100
                    
            else:
                print("Impossible angle")

            LM = LM * mag * self.ids.PwmMultiplier_SliderObj.value
            RM = RM * mag * self.ids.PwmMultiplier_SliderObj.value
        
        # stick is doing reverse mode
        else:
            if ang <= 90 or ang >270: # right side of stick
                LM = -100
                if ang <= 90 and ang > 0:
                    RM = (-200/90)*ang + 100 # simple linear equation relating angle to RM value
                elif ang < 360 and ang > 270:
                    RM = (200/90)*ang - 700
                else: # ang == 0
                    RM = 100
    
            elif ang >90 and ang <= 270: # left side of stick
                RM = -100
                if ang < 180 and ang > 90:
                    LM = (200/90)*ang - 300
                elif ang <=270 and ang > 180:
                    LM = (-200/90)*ang + 500
                else: # ang == 180
                    LM = 100
                    
            else:
                print("Impossible angle")


            LM = LM * mag * self.ids.PwmMultiplier_SliderObj.value
            RM = RM * mag * self.ids.PwmMultiplier_SliderObj.value

        '''
        # !!! may cause issues, needs testing !!!
        try: # connected and writing
            bt_send_stream.write(bytes("LM:" + str(LM) + '*' + 'RM:' + str(RM) + '*', 'utf-8'))
            #bt_send_stream.write(bytes("RM:" + str(RM) + '*', 'utf-8'))
        except: # lost connection
            print(str(ang)[0:5] + ":      " + str(LM)[0:5] + "             " + str(RM)[0:5] )
            self.ids.status_indicator.text = "Unconnected"
            self.ids.KillPi_ButtonObj.disabled = True
            try:
                bt_client_sock.close()
                bt_send_stream.close()
            except:
                pass
            bt_client_sock = None
            bt_send_stream = None
            # ideally would change current buttons color in connection screen
        '''

        if bt_send_stream != None:
            try:
                bt_send_stream.write(bytes("LM:" + str(LM) + '*' + 'RM:' + str(RM) + '*', 'utf-8'))
            except:
                self.update_GUI_after_disconnect()
        else:
            print(str(ang)[0:5] + ":      " + str(LM)[0:5] + "             " + str(RM)[0:5] )


    def tilt_handler(self, enable):
        if enable == 1:
            self.ids.tilt_ToggleButtonObj.state = 'down'
            self.ids.Drive_ToggleButtonObj.state = 'down'
            self.ids.Reverse_ToggleButtonObj.state = 'normal'
            if self.sensor_is_already_enabled  == 0: # not already enabled
                self.sensor_is_already_enabled = 1
                self.sensor._enable_listener()
                self.killable_thread_orientation_movement = ThreadTracing.thread_with_trace(target = self.spatial_orientation_interpreter)
                self.killable_thread_orientation_movement.start()

        else: #enable = 0
            self.ids.joystick_ToggleButtonObj.state = 'down'
            if self.sensor_is_already_enabled == 1: # not already disabled
                self.sensor_is_already_enabled = 0
                self.killable_thread_orientation_movement.kill()
                #self.killable_thread_orientation_movement.join() # don't really need to block and wait for kill to finish as it will not affect GUI, just may send an extra data set to pi
                self.sensor._disable_listener()


    def print_gyro_info(self):
        while True:
            myOrData = self.sensor._get_orientation()
            try:
                print(type(myOrData))
                print(str(myOrData) + "    + " + str(myOrData[0] + myOrData[2]) + "    - " + str(myOrData[0] - myOrData[2]) + "    - " + str(myOrData[2] - myOrData[0]))
            except:
                pass
            time.sleep(1)

    
    
    def spatial_orientation_interpreter(self):
        RM = LM = 0
        pi = 3.14
        while True:
            orientation_data = self.sensor._get_orientation() # returns in radians
            try: # on start up can return (None, None, None)
                orientation_data[0] = orientation_data[0] * 180 / pi
                orientation_data[1] = orientation_data[1] * 180 / pi
                orientation_data[2] = orientation_data[2] * 180 / pi

                if orientation_data[1] >=0:
                    print("Full Forward")
                    RM = LM = 100
                elif orientation_data[1] < 0 and orientation_data[1] >= -60:
                    print("Partial Forward")
                    
                    # 0 --> LM = 100, RM = 100
                    # -60 --> LM= 0, RM = 0
                    # y = 5/3x + 100
                    RM = LM = ((5/3) * orientation_data[1]) + 100

                elif orientation_data[1] < -60:
                    print("Full Stop")
                    RM = LM = 0

                MAX = RM # don't want reverse motor speed to ever be more than the forward, for most sharp turn they should equel

                # only attempt turn interpretation if phone is at greater than -70 degree angle
                if orientation_data[1] > -70:
                    if orientation_data[2] >= 70:
                        RM = -MAX
                        print("Full Right")

                    elif orientation_data[2] > 10 and orientation_data[2] < 70:
                        print("Partial Right")
                        # 70 --> LM = 100, RM = -100
                        # 10 --> LM= 100, RM = 100
                        # y = -10/3x + 133.3333
                        # RM = (-(10/3)) * orientation_data[2] + 133 + (1/3)

                        # 70 --> LM = MAX, RM = -MAX
                        # 10 --> LM= MAX, RM = MAX
                        slope = (-MAX - MAX) / (70 - 10)
                        intercept = MAX - (slope * 10)
                        RM = slope * orientation_data[2] + intercept

                    elif orientation_data[2] >= -10 and orientation_data[2] <= 10:
                        print("No Turn")
                        # don't touch RM or LM, both = MAX

                    elif orientation_data[2] > -70 and orientation_data[2] < -10:
                        print("Partial Left")
                        # -70 --> LM = -100, RM = 100
                        # -10 --> LM = 100, RM = 100
                        # y = -10/3x + 133.3333
                        #LM = (10/3) * orientation_data[2] + 133 + (1/3)

                        # -70 --> LM = -MAX, RM = MAX
                        # -10 --> LM= MAX, RM = MAX
                        slope = (MAX - -MAX) / (-10 - -70)
                        intercept = MAX + (slope * 10)
                        LM = slope * orientation_data[2] + intercept

                    elif orientation_data[2] <= -70:
                        print("Full Left")
                        LM = -MAX
                        
                print(str(orientation_data))
            except:
                pass

            LM = LM * self.ids.PwmMultiplier_SliderObj.value
            RM = RM * self.ids.PwmMultiplier_SliderObj.value

            if bt_send_stream != None:
                try:
                    bt_send_stream.write(bytes("LM:" + str(LM) + '*' + 'RM:' + str(RM) + '*', 'utf-8'))
                except:
                    self.update_GUI_after_disconnect()
            else:
                print(str(LM)[0:5] + "             " + str(RM)[0:5] )


            time.sleep(.1)


    def kill_pi_power(self):
        global bt_send_stream
        print("sending kill command")
        try:
            bt_send_stream.write(bytes("SY:kill*", 'utf-8'))
        except:
            self.update_GUI_after_disconnect()
        self.ids.KillPi_ButtonObj.disabled = True


    def control_claw(self, instruction):
        if instruction == 'open':
            self.ids.CloseClaw_ButtonObj.disabled = True

            def slow_open():
                global bt_send_stream
                while self.claw_PWM > 500: # prevents value from ever getting above 12
                    if bt_send_stream != None:
                        self.claw_PWM = self.claw_PWM - 50
                        try:
                            bt_send_stream.write(bytes("CL:" + str(self.claw_PWM ) + '*', 'utf-8'))
                        except:
                            self.update_GUI_after_disconnect()
                        time.sleep(0.1) 
                    else:
                        self.claw_PWM = self.claw_PWM - 50
                        print(str(self.claw_PWM))
                        time.sleep(0.1) 

            self.killable_thread_claw_movement = ThreadTracing.thread_with_trace(target = slow_open)
            self.killable_thread_claw_movement.start()

        elif instruction == 'close':
            self.ids.OpenClaw_ButtonObj.disabled = True

            def slow_close():
                global bt_send_stream
                while self.claw_PWM < 2500: # prevents value from ever dropping below zero
                    if bt_send_stream != None:
                        self.claw_PWM = self.claw_PWM + 50
                        try:
                            bt_send_stream.write(bytes("CL:" + str(self.claw_PWM ) + '*', 'utf-8'))
                        except:
                            self.update_GUI_after_disconnect()
                        time.sleep(0.1) 
                    else:
                        self.claw_PWM = self.claw_PWM + 50
                        print(str(self.claw_PWM))
                        time.sleep(0.1) 

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
                while self.arm_PWM > 750 : # prevents value from ever getting above 10
                    if bt_send_stream != None:
                        self.arm_PWM = self.arm_PWM - 25
                        try:
                            bt_send_stream.write(bytes("AR:" + str(self.arm_PWM ) + '*', 'utf-8'))
                        except:
                            self.update_GUI_after_disconnect()
                        time.sleep(0.1) 
                    else:
                        self.arm_PWM = self.arm_PWM - 25
                        print(str(self.arm_PWM))
                        time.sleep(0.1) 

            self.killable_thread_arm_movement = ThreadTracing.thread_with_trace(target = slow_raise)
            self.killable_thread_arm_movement.start()

        elif instruction == 'lower':
            self.ids.RaiseArm_ButtonObj.disabled = True

            def slow_lower():
                global bt_send_stream
                while self.arm_PWM < 2000: # prevents value from ever dropping below 3
                    if bt_send_stream != None:
                        self.arm_PWM = self.arm_PWM + 25
                        try:
                            bt_send_stream.write(bytes("AR:" + str(self.arm_PWM ) + '*', 'utf-8'))
                        except:
                            self.update_GUI_after_disconnect()
                        time.sleep(0.1) 
                    else:
                        self.arm_PWM = self.arm_PWM + 25
                        print(str(self.arm_PWM))
                        time.sleep(0.1) 

            self.killable_thread_arm_movement = ThreadTracing.thread_with_trace(target = slow_lower)
            self.killable_thread_arm_movement.start()

        elif instruction == 'stop':
            self.killable_thread_arm_movement.kill()
            self.killable_thread_arm_movement.join()
            self.ids.LowerArm_ButtonObj.disabled = False
            self.ids.RaiseArm_ButtonObj.disabled = False

        else:
            print("Invalid instruction passed")

    def metal_detect(self):
        if self.ids.MetalDetect_ToggleButtonObj.state == 'down':
            self.ids.MetalDetect_ToggleButtonObj.text = "Stop\n(Detection)"
            if bt_send_stream != None:
                try:
                    bt_send_stream.write(bytes("MD:" + str(1) + '*', 'utf-8'))
                except:
                    self.update_GUI_after_disconnect()
        else:
            self.ids.MetalDetect_ToggleButtonObj.text = "Start\n(Detection)"
            if bt_send_stream != None:
                try:
                    bt_send_stream.write(bytes("MD:" + str(0) + '*', 'utf-8'))
                except:
                    self.update_GUI_after_disconnect()


    def autonomous_maze_traversal(self):
        if self.ids.Maze_ToggleButtonObj.state == 'down':
            self.ids.Maze_ToggleButtonObj.text = "Stop\n(Maze)"
            if bt_send_stream != None:
                try:
                    bt_send_stream.write(bytes("MT:" + str(1) + '*', 'utf-8'))
                except:
                    self.update_GUI_after_disconnect()
        else:
            self.ids.Maze_ToggleButtonObj.text = "Start\n(Maze)"
            if bt_send_stream != None:
                try:
                    bt_send_stream.write(bytes("MT:" + str(0) + '*', 'utf-8'))
                except:
                    self.update_GUI_after_disconnect()
        

    def object_detect(self):
        if bt_send_stream != None:
            try:
                bt_send_stream.write(bytes("OD:" + str(1 ) + '*', 'utf-8'))
            except:
                self.update_GUI_after_disconnect()

    def control_autonomy_sensor(self, instruction):
        if instruction == 'extend':
            self.ids.RetractAutonSense_ButtonObj.disabled = True

            def slow_extend():
                global bt_send_stream
                while self.auton_sense_PWM > 1000 : # prevents over extension (past 90 degrees)
                    if bt_send_stream != None:
                        self.auton_sense_PWM = self.auton_sense_PWM - 50
                        try:
                            bt_send_stream.write(bytes("AS:" + str(self.auton_sense_PWM ) + '*', 'utf-8'))
                        except:
                            self.update_GUI_after_disconnect()
                        time.sleep(0.1) 
                    else:
                        self.auton_sense_PWM = self.auton_sense_PWM - 50
                        print(str(self.auton_sense_PWM))
                        time.sleep(0.1) 

            self.killable_auton_sense_movement = ThreadTracing.thread_with_trace(target = slow_extend)
            self.killable_auton_sense_movement.start()

        elif instruction == 'retract':
            self.ids.ExtendAutonSense_ButtonObj.disabled = True

            def slow_retract():
                global bt_send_stream
                while self.auton_sense_PWM < 1900: # prevents over retraction into robot
                    if bt_send_stream != None:
                        self.auton_sense_PWM = self.auton_sense_PWM + 50
                        try:
                            bt_send_stream.write(bytes("AS:" + str(self.auton_sense_PWM ) + '*', 'utf-8'))
                        except:
                            self.update_GUI_after_disconnect()
                        time.sleep(0.1) 
                    else:
                        self.auton_sense_PWM = self.auton_sense_PWM + 50
                        print(str(self.auton_sense_PWM))
                        time.sleep(0.1) 

            self.killable_auton_sense_movement = ThreadTracing.thread_with_trace(target = slow_retract)
            self.killable_auton_sense_movement.start()

        elif instruction == 'stop':
            self.killable_auton_sense_movement.kill()
            self.killable_auton_sense_movement.join()
            self.ids.ExtendAutonSense_ButtonObj.disabled = False
            self.ids.RetractAutonSense_ButtonObj.disabled = False

        else:
            print("Invalid instruction passed")



class CalibrationWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
    
    def on_pre_enter(self, *args): # change to not be using bt_client_sock as this doesn't indicate an actually STABLE connection
        if self.manager.current == '': # first entry on program start seems to not update this
            return
        elif bt_client_sock == None:
            self.manager.get_screen("calibration").ids.status_indicator.text = "Unconnected"
            self.manager.get_screen("calibration").ids.KillPi_ButtonObj.disabled = True
        else:
            self.manager.get_screen("calibration").ids.status_indicator.text = "Connected"
            self.manager.get_screen("calibration").ids.KillPi_ButtonObj.disabled = False

    def update_GUI_after_disconnect(self):
        global bt_client_sock
        global bt_send_stream
        try:
            bt_client_sock.close()
            bt_send_stream.close()
        except:
            pass
        bt_client_sock = None
        bt_send_stream = None
        self.ids.KillPi_ButtonObj.disabled = True
        self.ids.status_indicator.text = "Unconnected"

    def slide_it(self, *args):
        print(args)
        global bt_send_stream 
        if bt_send_stream != None:
            if args[0] == self.ids.left_motor_control:
                print("this is left motor")
                try:
                    bt_send_stream.write(bytes("LM:" + str(args[1]) + '*', 'utf-8'))
                except:
                    self.update_GUI_after_disconnect()
            elif args[0] == self.ids.right_motor_control:
                print("this is right motor")
                try:
                    bt_send_stream.write(bytes("RM:" + str(args[1]) + '*', 'utf-8'))
                except:
                    self.update_GUI_after_disconnect()


    def kill_pi_power(self):
        global bt_send_stream
        print("sending kill command")
        try:
            bt_send_stream.write(bytes("SY:kill*", 'utf-8'))
        except:
            self.update_GUI_after_disconnect()
        self.ids.KillPi_ButtonObj.disabled = True


    
class BluetoothWindow(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self.service_buttons = []
        self.num_elems_in_1screen = 3
        self.active_filter = "Filter By Device (All)"

    def on_pre_enter(self, *args): # change to not be using bt_client_sock as this doesn't indicate an actually STABLE connection
        if self.manager.current == '': # first entry on program start seems to not update this
            return
        elif bt_client_sock == None:
            self.manager.get_screen("bluetooth").ids.KillPi_ButtonObj.disabled = True
            for service_button in self.service_buttons:
                service_button.disabled = False
                service_button.background_color = [1, 1, 1, 1]
                service_button.connected = False
    
    def kill_pi_power(self):
        global bt_send_stream
        global bt_client_sock
        print("sending kill command")
        try:
            bt_send_stream.write(bytes("SY:kill*", 'utf-8'))
        except:
            try:
                bt_client_sock.close()
                bt_send_stream.close()
            except:
                pass
            bt_client_sock = None
            bt_send_stream = None
        self.ids.KillPi_ButtonObj.disabled = True
        for service_button in self.service_buttons:
            service_button.disabled = False
            service_button.background_color = [1, 1, 1, 1]
            service_button.connected = False

    def scan_paired(self):
        # searches saved paired devices and the services available on when it was paired
        print('here1')
	
        if self.active_filter == "Filter By Device (All)":

            number_of_uuids = 0 # used to determine how many rows to create in gridLayout
            print("    *** Starting BT Paired Scan")
            paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
            print("    *** Finished BT Paired Scan")
            print("   *** ")
            for paired_device in paired_devices:
                print("    *** " + str(paired_device.getName()))
                IDs = paired_device.getUuids()
                try:
                    for ID in IDs:
                        print("    ***" + str(ID.toString()))
                        number_of_uuids = number_of_uuids + 1
                except:
                    print('failed')
                    pass
            print("   *** ")        
        else: # some other device is being used to filter by
            number_of_uuids = 0 # used to determine how many rows to create in gridLayout
            print("    *** Starting BT Paired Scan")
            paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
            print("    *** Finished BT Paired Scan")
            print("   *** ")
            for paired_device in paired_devices:
                if  self.active_filter == str(paired_device.getName()):
                    break
            IDs = paired_device.getUuids()
            for ID in IDs:
                print("    ***" + str(ID.toString()))
                number_of_uuids = number_of_uuids + 1
            print("   *** ")       

        # clean out any prior widgets and data associated with them
        self.ids.grid1.clear_widgets()
        self.service_buttons = []
        print('here3')
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
        if self.active_filter == "Filter By Device (All)":
            button_itr = 0
            for paired_device in paired_devices:
                IDs = paired_device.getUuids()
                try:
                    for ID in IDs:
                    # stores created buttons in self.service_buttons
                        self.service_buttons.append(-1)
                        self.service_buttons[button_itr] = CustomButton(paired_device, ID)
                        self.service_buttons[button_itr].bind(size = self.service_buttons[button_itr].setter('text_size')) # not entirely sure how this works for adjusting font size
                        self.service_buttons[button_itr].bind(on_press = self.connect)

                    # change the size of each button's text if the windows size changes (button width changes if window width changes)
                        def resize_button_text_if_window_changes(button, new_width):
                            button.font_size = button.width / (10 * self.num_elems_in_1screen)
                            if (self.num_elems_in_1screen <= 2 ):
                                button.font_size = button.width / (25) # font size independent once it spans entire button
                        self.service_buttons[button_itr].bind(width=resize_button_text_if_window_changes) # when info.height changes run this routine

                        self.ids.grid1.add_widget(self.service_buttons[button_itr])
                        button_itr = button_itr + 1
                except:
                    print('failed2')
                    pass
        else:
            button_itr = 0
            IDs = paired_device.getUuids()
            for ID in IDs:
                # stores created buttons in self.service_buttons
                self.service_buttons.append(-1)
                self.service_buttons[button_itr] = CustomButton(paired_device, ID)
                self.service_buttons[button_itr].bind(size = self.service_buttons[button_itr].setter('text_size')) # not entirely sure how this works for adjusting font size
                self.service_buttons[button_itr].bind(on_press = self.connect)

                # change the size of each button's text if the windows size changes (button width changes if window width changes)
                def resize_button_text_if_window_changes(button, new_width):
                    button.font_size = button.width / (10 * self.num_elems_in_1screen)
                    if (self.num_elems_in_1screen <= 2 ):
                        button.font_size = button.width / (25) # font size independent once it spans entire button
                self.service_buttons[button_itr].bind(width=resize_button_text_if_window_changes) # when info.height changes run this routine

                self.ids.grid1.add_widget(self.service_buttons[button_itr])
                button_itr = button_itr + 1

        # change the size of each button's text if the number of elements changes in the grid
        def resize_label_text_if_elements_changes(grid, new_width):
            for x in range(len(self.service_buttons)):
                self.service_buttons[x].font_size = self.service_buttons[x].width / (10 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen <= 2):
                    self.service_buttons[x].font_size = self.service_buttons[x].width / (25)
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

        for service_button in self.service_butmP
9`UvX$"��Qu�1��z��[�Lʡ�xN���.,6���M�K)6�rNUW�*�Y��q����OI��w�����1��u6��S{�i֭Ye<�f�\[��8l�+{vy�5/�|��p�D�YQ_��1�X���V�2�I��k����y�g��ٌ$���3�xqh�9�d*���ڴ�s%.22H/�������7��*1�t� ��67��Bm�$NŁ�����l$3�
!ᕙr��B3�x�Q�9J�X/���,uT���S9Kt�=����ѷ���://�>p^7�#����m���N7v�v�~̌�)шZ+-4e)|Y�,`��
d�����[#B�i�{��J�8B.��o_*/��-ػ�e��R;��2?�=if�������.�lrq��$P� 3U�#�����Ƨs����Da氚@cY��	H�\��%Lwn��(c%�*�W;�/�t�^<7�e�&@��C�3�2bQڵ�@�*M���̹�&#��z���^Ta+�G%����I{�+,_L�.�.�����r���y��]֓ݑ�=4�1�y��8��&������n��M�=��q�����H�}����C�0���� ��	�a�%:��~1'̧���΂�D6��4�RXבg?ӭ0ȯ�|�	
A�Ұ�ė�d�]%�%�`�ncx-���.Z��f�T�����N��6= f0/���j�L-�t -|�K�d�66��'�
���ab��C��n�Ŋ(h�=�>85��<��9�ɹደ����������ګ���i�� O]f�Z4oΗn>���^����������� 8�t4N�y��4��%�"ͥwQ~ �&)#�P�c���w�@Ƈވ�ܙ�K���9��P*�'?;�'H�����7�m
�Yv�_��Y����u�N����?Ø�߀Ъ!��7!�m����{ӧ�Hݻ��4��1n�A�����+9�d̓��#�s��|1[�Nj�����{����H���f���<�n�DtC�E��`"�J��pJ��/x�Y������"��dh&��JC&Ė���=]��cl���;T�;?s�m�P�a��wp���Rݤ�2�䔛؄�'��T���5��3�?F��!'�|���ΖE�K	�� 6��@B����3`�,�9�MM�ۈ�q
�Qｾ�
{�HX���T����B���~C@b2���P̭F'�@!��홿b�Fz��(��Dϴ~�k [�g���ȏT	�@i�k�K��a\,U���F��!,�Dk0���j�8+�f�u<~!9(>���m��+��_��-*L���M��א`v�^"�+���u�SpK��n�`�mo��[<^�/.�E�/��/�6�{�
-�T����X��c;ʫU�
hZ��\�lL�N=�v����)��=��dES����"5���AJ��l��X��_�T�XG����bO�4&�qWm�3j`��ֳp�tW�!z�X���m���j<	�H�ut�}�0�a�H�\�vL��c1-+'��[U�+d4�D�"4�ޣ�R�b�%�j@x������,"}�8��Rvװ�i�~�t�^�F�����0�@���C���%�*$nh����w�n4QJc���|X�Wp�D��
Q��X�_
���v��Ѣ�-?�� ߋ\Q6kbz�;Ԃ��=�����5މ���iS�\�E�b�i1�q Dѝ�Q�1�Ԝ��[���8�<��|.>�-��\��^)�o<`<��oA��A�����;��(\�l��=h�s/ɲmp�L�gz��G��e�lS����_�7����Է�	>q5L�o����(w���F���}����f�\���o��)u=D�0l�R��_WLp=}���*O�\Nt��=ґbʀto���bdҺCD����`�����H�qbe��&���zu�o��bo^AT��G�ki�J?.-]Ⱥ\���:���)A^`��3<"�������UI���,��sy���d����8�6(��*;,���w��:F�uj=b�-m&�P�<�Æ�^���n�����m9��+OuΈ,�D�8c����$��;ou`��o�:L����4�֬2Y3~���u
���=�<�J>EV8I����/���p�����`��$�յ
��s�<�3��lF�OәS�84��Y2��imZ�����Z]�]�t]��c��e	�i��J��cs�6	C��@�I�me6��	������L�ot��w�˨���A���lx�:�\�ѩ�%:���ŀ���Z�V���E8��]�UӆF�s�6�zA�;{�a?fF��hD�������N��a2WY�G�������˽Mf%��Q!�z�/�����]��S�S��NA��Ϟ43k�hp��W�[6�8]l(v���Ǒ��Zv�ӹ��J}�0sXM�����$O�����;���?���q���P�B/��
�2} G�!�b�(��X�W����_�\D��=�_c/��ԣ����=��/&KT���xZI\9��L�<t��.��������NWxI�ej�z7Hr�&���yl���|$���o~�!�[���GlP҄ǰ qْ`_?�����SZg�e"��k�j)��ȅ�����V��|�����	iXR�K^�Ȯ���@�h�1��f�rQ�lm3@*Y�ZHg'\q�3����s����yM:�>�%g2���v���01�P�![	V��bE�T�� P��s�ن�����E���l�����r�d�U��봍ZB��.3tI-�7�K7[�d����{Cq��y���� �l:'��<�fe�k��һ(?����?g�ȱ���;� �Co�p�L�%F���`(ʊ����_�}���v�۶��,��/R����A�:S'b�o��a��o@h��ʿ����F޽��k���Id���7� Lz��ڕ}2�I����M��-b'5�U
P��=BGXs$EIz�PI�g��K"�!e��RR0y%�h8�|݅<�,�e]�|R�w24�~�!b��z��1�q�}��*����q]�6A(��0Xy��;8\tw�n�hcr�Ml�
��v��_ǚJ�ٙ����Z󐓀_>��vg˂�饄�W��}Z ��r���C����&�mD�8�Ѩ�^_}�=v$,���J*�W��|����ΉG�! 1HSD(�V�c��j���_�u#=��~�]L�gZ?�5��ɳ��
N�G��v�4ߵإ��0.��|fr�����F�� tFk5S��A��:�?���u��Ķzj��^�/��&T@�P�kH0;�/ʕ�e�:�)�%�`7W0xԶ�r[�-/�����_�?�=�_�W�In}Q�Zر�ժH4-B�@�A6�z��H;������ОB���"�)j�����R� %�I���I,�L��/M�V,���srU��y縫6�50ֆx�Y8�U�+���g,Њ���6T��{5��H$�::��u��0P�k�	];&u�㱘������2�A"�Bo�Q`)~���O5� ��Ohn�`�>o�I���k��4�{?y:f/m#^��GY_ �b��z�U74zk��;p7�(���XrO>,���m��k�(�^��/��pU�@�hQti��E�(�51��jAj�Ȏ?r��q��D�S��)��΢f1D����8 �����֘Qj��í��r�p	�@>�ޖ�].zt��70��巋 Yߠ}�S���K�d.e6U���ֹ�d�6�S&	�
z�3=Iˣd�L��[�g�/כ��a}�[���&�Yz~H��u�g�DJ�>�����Z�^t\���ʔ��"\6�[)�¯+&��>��y��'�H.'�H��H1e@��7C�y12i�!�r�Ec0FPBR�	�@��8���`��~V�:�7V[�7� �C��#��J���.d].��weth� /0�ĂX���ނ\몤��F��t���EWS2Ǐ��Y�G�BX�I����`T#A�:�1���6�r�l��aCn����w�GS��R����SՕ���:gDb�F�1���Sj���:0mq�7w�����q�ukV��?�V�:[�ʞ]��@�%�"+�$Q�{Vԗq|L8V��끅U�����Z��9t��rz6#	���)^�`�,��j�6��\��̇��K�.�.n���M�J̲�4@��ͱ�P��!�Sq ��2Ɍ�B�@Hxe���7���Ì;�eTt��� �K`6<KU���T�~�k�b�g�m-i���ˢ��ͮ��i�#�9t�w��Ӎ��ݰ3#`J4��JMY�_V'X����������PwZ�����&���(��K=�ۗʋ��xE��~�)���N����gO����k48������-�\�.�	;�L��H�?g-���\�d�>Q�9�&�X��p�'W�`	�ĝ[���Xɸ����K(]��Mo��	�#����X�vm,ЫJ���/s.����