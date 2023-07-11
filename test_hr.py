from htag import Tag
from htag.render import HRenderer
import asyncio

class App(Tag.body):
    def init(self):
        self.b=Tag.Button("say hello",_onclick=self.bind.doit() )
        self+=self.b
        self+=Tag.cpt(self.session['cpt'])
        self.session['created']=True
    def doit(self):
        self+="hello"
        self.session['cpt']+=1
        self.session['interacted']=True

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