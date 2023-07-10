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
9`UvX$"çï‚QuŒ1êÔzÄÔ[ÚLÊ¡²xN‡¹½.,6³ßİMıK)6ÚrNUW*êœYˆ‰qÆĞ÷ïOI¨éwŞêÀ´Å1ßÜu6˜şS{ÇiÖ­Ye<²fü\[Ñë8lé+{vyâ5/”|Š¬p’DîYQ_Æñ1áXÓ¬VÁ2üIş«kşéçĞyôgÊéÙŒ$œŸ¦3§xqh‚9³d*ª‘ÓÚ´Ús%.22H/µº„»¸éºÆ7¥Ç*1ËtÓ ü•67ÇæBm†$NÅ¤“¾ÛÊl$3¦
!á•™rßèB3îx—QÑ9JƒX/Ùğ,uT¹–¢S9Ktø=®™‹ŸÑ·µ¤­://‹>p^7»î«¦#Œ”çĞmŞõ‚N7vövÃ~ÌŒ€)ÑˆZ+-4e)|Y,`ñÃ
d®²ªú[#BİiÉï£—{›ÌJ£8B.õào_*/â“ã-Ø»úe§è§R;‚2?Ÿ=ifÖ®ÑàœÃ¯.·lrqºØ$Pì 3U#ÿœµìÆ§sı“•úDaæ°š@cYëÃ	H\õƒ%Lwn‘(c%ã*ÂW;ô/¡t…^<7¼eú&@ìCÔ3Ä2bQÚµ±@¯*MÃû¿Ì¹ˆ&#ÄÿzŒ¿Æ^Ta+¨G%¶ë×ÇI{Ø+,_L–.¨.ˆƒıñ´’¸rà™Âyèäµ]Ö“İ‘Ù=4¨1Êy¶8®ğ&’ÔËÔàõnäMâ=±ÛqóØøìùHü}ßüØCê·0×íØ  ¤	aâ²%:À¾~1'Ì§¡§´Î‚ËD6Ï×4ÕRX×‘g?Ó­0È¯ù|Ÿ	
AÛÒ°¤Ä—¼d‘]%ô%€`Ñncx-Í€å¢.ZÙÚf€T²ôµÎN¸â6= f0/ıÑçjñL-óšt -|´KÎdò66¬'ì
ÔÕıab¨¡C¶¬n»ÅŠ(h©= >85ªç<³‡9ÚÉ¹á‹°åÙîôÃ§÷å¨ÉÚ«˜‰×iµ„ O]fè’Z4oÎ—n>¶ÊÉ^³£Õ÷†âÚãó‹» 8Ùt4N™yöÍ4Ê¢%Ö"Í¥wQ~ ÿ&)#ÎP‘c¡ûwÔ@Æ‡ŞˆáÜ™èKŒèï9¦ÁP*”'?;ˆ'H¿šû”í7í¬·m
ßYv¡_¤ĞY½ƒŠu¦NÄêßö?Ã˜õß€Ğª!¨•7!ßmëı¼{Ó§×Hİ»“È4£½1nÌA˜ô´ûµ+9údÌ“ÂÓ#Ïs›|1[ÄNj¸ª š{„°æHŠ’ôf¡’¼<În—DtCÊE¥¤`"òJøÑpJùº/x¢YŞËºÒù¤"®ïdh&ŒıJC&Ä–×ôÜ=]¢clãÌû;T†;?sãºm‚P÷a°ò†‹wp¸èîRİ¤Ñ2Æä”›Ø„ê'æíT§¿5•³3Í?Fëµæ!'¿|ÂÇíÎ–EÓK	›¯ 6û´@BŸåÔÁ3`‡,³9äMMâÛˆˆq
£Qï½¾ú
{ìHXÈÓñ•T¯º›ùBıï~C@b2¦ˆPÌ­F'Æ@!Õöí™¿bëFz§ı(»˜DÏ´~Æk [“g„›œÈT	í@i¾k±K§Éa\,UùÌäFÁÿ!,Dk0èŒÖj¦8+ƒf«u<~!9(>ëö‰mõÔ+½â_³-*L¨€ÚM¡Ú×`v¾^"”+£ËŞuÒSpK’Án®`ğ¨moå¶à[<^¸/.àEß/éî/¾6¬{¿
-®T“Üú¢Xµ°c;Ê«U‘
hZ„\ƒlLõN=‘v‘›±)†¡=…¸dESÔşÜï"5µ¥ÆAJ®“lí“Xâ™•_šT­XG×çäªbOó4&ÎqWm¶3j`¬ñÖ³pä«tW !zÏX »Ïm¨ë÷j<	‘H€utã}ë0•a H×\ºvLêÇc1-+'Óå[Uó+d4ƒD…"4ŞŞ£ÀRübß%Ÿj@xƒŸĞÜÎÁ,"}Ş8š“Rv×°Íi÷~òtÌ^ÚF¼œ²0¾@ÅÂCõõÊ%ª*$nhôÖÚİwàn4QJc‹±ä|XöWpÛDû×
Q¦½XÃ_
‚—áªvòÑ¢Ş-?éÒ ß‹\Q6kbzû;Ô‚ÔÌ=äƒãØ5Ş‰Š§üiSŞ\EÍbˆi1ÿq DÑÿQ­1£Ôœı‡[û¡å8à<¸|.>¼-‘»\ôè^)’o<`<ÛËoA²¾Aû¾§Âí§;–É(\ÊlªÌ=h­s/É²mp§Lôgz’–GÉÎe™lS·´ÏÖ_®7ÙÏÃúÔ·Ü	>q5LŞo³ôü(wëâÏF‰”}ş•ïáfµ\½è¸ÁoÅ•)u=D¸0l·Rö…_WLp=}¨×ó*Oæ‘\Nt‘=Ò‘bÊ€to†üóbdÒºCDåş‹Æ`Œ „¤úHqbe¹Á&Åı¬zuÄo¬¶bo^AT‡ûGÜki•J?.-]Èº\ÌïÊ:èĞÖ)A^`’‰3<"°Æåÿà½¸ÖUI·«,­ésy‹®¦dßı³86(…°*;,’‘ówÁ¨:F‚uj=bê-m&åPÙ<§Ã†Ü^›Ùïn¦ş¿¥m9§ª+OuÎˆ,ÄD8cèû÷§$Ôô;ou`Úâ˜oî:Lÿ©½ã4ëÖ¬2Y3~®­èu
¶ô•=»<ñšJ>EV8I¢÷¬¨/ãø˜p¬ÀéÖ«`™ş$ÿÕµ
ÿôsè<ú3åôlFÎOÓ™S¼84ÁœY2ÕÈimZí¹™¤—Z]Â]Üt]ã›Òc•˜e	ºiş€J››cs¡6	C§â@ÒIßme6’Ó	…†ğÊL¹ot¡‡w¼Ë¨è¥A¬—Àlx–:ª\ËÑ©œ%:ü×ÌÅ€ÏèÛZÒV——E8¯›]÷UÓ†FÊsè6ïzA§;{»a?fFÀ”hD­•š²”¾¬N°øa2WYÕGı­¡î´ä÷ÑË½Mf%Š‡Q!—zğ·/•ñÉñŠì]ı²SôS©NA™ŸÏ43k×hpÎáW—[6¹8]l(v€™ªÇ‘ÆÎZvãÓ¹şÉJ}¢0sXM ±¬õá$O®úÁ¦‰;·ÈÇ?”±’qá«ú—PºB/›
Ş2} Gö!êb±(íÚX W•¦áı_æ\D“â=Æ_c/ª°Ô£Ûõëã¤=ì–/&KTÄÁşxZI\9ğƒLá€<tòÚ.ëÉîÈìÔå¼ÛNWxIêejğz7Hr‚&ñØí¸ylüö|$ş¾Îo~ì!õ[˜ëöGlPÒ„Ç° qÙ’`_?Š˜æÓĞSZgÁe"›çkšj)¬ëÈ…³‰Ÿ†éVä×|¾Ï‰ í	iXRâK^²È®’úˆ@°h·1¼–fÀrQ­lm3@*YúZHg'\q›3˜—şèŒsµø¦–yM:€>Ú%g2ùÖÎvêêş01ÔP![	V·İbE´TŒ PœÕsÙ†ÃíäÜğEØÇòŒl÷úá¿ÓûrÔdíUÌÄë´ZB€§.3tI-š7çK7[åˆd¯ÙÑê{CqíñyŠÅİ œl:'„Ì<ûfeÑk‘æÒ»(?€“”‘?g¨È±ĞıÏ;ê ãCoÄpîLô%Fô÷Ó`(ÊŠ“ŸÄ¤_Í}Êö›vÖÛ¶…ï,»Ğ/Rè¬ŞÀŠAÅ:S'bõoûŸaÌúo@hÕÔÊ¿›ïˆ¶õşFŞ½éÓk¤îİIdšÑŞ7æ LzÚıÚ•}2æIáé‘ç¹ÀM¾˜-b'5ÜU
PÍÆ=BGXs$EIz³PIŞg·ŠK"º!e¢RR0y%üh8¥|İ…<Ñ,ïe]é|R×w24Æ~¥!bËëzî®ÑÀ1¶qæ}‚*Ã†Ÿ¹q]Š6A(û0XyÃÅ;8\tw©nÒhcrÊMlÂ
õóvªÓ_ÇšJ„Ù™æ£õZó“€_>áãvgË‚¢é¥„ÍW€›}Z ¡Ïrêà°C–¿Ùò¦&ñmDÄ8…Ñ¨÷^_}…=v$,äéøJ*‹WİÍ|¡ş÷Î‰G¿! 1HSD(æV£c jûöÌ_±u#=„Ó~”]L¢gZ?ã5€­É³ÂÍ
NäGª„v 4ßµØ¥Óä0.–ª|fr£àÿ‰–F¢µ tFk5Sœ•A³Õ:?¿ŸuûŠÄ¶zj†•^ñ/ÈÙ&T@í¦PíkH0;ß/Ê•Ñeïƒ:é…)¸%É`7W0xÔ¶·r[ğ-/Üğ¢Šï—ô÷_›?Ö=_…WªIn}Q¬ZØ±åÕªH4-BŠ@®A6¦z§H;‚ÀÈÍØÃĞBÜ²Š")jî÷‘šÚRã %×I¶ÀöI,ñL‚Ê/MªV,‡£ësrU±§yç¸«6Û50Ö†xëY8òUº+‚Ğ½g,ĞŠŒİç6Tõ{5„H$À::Šñ¾u˜Ê0P¤k®	];&u†ã±˜–•“éò­ªù2šA"BoïQ`)~±ï‡O5  ¼ÁOhnç`‘>oÍI©‚»kØæ4‚{?y:f/m#^ÎÀGY_ Èbá¡úzåU74zkíî;p7š(¥±ÅXrO>,û«¸m¢ık…(Ó^¬á/ÁËpU»@ùhQï–Ÿti€ïE®(›51½ıjAjæÈ?rˆÁqìšïDÅSş´)ï®Î¢f1D†´˜ÿ8 ¢èÎÿ¨Ö˜QjÎşÃ­ıĞrœp	Ü@>—Ş–È].zt¯É70íå·‹ Yß }ßSáöÓK‡d.e6Uæ´†Ö¹—dÙ6¸S&	
z‡3=IË£dç²L¶©[Úgë/×›ìça}ê[îŸ¸&ï·Yz~H”»uñg£DJÇ>ÿÊ÷ğ³Z®^t\ˆà·âÊ”ºŠ"\6[)ûÂ¯+&¸>Ôëy•‡'óH.'ºHÈéH1e@º7Cşy12iİ!¢rÿEc0FPBRı	¤@‡8±²Ü`“â~V½:â7V[±7¯ ªC‰ı#îµŒ´J¥—–.d].ƒæwethë” /0ÉÄ‚XãòğŞ‚\ëª¤ÛÕF–Öt¹¼EWS2ÇïşYœG”BX•IƒÈù»`T#AŒ:µ1õ–€6“r¨lÓaCn¯‹Íìw·GSÿßRŠ¶œSÕ•§Š†:gDb¢Fœ1ôıûSjú·:0mqÌ7w¦ÿÔŞqšukV¬?×Vô:[úÊ]ø@Í%Ÿ"+œ$Q‡{VÔ—q|L8Vàôë…U°Ì’ÿêZ…ú9tı™rz6#	ç§éÌ)^š`Î,™Šjä´6­ö\‰‹Ì‡ÒÆK­.á.nº®ñMé±JÌ²İ4@¥ÍÍ±¹P›„!‰Sq é¤ï¶2ÉŒé„BÃ@Hxe¦ƒÜ7º…ĞÃŒ;ŞeTtÒÇ ÖK`6<KU®åƒèTÎ~kæbÀgôm-i«ÎËË¢œ×Í®ûªiÃ#å9t›w½ Ó½İ°3#`J4¢ÖJMYÊ_V'Xü°…™«¬ê£şÖ‡PwZòûèåŞ&³ÅÃ(K=øÛ—Ê‹øäxEö®~Ù)ú©ÔN§ ÌÏgOš™µ…k48çğÀ«‡Ë-›\œ.¶	;ÀLÕãHã?g-»ñé\ÿd¥>Q˜9¬&ĞXÖúp’'Wı`	ÓÄ[äãÊXÉ¸ŠğÕıK(]¡ÏMo™¾	#ûõ±ŒX”vm,Ğ«JÓğş/s.¢Éñ¿ã