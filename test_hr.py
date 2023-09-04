from htag import Tag
from htag.render import HRenderer
import asyncio
import pytest

class App(Tag.body):
    def init(self):
        self.b=Tag.Button("say hello",_onclick=self.bind.doit() )
        self+=self.b
        self+=Tag.cpt(self.state['cpt'])
        self.state['created']=True
    def doit(self):
        self.state['cpt']=int(self.state['cpt'])+1
        self.state['interacted']=True
        self+="hello" +Tag.cpt2(self.state['cpt'])

@pytest.mark.asyncio
async def test_hr():
    ses=dict(cpt=1)
    hr=HRenderer( App ,"//",session = ses)

    assert ses["created"]
    assert ses["cpt"]==1

    r=await hr.interact( id(hr.tag), "doit", [], {}, {})
    assert "update" in r

    assert ses["interacted"]
    assert ses["cpt"]==2
    print("ok")

if __name__=="__main__":
    asyncio.run(test_hr())