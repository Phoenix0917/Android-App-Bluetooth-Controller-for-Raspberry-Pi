from kivy.app import App
from kivy.garden.joystick import Joystick
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class DemoApp(App):
  def build(self):
    self.root = BoxLayout()
    self.root.padding = 50
    joystick = Joystick(
      sticky= False,
      outer_size= 0.7,
      inner_size= 0.7,
      pad_size=   0.5,
      outer_line_width= 0.025,
      inner_line_width= 0.015,
      pad_line_width=   0.025,
      outer_background_color= (0.75, 0.75, 0.75, 1),
      outer_line_color=       (0.25, 0.25, 0.25, 1),
      inner_background_color= (0.75, 0.75, 0.75, 1),
      inner_line_color=       (0.7,  0.7,  0.7,  1),
      pad_background_color=   (0.4,  0.4,  0.4,  1),
      pad_line_color=         (0.35, 0.35, 0.35, 1)
      )
    '''
    outer_size: 0.7
    inner_size: 0.7
    pad_size:   0.5
    outer_line_width: 0.025
    inner_line_width: 0.015
    pad_line_width:   0.025
    outer_background_color: (0.75, 0.75, 0.75, 1)
    outer_line_color:       (0.25, 0.25, 0.25, 1)
    inner_background_color: (0.75, 0.75, 0.75, 1)
    inner_line_color:       (0.7,  0.7,  0.7,  1)
    pad_background_color:   (0.4,  0.4,  0.4,  1)
    pad_line_color:         (0.35, 0.35, 0.35, 1)
    '''

    joystick.bind(pad=self.update_coordinates)
    self.root.add_widget(joystick)
    self.label = Label()
    self.root.add_widget(self.label)
  def update_coordinates(self, joystick, pad):
    x = str(pad[0])[0:5]
    y = str(pad[1])[0:5]
    radians = str(joystick.radians)[0:5]
    magnitude = str(joystick.magnitude)[0:5]
    angle = str(joystick.angle)[0:5]
    text = "x: {}\ny: {}\nradians: {}\nmagnitude: {}\nangle: {}"
    self.label.text = text.format(x, y, radians, magnitude, angle)

DemoApp().run()