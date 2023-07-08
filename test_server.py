import pytest
from htag import Tag
from htagweb import findfqn
import sys
class MyTag(Tag.div): pass
class App(Tag.div): pass

def test_fqn():
    with pytest.raises( Exception ):
        findfqn(42)

    with pytest.raises( Exception ):
        findfqn("mod_name")

    assert findfqn("mod.name") == "mod.name"
    assert findfqn(MyTag) in ["__main__.MyTag","test_server.MyTag"]
    assert findfqn(sys.modules[__name__]) in ["__main__.App","test_server.App"]

if __name__=="__main__":
    test_fqn()