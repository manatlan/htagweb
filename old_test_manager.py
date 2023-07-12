import pytest
import asyncio
from htag import Tag
from requests import Session
from htagweb.manager_old import Manager



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

    ses=dict(cpt=42)


    m=Manager()
    uid="u1"

    try:
        fqn="test_hr.App"

        x=m.ht_create(uid,ses,fqn,"//jscom")
        assert isinstance(x,str)
        assert "//jscom" in x
        assert "function action(" in x
        assert ">say hello</Button>" in x
        assert ">42</cpt>" in x

        data=dict(id="ut",method="doit",args=(),kargs={})
        x=m.ht_interact(uid,ses,fqn, data)
        assert isinstance(x,dict)
        assert "update" in x
        ll=list(x["update"].items())
        assert len(ll) == 1 # one update
        id,content = ll[0]
        assert isinstance( id, int) and id
        assert isinstance( content, str) and content

        # assert the cpt var was incremented after interaction
        assert ses["cpt"]==43

    finally:
        m.shutdown()


if __name__=="__main__":
    # asyncio.run( test_the_base() )
    asyncio.run( test_htag_ok() )
