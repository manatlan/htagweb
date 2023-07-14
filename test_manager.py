import pytest,asyncio

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

        # trying to double start is a bug ;-)
        with pytest.raises( Exception ):
            assert await m.start()          # can't start a 2nd ;-)

        # assert that a second manager can't start the server part (IRL)
        mm=Manager()
        assert not await mm.start()

        r=await m.ping("bob")
        assert r=="hello bob"

        assert len(await m.all()) == 0      # no creating a user for ping ^
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

        # asser we got one user
        assert len(await m.all()) == 1


@pytest.mark.asyncio
async def test_htag_bad_fqn():
    async with Manager() as m:
        uid="u1"
        fqn="unknown.fqn"

        with pytest.raises(Exception):
            await m.ht_create(uid,fqn,"//jscom")

        # assert we got one user
        assert len(await m.all()) == 1


@pytest.mark.asyncio
async def test_htag_bad():
    async with Manager() as m:
        uid="u666"
        fqn="test_hr.App"

        # the app is ok, but session.cpt is not here
        x=await m.ht_create(uid,fqn,"//jscom")
        assert isinstance(x,str)

        # we've got an "init error"
        assert "init error : \'cpt\'" in x

        # but the interaction will 'work', with session trouble
        data=dict(id="ut",method="doit",args=(),kargs={})
        x=await m.ht_interact(uid,fqn, data)
        assert isinstance(x,dict)
        assert x["err"]

        # assert we got the user in memory
        assert uid in await m.all()


@pytest.mark.asyncio
async def test_htag_bad_bug_interact():
    async with Manager() as m:
        uid="u666x2"
        fqn="test_hr.App"

        Users.use(uid).session["cpt"]=42        # create a session !!!

        x=await m.ht_create(uid,fqn,"//jscom")
        assert isinstance(x,str)
        assert "//jscom" in x
        assert "function action(" in x
        assert ">say hello</Button>" in x
        assert ">42</cpt>" in x

        # set a var in ses which will bug in interact
        Users.use(uid).session["cpt"]="NaN"

        data=dict(id="ut",method="doit",args=(),kargs={})
        x=await m.ht_interact(uid,fqn, data)
        assert isinstance(x,dict)
        assert x["err"]

        # assert we got the user in memory
        assert uid in await m.all()

@pytest.mark.asyncio
async def test_stress():
    import random
    async with Manager() as m:
        for i in range(1000):
            ll=[Users.use("mstress%s"%i) for i in range( 1+int(i/100))]
            one=random.choice(ll)
            one.session["cpt"]=79

            x=random.choice([1,2])
            if x==1:
                r=await m.ping( one.uid )
                print(i,r)
            else:
                fqn = "test_hr.App"
                x=await m.ht_create(one.uid,fqn,"//jscom")
                assert isinstance(x,str)

                data=dict(id="ut",method="doit",args=(),kargs={})
                x=await m.ht_interact(one.uid, fqn, data)
                assert isinstance(x,dict),x
                assert "update" in x
                print(i,x)

if __name__=="__main__":
    # asyncio.run( test_the_base() )
    # asyncio.run( test_htag_ok() )
    asyncio.run( test_stress() )
