import time
from functools import partial
import kivy
from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.app import App
from kivy.clock import Clock
import threading
from kivy.uix.button import Button

kivy.require('2.1.0')



class CustumButton(Button):
    def __init__(self, name, addr, port, proto, **kwargs):
        super(CustumButton, self).__init__(**kwargs)
        #Button.__init__(self, **kwargs)
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
        #super(CustumButton, self).__init__(**kwargs)

class WindowManager(ScreenManager):
    pass



class PrintHello(Screen):
    username = ObjectProperty(None)
    status = ObjectProperty(None)

    def display_hello_status(self):
        # Inform about process of generating hello text.
        self.status.text = "printing hello..."  # this text is never displayed.
        # Pretend something is happening in the background. Actually make it happen on a background thread
        threading.Thread(target=self.do_somehing(1)).start()

    def do_somehing(self, hi):
        print('starting something')
        time.sleep(2)
        print(hi)
        print('finished something')
        
        # schedule the GUI update back on the main thread
        Clock.schedule_once(partial(self.something_finished, 1))

    def something_finished(self, my_var, dt):
        self.username.text = f"Hello, {self.username.text}!"
        # Display information indicating successful printing.
        self.status.text = "printed!"
        x = Button()
        y = CustumButton('1', '0', '2', '3')
        self.add_widget(y)

class MyApp(App):
    pass


if __name__ == '__main__':
    MyApp().run()










