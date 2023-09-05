import pytest
from htagweb.sessions import createFile, createShm, createMem

def test_sessions():
    for method in [createFile, createShm, createMem]:
        state = method(uid)
        try:
            nb=state.get("nb",0)
            nb+=1
            state["nb"]=nb
            assert state["nb"]==1
        finally:
            state.clear()
