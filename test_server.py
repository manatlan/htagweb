from htag import Tag
import asyncio
import pytest
from htagweb.hrclient import HrClient
import re

@pytest.mark.asyncio
async def test_new1( ):
    try:
        hr=HrClient("ut1","main")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","main.AppUnknown")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","main:App")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","mainUnknown.AppUnknown")
        with pytest.raises(Exception):
            await hr.create("//ddd")

        hr=HrClient("ut1","examples.simple.App")
        html = await hr.create("//ddd")
        assert "<!DOCTYPE html>" in html
        assert "function action" in html
    finally:
        await HrClient.clean()

@pytest.mark.asyncio
async def test_new2( ):
    # hr2=HrClient("u2","main.App")
    # await hr2.create("//js")
    try:
        hr=HrClient("ut2","examples.simple.App")

        htm=await hr.create("//js") # will create fifo/process
        htm=await hr.create("//js") # will reuse fifo and reuse process
        #print(htm)
        print("------------------------------------------------")
        id="12156456465456413"
        datas={"id":int(id),"method":"__on__","args":["onclick-"+id],"kargs":{},"event":{}}
        actions=await hr.interact(**datas)
        assert "err" in actions

        id=re.findall( r'id="(\d+)"',htm )[-1]
        datas={"id":int(id),"method":"__on__","args":["onclick-"+id],"kargs":{},"event":{}}
        for _ in range(3):
            actions=await hr.interact(**datas)
            assert "update" in actions
        print("------------------------------------------------")
    finally:
        await HrClient.clean()

# @pytest.mark.asyncio
# async def test_base( ):

#     ses={}

#     uid ="u1"
#     p=HrClient(uid,"test_hr:App","//",)
#     html=await p.start()
#     assert html.startswith("<!DOCTYPE html><html>")

#     # session.cpt initialized at "0"
#     assert ">0</cpt>" in html

#     p=HrClient(uid,"test_hr:App","//")
#     html=await p.start()
#     assert html.startswith("<!DOCTYPE html><html>")

#     # session.cpt stays at "0"
#     assert ">0</cpt>" in html

#     actions=await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )
#     assert "update" in actions
#     update_rendering = list(actions["update"].values())[0]

#     # session.cpt was incremented at "1"
#     assert ">1</cpt2>" in update_rendering

#     # test a method inherited from serverclient
#     ll=await p.list()
#     assert len(ll)==1
#     assert ll[0].uid == uid
#     assert ll[0].fqn == "test_hr:App"


# @pytest.mark.asyncio
# async def test_app_block_killed( server ):
#     # test that a blocking interaction will be stopped
#     # and app killed

#     uid ="u2"
#     fqn="test_hr:AppFuck"
#     p=HrClient(uid,fqn,"//",timeout_interaction=2)
#     html=await p.start()
#     assert html.startswith("<!DOCTYPE html><html>")

#     # app is running
#     assert fqn in [i.fqn for i in await p.list()]

#     await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )

#     # app was killed
#     assert fqn not in [i.fqn for i in await p.list()]


# @pytest.mark.asyncio
# async def test_app_suicide( server ):
#     # test that a blocking interaction will be stopped
#     # and app killed

#     uid ="u2"
#     fqn="test_hr:App"
#     p=HrClient(uid,fqn,"//",timeout_inactivity=1)
#     html=await p.start()
#     assert html.startswith("<!DOCTYPE html><html>")


#     # app is running
#     assert fqn in [i.fqn for i in await p.list()]


#     # app will suicide during this period
#     await asyncio.sleep(2)


#     # app was killed
#     assert fqn not in [i.fqn for i in await p.list()]



# if __name__=="__main__":
#     s=asyncio.run( startServer())

#     asyncio.run( test_base("x") )
#     asyncio.run( test_app_block_killed("x") )

#     asyncio.run( stopServer(s))



