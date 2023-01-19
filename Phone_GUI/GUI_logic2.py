from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import *
import bluetooth



# Defines different screens
class ControlWindow(Screen):
    pass

class BluetoothWindow(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.info = []
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
        print("Scanning for bluetooth services:")
        services = bluetooth.find_service()
        print("hi")
        print(len(services))
        self.ids.grid1.rows = len(services)
        self.ids.grid1.height = self.ids.grid1.row_default_height * len(services)
        print(len(services) / self.num_elems_in_1screen)

        def resize(instance, value):
            #print('My callback is call from', instance)
            #print('and the a value changed to', value)
            #self.ids.grid1.height = self.ids.scrollie.height * len(services) / self.num_elems
            self.ids.grid1.height = self.ids.grid1.row_default_height * len(services)
        self.ids.scrollie.bind(height = resize)
        self.ids.grid1.bind(row_default_height = resize)

        list_of_info = []
        for x in range(len(services)):
            list_of_info.append(-1)
            list_of_info[x] = Button(
                text= "Name:  " + str(services[x]['name']) + '\nHost:  ' + str(services[x]['host']) + '\nPort:  ' + str(services[x]['port']) + '\nProtocol:  ' +str(services[x]['protocol']),
                disabled = True,
                size_hint_x = 1,
                halign= "left",
                valign= "top"
            )
            list_of_info[x].bind(size=list_of_info[x].setter('text_size')) 
            
            def resize_label_text_if_window_changes(button, new_width):
                button.font_size = button.width / (5 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen == 1):
                    button.font_size = button.width / (8.5 * self.num_elems_in_1screen)
            list_of_info[x].bind(width=resize_label_text_if_window_changes) # when info.height changes run this routine
            self.ids.grid1.add_widget(list_of_info[x])

        def resize_label_text_if_elements_changes(grid, new_width):
            for button in list_of_info:
                button.font_size = button.width / (5 * self.num_elems_in_1screen)
                if (self.num_elems_in_1screen == 1):
                    button.font_size = button.width / (8.5 * self.num_elems_in_1screen)
                print("hi")
        self.ids.grid1.bind(row_default_height = resize_label_text_if_elements_changes)

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

