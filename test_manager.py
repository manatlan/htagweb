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

@pytest.mark.asyncio
async def test_htag_ok():

    m=Manager()
    uid="u1"

    x=m.ht_create(uid,"test_uidprocess.App","//jscom")
    assert isinstance(x,str)
    assert "//jscom" in x
    assert "function action(" in x
    assert ">say hello</Button>" in x

    data=dict(id="ut",method="doit",args=(),kargs={})
    x=m.ht_interact(uid,"test_uidprocess.App", data)
    assert isinstance(x,dict)
    assert "update" in x
    ll=list(x["update"].items())
    assert len(ll) == 1 # one update
    id,content = ll[0]
    assert isinstance( id, int) and id
    assert isinstance( content, str) and content

    m.shutdown()

# @pytest.mark.asyncio
# async def test_pye_ok():

#     m=Manager()
#     uid="u1"

#     string="""
# import sys

# async def test():
#     return sys.version

# print( await test(), web.request.method, web.request.url )
# web.response.status_code=201
# web.response.content_type="text/plain"
# """
#     x=m.exec( uid, string )
#     assert x.status_code==201
#     assert x.headers["content-type"].startswith("text/plain")
#     assert x.body and isinstance(x.body,bytes)

#     m.shutdown()

if __name__=="__main__":
    asyncio.run( test_the_base() )
    asyncio.run( test_htag_ok() )
    # asyncio.run( test_pye_ok() )
