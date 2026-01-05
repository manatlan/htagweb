from htag import Tag
import asyncio
import pytest
from htagweb.hrclient import HrClient
import re

class BugInit(Tag.body):
    def init(self):
        a=42/0

import time

class AppBlockInteraction(Tag.body):
    def init(self,tempo):
        async def doit(ev):
            if tempo==-1:
                while 1: 
                    await asyncio.sleep(0.1)    # PERMIT THE LOOP to do its job
                    pass
            else:
                await asyncio.sleep(tempo)
            # time.sleep(tempo)
            self <="!!"
        self.b=Tag.Button("say hello",_onclick=doit )
        self+=self.b


@pytest.mark.asyncio
async def test_process_trouble_bad_moduleapp():
    hr=HrClient("u1","crash")
    try:
        await hr.create("//ddd")
    except Exception as e:
        assert "miss" in str(e)

@pytest.mark.asyncio
async def test_process_kaputt():
    hr=HrClient("u1","examples.kaputt.App")
    try:
        await hr.create("//ddd")
    except Exception as e:
        assert "invalid" in str(e)



@pytest.mark.asyncio
async def test_process_trouble_bad_app(): # but existing module
    hr=HrClient("u1","examples.simple.UNKOWN")
    try:
        await hr.create("//ddd")
    except Exception as e:
        assert "has no attribute" in str(e)

@pytest.mark.asyncio
async def test_process_trouble_App_crash(): # at start
    hr=HrClient("u1","test_server.BugInit")
    try:
        html = await hr.create("//ddd")
        assert 'division by zero' in html
    finally:
        await HrClient.clean()

@pytest.mark.asyncio
async def test_crashes( ): # no start !
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

    finally:
        await HrClient.clean()

# @pytest.mark.asyncio
# async def test_killing_itself( ):
#     hr=HrClient("ut2","examples.simple.App")

#     htm=await hr.create("//js") # will create fifo/process
#     htm=await hr.create("//js") # will reuse fifo and reuse process
#     await hr.exit()
#     with pytest.raises(Exception):
#         await hr.exit()

@pytest.mark.asyncio
async def test_killing_server( ):
    try:
        hr=HrClient("ut1","examples.simple.App")
        htm=await hr.create("//js") # will create fifo/process
        htm=await hr.create("//js") # will reuse fifo and reuse process
        htm=await hr.create("//js") # will reuse fifo and reuse process

        hr=HrClient("ut2","examples.simple.App")
        htm=await hr.create("//js") # will create fifo/process
    finally:
        await HrClient.clean()


@pytest.mark.asyncio
async def test_ok( ):
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



@pytest.mark.asyncio
async def test_timeout_interaction0( ):
    # test the interaction in 0s, with a timeout_interaction=1s
    uid,fqn ="u2","test_server.AppBlockInteraction"
    try:
        p=HrClient(uid,fqn,timeout_interaction=1)
        html=await p.create("//js",init=([0],{}))
        assert html.startswith("<!DOCTYPE html><html>")

        id=re.findall( r'id="(\d+)"',html )[-1]
        datas={"id":int(id),"method":"__on__","args":["onclick-"+id],"kargs":{},"event":{}}
        actions=await p.interact(**datas)
        assert "update" in actions
    finally:
        await HrClient.clean()

@pytest.mark.asyncio
async def test_timeout_interaction3( ):
    # test the interaction in 3s, with a timeout_interaction=1s
    uid,fqn ="u2","test_server.AppBlockInteraction"
    try:
        p=HrClient(uid,fqn,timeout_interaction=1)
        html=await p.create("//js",init=([3],{}))
        assert html.startswith("<!DOCTYPE html><html>")

        id=re.findall( r'id="(\d+)"',html )[-1]
        datas={"id":int(id),"method":"__on__","args":["onclick-"+id],"kargs":{},"event":{}}
        actions=await p.interact(**datas)
        assert actions=={}  # process is killed
    finally:
        await HrClient.clean()



@pytest.mark.asyncio
async def test_timeout_interaction_long( ):
    uid,fqn ="u2","test_server.AppBlockInteraction"
    try:
        p=HrClient(uid,fqn,timeout_interaction=1)
        html=await p.create("//js",init=([-1],{}))
        assert html.startswith("<!DOCTYPE html><html>")

        id=re.findall( r'id="(\d+)"',html )[-1]
        datas={"id":int(id),"method":"__on__","args":["onclick-"+id],"kargs":{},"event":{}}
        actions=await p.interact(**datas)
        assert actions=={}  # process is killed
    finally:
        await HrClient.clean()



@pytest.mark.asyncio
async def test_timeout_inactivity( ):
    try:
        hr=HrClient("ut2","examples.simple.App",timeout_inactivity=1)

        htm=await hr.create("//js") # will create fifo/process

        await asyncio.sleep(2.5)  # Increased timeout to allow process to terminate

        assert not hr._fifo.exists() # fifo is dead

        id="12156456465456413"
        datas={"id":int(id),"method":"__on__","args":["onclick-"+id],"kargs":{},"event":{}}
        with pytest.raises(Exception): # App ut~t2.examples.simple.App is NOT RUNNING ! (can't interact)
            await hr.interact(**datas)

    finally:
        await HrClient.clean()


