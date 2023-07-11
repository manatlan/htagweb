import pytest
import asyncio
from htag import Tag
from htagweb.uidprocess import UidProcess as UidProxy


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



@pytest.mark.asyncio
async def test_bad_interop_unknown_method():
    p1=UidProxy("u1",{})
    r = p1.unknown(42) # >> Process u1: error ''unknown''
    assert isinstance(r,Exception)

@pytest.mark.asyncio
async def test_bad_interop_bad_signature():
    p1=UidProxy("u1",{})
    r=p1.ping() # >> Process u1: error 'ping() missing 1 required positional argument: 'msg''
    assert isinstance(r,Exception)


@pytest.mark.asyncio
async def test_ok_ping():
    p1=UidProxy("u1",{})
    r=p1.ping("manatlan")
    assert r == "hello manatlan"
    p1.quit()


@pytest.mark.asyncio
async def test_htag_ok():

    ses=dict(cpt=42)

    p1=UidProxy("u1",ses)
    try:
        fqn = "test_uidprocess.App"

        x= p1.ht_create(fqn,"//jscom")
        assert isinstance(x,str)
        assert "//jscom" in x
        assert "function action(" in x
        assert ">say hello</Button>" in x
        assert ">42</cpt>" in x
        assert ses["created"]
        assert ses["cpt"]==42,ses

        data=dict(id="ut",method="doit",args=(),kargs={})
        x=p1.ht_interact(fqn, data)
        assert isinstance(x,dict)
        assert "update" in x
        ll=list(x["update"].items())
        assert len(ll) == 1 # one update
        id,content = ll[0]
        assert isinstance( id, int) and id
        assert isinstance( content, str) and content
        assert "hello" in content

        # assert the cpt var was incremented after interaction
        assert ses["cpt"]==43,p1.session
        assert ses["interacted"],ses

    finally:
        p1.quit()


@pytest.mark.asyncio
async def test_com_after_quit():
    p1=UidProxy("u1",{})
    p1.ping("x")
    p1.quit()

    await asyncio.sleep(0.1)

    r=p1.ping("hello") # UidProxyException(f"queue is closed")
    assert isinstance(r,Exception)



@pytest.mark.asyncio
async def test_com_after_timeout_death():
    p1=UidProxy("u1",{},0.5)
    p1.ping("x")

    await asyncio.sleep(1)

    r = p1.ping("hello") # UidProxyException(f"queue is closed on process side")
    print(r)
    assert isinstance(r,Exception)



if __name__=="__main__":
    # asyncio.run( test_bad_interop_unknown_method() )
    # asyncio.run( test_bad_interop_bad_signature() )
    # asyncio.run( test_ok_ping() )
    # asyncio.run( test_htag_ok() )
    # asyncio.run( test_com_after_quit() )
    asyncio.run( test_com_after_timeout_death() )