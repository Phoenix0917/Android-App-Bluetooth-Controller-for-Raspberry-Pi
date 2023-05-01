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
from kivy.garden.joystick import Joystick


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
        
        if self.active_filter == "Filter By Device (All)":
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
        self.ids.KillPi_ButtonObj.disabled = False

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
        self.ids.KillPi_ButtonObj.disabled = True

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


    def display_devices(self):
        device_names = ["Filter By Device (All)"]
        paired_devices = BluetoothAdapter.getDefaultAdapter().getBondedDevices().toArray()
        for paired_device in paired_devices:
            device_names.append(str(paired_device.getName()))
        self.ids.devices_CustomSpinnerObj.values = device_names

    def set_filter(self, device_name):
        self.active_filter = device_name

class WindowManager(ScreenManager):
    pass

kv = Builder.load_file('UI_build.kv')

class AwesomeApp(App):
    def build(self):
        return kv

if __name__=="__main__":
    AwesomeApp().run()

