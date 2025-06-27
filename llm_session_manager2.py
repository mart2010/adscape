import os
import json
import requests
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.rst import RstDocument
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.actionbar import ActionBar, ActionView, ActionPrevious, ActionOverflow, ActionButton

SESSIONS_DIR = "sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

class Config:
    def __init__(self):
        self.config_file = "config.json"
        self.data = self.load()

    def load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {"ollama_url": "http://localhost:11434", "selected_model": "", "initial_prompt": ""}

    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=2)

config = Config()

class ConversationApp(App):
    def build(self):
        self.title = "LLM Conversation Manager"
        self.model = config.data.get("selected_model", "")
        self.session_files = sorted([f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")])
        self.current_session_index = -1
        self.current_session = {}
        self.session_label = Label(size_hint_y=None)
        self.rst_view = RstDocument(text="", size_hint_y=None)
        self.prompt_input = TextInput(hint_text="Ask something...", multiline=False)
        self.prompt_input.bind(on_text_validate=self.send_prompt)
        
        layout = BoxLayout(orientation='vertical')
        self.scroll = ScrollView(size_hint=(1, 0.8))
        self.scroll.add_widget(self.rst_view)

        layout.add_widget(self.scroll)
        layout.add_widget(self.prompt_input)

        btn_layout = BoxLayout(size_hint_y=0.1)
        self.back_btn = Button(text="< Back")
        self.next_btn = Button(text="Next >")
        self.back_btn.bind(on_press=self.previous_session)
        self.next_btn.bind(on_press=self.next_or_new_session)
        btn_layout.add_widget(self.back_btn)
        btn_layout.add_widget(self.next_btn)

        layout.add_widget(btn_layout)

        action_bar = ActionBar()
        action_view = ActionView()
        action_view.add_widget(ActionPrevious(with_previous=False, title="LLM Manager"))
        action_view.add_widget(ActionOverflow())
        action_view.add_widget(ActionButton(text="Configuration", on_press=self.open_config))
        action_view.add_widget(ActionButton(text="About", on_press=self.open_about))
        action_bar.add_widget(action_view)

        root = BoxLayout(orientation='vertical')
        root.add_widget(action_bar)
        root.add_widget(layout)

        self.new_session()
        return root

    def load_session(self, filename):
        with open(os.path.join(SESSIONS_DIR, filename), 'r') as f:
            self.current_session = json.load(f)
        self.update_rst_view()

    def save_session(self):
        if self.current_session:
            with open(os.path.join(SESSIONS_DIR, self.current_session['filename']), 'w') as f:
                json.dump(self.current_session, f, indent=2)

    def update_rst_view(self):
        conversation = self.current_session.get("conversation", [])
        self.rst_view.text = "\n\n".join([entry["role"] + ":\n\n" + entry["content"] for entry in conversation])

    def send_prompt(self, instance):
        user_input = self.prompt_input.text
        if not user_input.strip():
            return
        self.prompt_input.text = ""
        self.current_session["conversation"].append({"role": "User", "content": user_input})
        self.query_llm(user_input)
        self.save_session()
        self.update_rst_view()

    def query_llm(self, prompt):
        url = config.data["ollama_url"] + "/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt + "\n(Please respond in reStructuredText format)",
            "stream": False
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            content = response.json().get("response", "(No response)")
            self.current_session["conversation"].append({"role": self.model, "content": content})
        except Exception as e:
            self.current_session["conversation"].append({"role": "Error", "content": str(e)})

    def new_session(self):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.json"
        self.current_session = {
            "filename": filename,
            "model": self.model,
            "timestamp": timestamp,
            "conversation": []
        }
        self.session_files.append(filename)
        self.current_session_index = len(self.session_files) - 1
        if config.data.get("initial_prompt"):
            self.send_prompt(TextInput(text=config.data["initial_prompt"]))

    def previous_session(self, instance):
        if self.current_session_index > 0:
            self.current_session_index -= 1
            self.load_session(self.session_files[self.current_session_index])

    def next_or_new_session(self, instance):
        if self.current_session_index < len(self.session_files) - 1:
            self.current_session_index += 1
            self.load_session(self.session_files[self.current_session_index])
        else:
            self.new_session()

    def open_config(self, instance):
        content = BoxLayout(orientation='vertical')
        url_input = TextInput(text=config.data.get("ollama_url", ""), hint_text="Local Ollama URL")
        models_box = BoxLayout(orientation='vertical')
        model_options = []
        try:
            response = requests.get(config.data["ollama_url"] + "/api/tags")
            model_options = response.json().get("models", [])
        except:
            model_options = []
        checkboxes = {}
        for model in model_options:
            box = BoxLayout()
            cb = CheckBox(group='models')
            if model["name"] == config.data.get("selected_model"):
                cb.active = True
            lbl = Label(text=model["name"])
            checkboxes[model["name"]] = cb
            box.add_widget(cb)
            box.add_widget(lbl)
            models_box.add_widget(box)

        initial_prompt = TextInput(text=config.data.get("initial_prompt", ""), hint_text="Optional initial prompt")

        def save_config(instance):
            config.data["ollama_url"] = url_input.text
            config.data["initial_prompt"] = initial_prompt.text
            for name, cb in checkboxes.items():
                if cb.active:
                    config.data["selected_model"] = name
                    break
            config.save()
            popup.dismiss()

        save_btn = Button(text="Save", on_press=save_config)
        content.add_widget(Label(text="Ollama URL:"))
        content.add_widget(url_input)
        content.add_widget(Label(text="Models:"))
        content.add_widget(models_box)
        content.add_widget(Label(text="Initial Prompt:"))
        content.add_widget(initial_prompt)
        content.add_widget(save_btn)

        popup = Popup(title="Configuration", content=content, size_hint=(0.9, 0.9))
        popup.open()

    def open_about(self, instance):
        content = Label(text="LLM Session Manager App\nBuilt with Kivy\nSelf-hosted Ollama integration", halign='center')
        popup = Popup(title="About", content=content, size_hint=(0.6, 0.4))
        popup.open()

if __name__ == '__main__':
    ConversationApp().run()
