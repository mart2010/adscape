import pytest
from main import *
import zipfile
import os
import pathlib

my_session = Session(meta={'llm': 'lxxx'}, questions=['q1', 'q2'], answers=['a1','a2'])

def test_Session():
    assert Session.from_json(my_session.to_json()) == my_session


def cleanup(session_zfile: str):
    session_zfile = pathlib.Path(session_zfile)
    if session_zfile.exists():
        os.remove(session_zfile)
       
    for s_f in session_zfile.parent.iterdir():
        if s_f.name[:8] == 'session_' and s_f.suffix == '.json' and s_f.is_file():
            os.remove(s_f)


def test_SessionStore():

    m_s = './my_store.zip'
    cleanup(m_s)

    ss = SessionStore(m_s)
    assert ss.current_idx == -1

    m_z = zipfile.ZipFile(m_s)
    assert m_z.filename == m_s
    assert m_z.namelist() == []
    m_z.close()

    ss.add_session(my_session)
    assert ss.sessions[0] == my_session
    assert pathlib.Path(f'./{my_session.name}').exists()
    ss.store_sessions()
    assert not pathlib.Path(f'./{my_session.name}').exists()

    # to mock an existing session store and test get_session, next, previous ...


    cleanup(m_s)    

