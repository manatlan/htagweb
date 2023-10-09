from htag import Tag
import asyncio
import pytest,sys,io
import multiprocessing,threading
import time

import redys.v2
from htagweb.server import ServerClient, startServer, stopServer
from htagweb.server.client import HrClient
import threading


@pytest.fixture()
def server(): # nearly "same code" as lifespan
    # start a process loop (with redys + hrserver)
    s=asyncio.run( startServer())

    yield "x"

    asyncio.run( stopServer(s))


@pytest.mark.asyncio
async def test_base( server ):

    ses={}

    uid ="u1"
    p=HrClient(uid,"test_hr:App","//",)
    html=await p.start()
    assert html.startswith("<!DOCTYPE html><html>")

    # session.cpt initialized at "0"
    assert ">0</cpt>" in html

    p=HrClient(uid,"test_hr:App","//")
    html=await p.start()
    assert html.startswith("<!DOCTYPE html><html>")

    # session.cpt stays at "0"
    assert ">0</cpt>" in html

    actions=await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )
    assert "update" in actions
    update_rendering = list(actions["update"].values())[0]
    
    # session.cpt was incremented at "1"
    assert ">1</cpt2>" in update_rendering

    # test a method inherited from serverclient
    ll=await p.list()
    assert len(ll)==1
    assert ll[0].uid == uid
    assert ll[0].fqn == "test_hr:App"


@pytest.mark.asyncio
async def test_app_block_killed( server ):
    # test that a blocking interaction will be stopped
    # and app killed

    uid ="u2"
    fqn="test_hr:AppFuck"
    p=HrClient(uid,fqn,"//",timeout_interaction=2)
    html=await p.start()
    assert html.startswith("<!DOCTYPE html><html>")

    # app is running
    assert fqn in [i.fqn for i in await p.list()]

    await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )

    # app was killed
    assert fqn not in [i.fqn for i in await p.list()]



if __name__=="__main__":
    s=asyncio.run( startServer())

    asyncio.run( test_base("x") )
    asyncio.run( test_app_block_killed("x") )

    asyncio.run( stopServer(s))



