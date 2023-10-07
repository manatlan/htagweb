from htag import Tag
import asyncio
import pytest,sys,io
import multiprocessing,threading
import time
from htagweb.appserver import processHrServer,lifespan
from htagweb.server import ServerClient, kill_hrserver, wait_hrserver
from htagweb.server.client import HrClient
import threading


@pytest.fixture()
def server(): # nearly "same code" as lifespan
    # start a process loop (with redys + hrserver)
    process_hrserver=multiprocessing.Process(target=processHrServer)
    process_hrserver.start()

    # wait hrserver ready
    asyncio.run( wait_hrserver() )

    yield "x"
    # stop hrserver
    asyncio.run( kill_hrserver() )

    # wait process to finnish gracefully
    process_hrserver.join()


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
    pass
    # p=multiprocessing.Process(target=processHrServer)
    # try:
    #     p.start()
    #     time.sleep(1)

    #     asyncio.run( test_base(42) )
    # finally:
    #     asyncio.run( kill_hrserver() )