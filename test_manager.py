import pytest
import asyncio
from htag import Tag
from requests import Session


from htagweb.manager import Manager
from htagweb.uidprocess import Users

# #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
# # Override the pytest-asyncio event_loop fixture to make it session scoped. This is required in order to enable
# # async test fixtures with a session scope. More info: https://github.com/pytest-dev/pytest-asyncio/issues/68
# @pytest.fixture(scope="session")
# def event_loop(request):
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()
# #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\


@pytest.mark.asyncio
async def test_the_base():

    m=Manager()
    try:
        assert await m.start()

        with pytest.raises( Exception ):
            assert await m.start()          # can't start a 2nd ;-)

        r=await m.ping("bob")
        assert r=="hello bob"
    finally:
        await m.stop()


@pytest.mark.asyncio
async def test_the_base_base():
    async with Manager() as m:
        r=await m.ping("bob")
        assert r=="hello bob"



@pytest.mark.asyncio
async def test_htag_ok():
    async with Manager() as m:
        uid="u1"
        fqn="test_hr.App"

        Users.use(uid).session["cpt"]=42        # create a session !!!

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
        assert Users.get(uid).session["cpt"]==43

if __name__=="__main__":
    # asyncio.run( test_the_base() )
    # asyncio.run( test_htag_ok() )
    pass
