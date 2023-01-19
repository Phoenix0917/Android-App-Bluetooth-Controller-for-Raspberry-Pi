from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
import bluetooth



# Defines different screens
class ControlWindow(Screen):
    pass

class BluetoothWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.info = []

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
        print("Scanning for bluetooth services:")
        services = bluetooth.find_service()
        tmp = []

        for service in services:
            tmpElem = Label(
                text_size= (None,None),
                pos_hint={'center_x': 0.5, 'center_y': .95},
                size_hint_y=None,
                size = self.size,
                height = self.size[1],
                halign="center",
                valign = "middle",
            )
            tmp.append(tmpElem)
        for x in range(len(services)):
            self.ids.output.add_widget(tmp[x])


            #self.info[self.ids.grid1.rows - 1].bind(size=self.setting_function)
    
    def setting_function(self, *args):
        """FUNCTION TO UPDATE THE LABEL TO ADJUST ITSELF ACCORDING TO SCREEN SIZE CHANGES"""
        self.info[0].pos_hint = {'center_x': 0.5, 'center_y': .85}
        self.info[0].text_size=self.size



class WindowManager(ScreenManager):
    pass

kv = Builder.load_file('UserInterface3.kv')

class AwesomeApp(App):
    def build(self):
        return kv

if __name__=="__main__":
    AwesomeApp().run()

