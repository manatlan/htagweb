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

    uid ="u1"
    p=HrClient(uid,"test_hr:App","//")
    html=await p.start()
    assert html.startswith("<!DOCTYPE html><html>")

    p=HrClient(uid,"test_hr:App","//")
    html=await p.start()
    assert html.startswith("<!DOCTYPE html><html>")

    actions=await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )
    assert "update" in actions


    s=ServerClient()
    ll=await s.list()
    assert len(ll)==1
    assert ll[0].uid == uid
    assert ll[0].fqn == "test_hr:App"




if __name__=="__main__":
    s=asyncio.run( startServer())

    asyncio.run( test_base("x") )

    asyncio.run( stopServer(s))



