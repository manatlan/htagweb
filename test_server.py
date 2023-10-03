from htag import Tag
import asyncio
import pytest,sys,io
import multiprocessing,threading
import time
from htagweb.appserver import processHrServer
from htagweb.server import kill_hrserver, wait_hrserver
from htagweb.server.client import HrClient
import redys.v2
import threading


@pytest.fixture()
def server():
    p=multiprocessing.Process(target=processHrServer)
    p.start()

    asyncio.run( wait_hrserver() )

    yield "x"

    asyncio.run( kill_hrserver() )


@pytest.mark.asyncio
async def test_base( server ):

    uid ="u1"
    p=HrClient(uid,"test_hr:App","//")
    html=await p.start()
    assert html.startswith("<!DOCTYPE html><html>")

    actions=await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )
    assert "update" in actions




if __name__=="__main__":
    pass
    # p=multiprocessing.Process(target=processHrServer)
    # try:
    #     p.start()
    #     time.sleep(1)

    #     asyncio.run( test_base(42) )
    # finally:
    #     asyncio.run( kill_hrserver() )