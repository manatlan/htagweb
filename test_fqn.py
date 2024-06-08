import pytest
from htag import Tag
from htagweb.fqn import findfqn

from examples import simple,main

class App(Tag.div):
    pass

def test_fqn():
    assert findfqn(App) == "test_fqn.App" # not "__main__.App" !!!!!

def test_fqn2():
    assert findfqn("test_fqn.App") == "test_fqn.App" 

def test_fqn3():
    assert findfqn("test_fqn:App") == "test_fqn.App" 

def test_fqn4():
    assert findfqn(simple) == "examples.simple.App" 

def test_module_without_App():
    with pytest.raises(Exception): # Exception: module should contains a 'App' (htag.Tag class)
        findfqn(main)

def test_bad_fqn():
    with pytest.raises(Exception): # Exception: ...is not a 'full qualified name'
        findfqn("main")
