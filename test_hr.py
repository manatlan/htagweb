from htag import Tag
from htag.render import HRenderer
import asyncio
import pytest

class App(Tag.body):
    
    def init(self):
        self.b=Tag.Button("say hello",_onclick=self.bind.doit() )
        self+=self.b
        self+=Tag.cpt(self.session.get('cpt',0))
        self.session['created']=True

    def doit(self):
        self.session['cpt']=int(self.session.get('cpt',0))+1
        self.session['interacted']=True
        self+="hello" +Tag.cpt2(self.session['cpt'])
# 
class AppFuck(Tag.body):
    def init(self):
        self.b=Tag.Button("say hello",_onclick=self.bind.doit() )
        self+=self.b
    def doit(self):
        while 1:
            pass


@pytest.mark.asyncio
async def test_hr():
    ses=dict(cpt=1)
    hr=HRenderer( App ,"//",session = ses)
    assert str(hr).startswith("<!DOCTYPE html><html>")
    assert ses["created"]
    assert ses["cpt"]==1
    r=await hr.interact( id(hr.tag), "doit", [], {}, {})
    assert "update" in r
    assert ses["interacted"]
    assert ses["cpt"]==2
    print("ok")


if __name__=="__main__":
    asyncio.run(test_hr())