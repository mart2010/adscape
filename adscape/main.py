
import zipfile
import pathlib
import dataclasses
from datetime import datetime
import os
import json

@dataclasses.dataclass
class Session():
    name: str = f'session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json' 
    meta: dict = None
    questions: list[str] = None
    answers: list[str] = None

    @classmethod
    def from_json(cls, json_s):
        json_d = json.loads(json_s)
        return Session(**json_d)

    def to_json(self):
        return json.dumps(dataclasses.asdict(self))
    
    def has_content(self):
        return self.questions is not None
    


class SessionStore():

    # to bet defined by caller ..
    # zip_file = pathlib.Path('kivy_data_folder', 'session_store.archive') 
    
    def __init__(self, archive_file) -> None:
        self.archive_file = pathlib.Path(archive_file)
        self.sessions : list[Session] = None
        
        # in case of app crash or not properly closed
        all_sorted_names = self.store_sessions()
        self.sessions = [Session(name=n) for n in all_sorted_names]
        self.current_idx = len(self.sessions)-1


    def add_session(self, new_session):
        self.sessions.append(new_session)
        with open(new_session.name, 'w', encoding='utf-8') as session_f:
            session_f.write(new_session.to_json())
    
    def fetch_previous_session(self, size=10):
        if not self.is_empty() and self.current_idx > 0:
            #cache ´size´ previous session
            with zipfile.ZipFile(self.archive_file, mode='r') as z_f:
                from_idx = 0 if self.current_idx-size < 0 else self.current_idx-size
                for i in range(from_idx, self.current_idx+1):
                    with z_f.open(name=self.sessions[i].name) as session_f:
                        # only if not fecthed previously
                        if not self.sessions[i].has_content():
                            session_json = json.load(session_f)
                            self.sessions[i] = Session.from_json(session_json)

            return self.sessions[self.current_idx]
    
    def previous_session(self):
        if  0 < self.current_idx <= len(self.sessions) - 1:
            self.current_idx -= 1
            return self.sessions[self.current_idx]
    
    def next_session(self):
        if 0 <= self.current_idx < len(self.sessions) - 1:
            self.current_idx += 1
            return self.sessions[self.current_idx]
    
    def store_sessions(self):
        """Save all pending session files
        and return all session-name sorted by name
        """
        with zipfile.ZipFile(self.archive_file, mode='a') as z_f:
            for session_file in self.pending_session_files():
                z_f.write(session_file)
            names = sorted(z_f.namelist())
        # clean-up pending session-files
        for session_file in self.pending_session_files():
            os.remove(session_file)
        return names

    def is_empty(self):
        return len(self.sessions) == 0
    
    def pending_session_files(self):
        for session_file in self.archive_file.parent.iterdir():
            if session_file.name[:8] == 'session_' and session_file.suffix == '.json' and session_file.is_file():
                yield session_file
        