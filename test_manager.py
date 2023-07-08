import pytest
import asyncio
from htag import Tag
from htagweb.manager import Manager


# class App(Tag.body):
#     def init(self):
#         self.b=Tag.Button("say hello",_onclick=self.bind.doit() )
#         self+=self.b
#     def doit(self):
#         self+="hello"


@pytest.mark.asyncio
async def test_the_base():
    c=Manager()
    c=Manager() # no effect
    c=Manager() # no effect
    c=Manager() # no effect
    r=c.ping("bob")
    assert r=="hello bob"
    c.shutdown()
    c.shutdown() # no effect
    c.shutdown() # no effect


if __name__=="__main__":
    asyncio.run( test_the_base() )
