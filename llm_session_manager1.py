import os
import json
import time
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.rst import RstDocument
from kivy.uix.checkbox import CheckBox
from kivy.uix.dropdown import DropDown
from kivy.uix.spinner import Spinner
from kivy.uix.settings import SettingsWithSidebar

SESSIONS_DIR = "sessions"
CONFIG_FILE = "config.json"

# Ensure sessions folder exists
os.makedirs(SESSIONS_DIR, exist_ok=True)

def list_sessions():
    return sorted([f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")])

class Config:
    def __init__(self):
        self.data = {
            "ollama_url": "http://localhost:11434",
            "default_model": "llama3",
            "initial_prompt": ""
        }
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                self.data.update(json.load(f))

    def save(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)

class LLMApp(App):
    def build(self):
        self.config_data = Config()
        self.session_index = -1
        self.sessions = list_sessions()
        self.current_session = None

        self.root = BoxLayout(orientation='vertical')

        self.display = RstDocument(size_hint_y=0.8)
        self.root.add_widget(ScrollView(size_hint_y=0.8, do_scroll_x=False, do_scroll_y=True, content=self.display))

        self.prompt = TextInput(hint_text="Type your message...", multiline=False, size_hint_y=None, height=50)
        self.root.add_widget(self.prompt)

        nav_bar = BoxLayout(size_hint_y=None, height=50)
        self.back_button = Button(text="Back", on_press=self.go_back)
        self.next_button = Button(text="Next / New", on_press=self.go_next_or_new)
        menu_button = Button(text="⋮", on_press=self.open_menu)
        nav_bar.add_widget(self.back_button)
        nav_bar.add_widget(self.next_button)
        nav_bar.add_widget(menu_button)
        self.root.add_widget(nav_bar)

        self.prompt.bind(on_text_validate=self.send_message)
        self.load_session(-1)  # Load latest session

        return self.root

    def load_session(self, index):
        self.sessions = list_sessions()
        if not self.sessions:
            self.new_session()
            return

        if index < 0:
            index = len(self.sessions) - 1

        if 0 <= index < len(self.sessions):
            self.session_index = index
            filename = self.sessions[index]
            with open(os.path.join(SESSIONS_DIR, filename)) as f:
                self.current_session = json.load(f)
            rst_content = "\n\n".join([f"**{msg['role']}**:\n\n{msg['content']}" for msg in self.current_session['messages']])
            self.display.text = rst_content

    def save_current_session(self):
        if self.current_session:
            filename = self.current_session['filename']
            with open(os.path.join(SESSIONS_DIR, filename), 'w') as f:
                json.dump(self.current_session, f, indent=2)

    def new_session(self):
        timestamp = str(int(time.time()))
        filename = f"session_{timestamp}.json"
        self.current_session = {
            "filename": filename,
            "model": self.config_data.data["default_model"],
            "messages": []
        }
        self.session_index = len(self.sessions)
        self.sessions.append(filename)
        if self.config_data.data["initial_prompt"]:
            self.send_message(text=self.config_data.data["initial_prompt"], from_init=True)

    def send_message(self, instance=None, text=None, from_init=False):
        message = text if text else self.prompt.text.strip()
        if not message:
            return

        self.current_session['messages'].append({"role": "user", "content": message})
        self.prompt.text = ""
        self.save_current_session()
        self.display.text += f"\n\n**user**:\n\n{message}"

        # Get response from local LLM
        response = requests.post(f"{self.config_data.data['ollama_url']}/api/generate", json={
            "model": self.current_session['model'],
            "prompt": message,
            "format": "rst"
        })
        if response.status_code == 200:
            reply = response.json().get("response", "[No response]")
            self.current_session['messages'].append({"role": "assistant", "content": reply})
            self.save_current_session()
            self.display.text += f"\n\n**assistant**:\n\n{reply}"

    def go_back(self, instance):
        if self.session_index > 0:
            self.load_session(self.session_index - 1)

    def go_next_or_new(self, instance):
        if self.session_index < len(self.sessions) - 1:
            self.load_session(self.session_index + 1)
        else:
            self.new_session()
            self.load_session(-1)

    def open_menu(self, instance):
        menu = BoxLayout(orientation='vertical', size_hint=(None, None), size=(200, 150))
        cfg_btn = Button(text="Configuration", on_press=self.open_config)
        about_btn = Button(text="About", on_press=self.open_about)
        menu.add_widget(cfg_btn)
        menu.add_widget(about_btn)
        popup = Popup(title="Menu", content=menu, size_hint=(None, None), size=(250, 200))
        popup.open()

    def open_about(self, instance):
        content = Label(text="LLM Chat GUI using Kivy\nBuilt with Ollama integration")
        popup = Popup(title="About", content=content, size_hint=(None, None), size=(300, 200))
        popup.open()

    def open_config(self, instance):
        layout = BoxLayout(orientation='vertical')

        url_input = TextInput(text=self.config_data.data["ollama_url"], hint_text="Ollama URL")
        init_prompt_input = TextInput(text=self.config_data.data["initial_prompt"], hint_text="Initial prompt")
        models_box = BoxLayout(orientation='vertical', size_hint_y=None)
        models_box.bind(minimum_height=models_box.setter('height'))

        model_checkboxes = {}
        try:
            models = requests.get(f"{self.config_data.data['ollama_url']}/api/tags").json().get("models", [])
        except Exception:
            models = []

        for model in models:
            box = BoxLayout(size_hint_y=None, height=30)
            checkbox = CheckBox(active=model["name"] == self.config_data.data["default_model"])
            model_checkboxes[model["name"]] = checkbox
            box.add_widget(checkbox)
            box.add_widget(Label(text=model["name"]))
            models_box.add_widget(box)

        def save_config(instance):
            self.config_data.data["ollama_url"] = url_input.text
            self.config_data.data["initial_prompt"] = init_prompt_input.text
            for name, cb in model_checkboxes.items():
                if cb.active:
                    self.config_data.data["default_model"] = name
            self.config_data.save()
            popup.dismiss()

        layout.add_widget(Label(text="Ollama URL"))
        layout.add_widget(url_input)
        layout.add_widget(Label(text="Initial Prompt"))
        layout.add_widget(init_prompt_input)
        layout.add_widget(Label(text="Select Default Model"))
        scroll = ScrollView(size_hint=(1, None), size=(300, 100))
        scroll.add_widget(models_box)
        layout.add_widget(scroll)
        layout.add_widget(Button(text="Save", on_press=save_config))

        popup = Popup(title="Configuration", content=layout, size_hint=(None, None), size=(400, 500))
        popup.open()

if __name__ == '__main__':
    LLMApp().run()
