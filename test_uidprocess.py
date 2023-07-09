import pytest
import asyncio
from htag import Tag
from htagweb.uidprocess import UidProxy,UidProxyException


class App(Tag.body):
    def init(self):
        self.b=Tag.Button("say hello",_onclick=self.bind.doit() )
        self+=self.b
    def doit(self):
        self+="hello"


@pytest.mark.asyncio
async def test_bad_interop_unknown_method():
    p1=UidProxy("u1",{})
    with pytest.raises( UidProxyException ):
        await p1.unknown(42) # >> Process u1: error ''unknown''
    UidProxy.shutdown()

@pytest.mark.asyncio
async def test_bad_interop_bad_signature():
    p1=UidProxy("u1",{})
    with pytest.raises( UidProxyException ):
        await p1.ping() # >> Process u1: error 'ping() missing 1 required positional argument: 'msg''
    UidProxy.shutdown()


@pytest.mark.asyncio
async def test_ok_ping():
    p1=UidProxy("u1",{})
    r=await p1.ping("manatlan")
    assert r == "hello manatlan"
    UidProxy.shutdown()


@pytest.mark.asyncio
async def test_htag_ok():

    p1=UidProxy("u1",{})

    x=await p1.ht_create("test_uidprocess.App","//jscom")
    assert isinstance(x,str)
    assert "//jscom" in x
    assert "function action(" in x
    assert ">say hello</Button>" in x

    data=dict(id="ut",method="doit",args=(),kargs={})
    x=await p1.ht_interact("test_uidprocess.App", data)
    assert isinstance(x,dict)
    assert "update" in x
    ll=list(x["update"].items())
    assert len(ll) == 1 # one update
    id,content = ll[0]
    assert isinstance( id, int) and id
    assert isinstance( content, str) and content

    UidProxy.shutdown()

# @pytest.mark.asyncio
# async def test_pye_ok():

#     p1=UidProxy("u1")

#     string="""
# import sys

# async def test():
#     return sys.version

# print( await test(), web.request.method, web.request.url )
# web.response.status_code=201
# web.response.content_type="text/plain"
# """
#     x=await p1.exec( string )
#     assert x.status_code==201
#     assert x.headers["content-type"].startswith("text/plain")
#     assert x.body and isinstance(x.body,bytes)

#     UidProxy.shutdown()


@pytest.mark.asyncio
async def test_com_after_quit():
    try:
        p1=UidProxy("u1",{})
        await p1.ping("x")

        p1.quit()
        await asyncio.sleep(0.1)

        with pytest.raises( UidProxyException ):
            await p1.ping("hello") # UidProxyException(f"queue is closed")

    finally:
        UidProxy.shutdown()


@pytest.mark.asyncio
async def test_com_after_timeout_death():
    try:
        p1=UidProxy("u1",{},0.5)
        await p1.ping("x")

        await asyncio.sleep(1)

        with pytest.raises( UidProxyException ):
            await p1.ping("hello") # UidProxyException(f"queue is closed on process side")

    finally:
        UidProxy.shutdown()


if __name__=="__main__":
    asyncio.run( test_bad_interop_unknown_method() )
    asyncio.run( test_bad_interop_bad_signature() )
    asyncio.run( test_ok_ping() )
    asyncio.run( test_htag_ok() )
    # asyncio.run( test_pye_ok() )
    asyncio.run( test_com_after_quit() )
    asyncio.run( test_com_after_timeout_death() )