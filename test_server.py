from htag import Tag
import asyncio
import pytest,sys,io
import multiprocessing,threading
import time
from htagweb.appserver import processHrServer
from htagweb.server.client import HrPilot
import redys.v2
import threading


@pytest.fixture()
def server():
    p=multiprocessing.Process(target=processHrServer)
    p.start()

    yield "x"

    p.terminate()


@pytest.mark.asyncio
async def test_base( server ):

    # while 1:
    #     try:
    #         if await redys.v2.AClient().get("hrserver_orchestrator_running"):
    #             break
    #     except Exception as e:
    #         print(e)
    #     await asyncio.sleep(0.5)


    uid ="u1"
    p=HrPilot(uid,"test_hr:App","//")
    # html=await p.start()
    # assert html.startswith("<!DOCTYPE html><html>")

    # actions=await p.interact( oid="ut", method_name="doit", args=[], kargs={}, event={} )
    # assert "update" in actions




if __name__=="__main__":
    p=multiprocessing.Process(target=processHrServer)
    try:
        p.start()
        time.sleep(1)

        asyncio.run( test_base(42) )
    finally:
        p.terminate()