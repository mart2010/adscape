import kivy
kivy.require('2.3.1')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.clock import Clock

from pathlib import Path
import threading
import time
import mss
import random


ss_file = Path('./ss/Screenshot.png').as_posix()


# a simple App that open in background and wakes up depending on some event
# as treated by sscapture_process() (for now randomly, but should be on the appearance of Ads..)

class MainLayout(BoxLayout):
    def __init__(self, on_close_callback, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.label = Label(text="An event occurred!", font_size=24)
        self.close_button = Button(text="Close", size_hint=(1, 0.3))
        self.close_button.bind(on_release=on_close_callback) # pylint: disable=no-member

        self.add_widget(self.label)
        self.add_widget(self.close_button)

class BackgroundEventApp(App):
    def build(self):
        self.layout = MainLayout(self.close_event)
        # Start in minimized mode
        Clock.schedule_once(lambda dt: self.minimize_window(), 1)
        
        # Start monitoring in background
        threading.Thread(target=self.monitor_loop, daemon=True).start()

        return self.layout

    def monitor_loop(self):
        while True:
            time.sleep(5)  # Simulated delay for event
            ret = sscapture_process()
            if ret == 1:
                Clock.schedule_once(lambda dt: self.show_event())
            else:
                Clock.schedule_once(lambda dt: self.minimize_window(), 1)
                print(f'no event, ret={ret}')

    def show_event(self):
        Window.show()
        Window.raise_window()

    def close_event(self, instance):
        self.minimize_window()

    def minimize_window(self):
        Window.hide()


def sscapture_process():
    with mss.mss() as sct:
        sct.shot(output=ss_file)
    return random.choice((1,2,3,4))
    

        
    





if __name__ == '__main__':
    BackgroundEventApp().run()

