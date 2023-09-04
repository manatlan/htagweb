import pytest,asyncio
import logging

from htagweb import ServeUnique

class SessionMemory:
    def __init__(self):
        self.SESSIONS={}
    def get(self,uid:str):
        return self.SESSIONS.get(uid,{})
    def set(self,uid:str,value:dict):
        assert isinstance(value,dict)
        self.SESSIONS[uid]=value

class BuggedObject:
    def testko(self):
        return 42/0 # runtime error ;-)
    def testok(self):
        return 42

class ObjectTest:
    async def test(self):
        await asyncio.sleep(0.1)
        return 42
    def testsize(self,buf):
        return buf

def f(klass,port):
    async def loop():
        async with ServeUnique( klass, port=port ) as m:
            assert not m.is_server()

            d=await m.get("uid")
            d["nb"]+=1
            await m.set("uid",d)

    asyncio.run(loop())

@pytest.mark.asyncio
async def test_manual_start_stop():
    m=ServeUnique( SessionMemory, port=19999 )
    print(m)
    assert not m.is_server()

    # ensure it doesn't work when m is not started
    with pytest.raises(ConnectionRefusedError):
        await m.get("uid1")

    # ensure it works with start/stop
    try:
        await m.start()
        with pytest.raises(Exception): # you can't multiple start ;-)
            await m.start()
        assert m.is_server()
        assert await m.get("uid1") == {}
        await m.set("uid1", dict(a=42))
        assert await m.get("uid1") == dict(a=42)
    finally:
        await m.stop()
        await m.stop()  # you can multiple stop ;-)

    assert not m.is_server()    # and it's closed

@pytest.mark.asyncio
async def test_classical_use():
    # ensure the classic use works
    async with ServeUnique( SessionMemory, port=19999 ) as m:
        assert m.is_server()
        print(m)
        assert await m.get("uid1") == {}
        await m.set("uid1", dict(a=42))
        assert await m.get("uid1") == dict(a=42)

    assert not m.is_server()    # and it's closed

    async with ServeUnique( SessionMemory, port=21213 ) as m:
        assert {} == await m.get("uid") # previous was closed, so new one

@pytest.mark.asyncio
async def test_exception_are_well_managed():
    # ensure exception are well managed
    async with ServeUnique( BuggedObject, port=19999 ) as m:
        with pytest.raises(ZeroDivisionError):
            await m.testko()

        # it works after crash
        assert 42==await m.testok()

@pytest.mark.asyncio
async def test_async_methods_on_object():
    # ensure object can have async methods
    async with ServeUnique( ObjectTest, port=19999 ) as m:
        assert 42==await m.test()
        buf=500_000*"x"
        assert buf==await m.testsize(buf)    # work better than redys

@pytest.mark.asyncio
async def test_compatibility_in_inner_thread():
    # ensure is compatible in same thread
    async with ServeUnique( SessionMemory, port=21213 ) as m:
        assert m.is_server()
        await m.set("uid",dict(nb=0))

        async with ServeUnique( SessionMemory, port=21213 ) as m2:
            assert not m2.is_server()   # m is not the real server
            d=await m2.get("uid")
            d["nb"]+=1
            await m2.set("uid",d)

        assert {"nb":1} == await m.get("uid")

@pytest.mark.asyncio
async def test_compatibility_in_multiprocessing():
    # ensure is compatible in different process
    import multiprocessing
    async with ServeUnique( SessionMemory, port=21213 ) as m:
        assert m.is_server()
        await m.set("uid",dict(nb=0))

        p=multiprocessing.Process(target=f,args=(SessionMemory,21213,))
        p.start()
        while p.is_alive():
            await asyncio.sleep(0.1)

        assert {"nb":1} == await m.get("uid")

if __name__=="__main__":
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    asyncio.run( test_manual_start_stop() )
    asyncio.run( test_classical_use() )
    asyncio.run( test_exception_are_well_managed() )
    asyncio.run( test_async_methods_on_object() )
    asyncio.run( test_compatibility_in_inner_thread() )
    asyncio.run( test_compatibility_in_multiprocessing() )
