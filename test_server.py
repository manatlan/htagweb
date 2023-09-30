from htag import Tag
import asyncio
import pytest,sys,io
import multiprocessing,threading
import time
from htagweb.appserver import processHrServer
from htagweb.server.client import HrPilot


@pytest.fixture()
def server():
    p=multiprocessing.Process(target=processHrServer)
    p.start()

    time.sleep(1)
    yield "x"
    p.terminate()


@pytest.mark.asyncio
async def test_base( server ):
    uid ="u1"
    p=HrPilot(uid,"test_hr:App","//")
    html=await p.start()
    assert html.startswith("<!DOCTYPE html><html>")

    actions=await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )
    assert "update" in actions

    # await p.kill()
    # await p.kill()
    # await p.kill()


if __name__=="__main__":
    p=multiprocessing.Process(target=processHrServer)
    try:
        p.start()
        time.sleep(1)

        asyncio.run( test_base(42) )
    finally:
        p.terminate()