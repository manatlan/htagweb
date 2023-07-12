import pytest
import asyncio
from htag import Tag
from requests import Session


from htagweb.manager import Manager



@pytest.mark.asyncio
async def test_the_base():

    c=Manager()
    await asyncio.sleep(0.1)

    r=await c.ping("bob")
    assert r=="hello bob"
    await c.stop()

@pytest.mark.asyncio
async def test_htag_ok():

    ses=dict(cpt=42)


    m=Manager()
    await asyncio.sleep(0.5)
    uid="u1"
    try:
        fqn="test_hr.App"

        await m.setsession(uid,ses)

        x=await m.ht_create(uid,fqn,"//jscom")
        assert isinstance(x,str)
        assert "//jscom" in x
        assert "function action(" in x
        assert ">say hello</Button>" in x
        assert ">42</cpt>" in x

        data=dict(id="ut",method="doit",args=(),kargs={})
        x=await m.ht_interact(uid,fqn, data)
        assert isinstance(x,dict)
        assert "update" in x
        ll=list(x["update"].items())
        assert len(ll) == 1 # one update
        id,content = ll[0]
        assert isinstance( id, int) and id
        assert isinstance( content, str) and content

        # assert the cpt var was incremented after interaction
        async with m.session(uid) as s:
            assert s["cpt"]==43

    finally:
        await m.stop()


if __name__=="__main__":
    # asyncio.run( test_the_base() )
    asyncio.run( test_htag_ok() )
