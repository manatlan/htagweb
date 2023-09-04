# -*- coding: utf-8 -*-
import asyncio,sys
import logging,pickle
from typing import Callable
logger = logging.getLogger(__name__)

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

class TestObject:
    async def test(self):
        await asyncio.sleep(0.1)
        return 42
    def testsize(self,buf):
        return buf

class ServeUnique:
    """ create a task, in current loop, to run a unique server (ip:port) which
        will expose methods of 'klass' in self (so exposed methods are async!).
        
        Concept:
        - as it's a tcp server, unicity is guaranted
        - each instance can act as a client, and only one is the real server
        
        (Ensure unicity of the instance in multi process context ... RPC)
    """
    def __init__(self,klass:Callable,host:str="127.0.0.1",port:int=17788):
        self._klass=klass
        self._host=host
        self._port=int(port)
        self._task=None

    def is_server(self):
        return self._task!=None

    async def start(self):
        """ start server part """
        if self._task==None:

            ###########################################################################
            instance = self._klass()

            ###########################################################################
            async def serve(reader, writer):
                
                question = await reader.read()

                logger.debug("Received from %s, size: %s",writer.get_extra_info('peername'),len(question))

                trunc = lambda x,limit=100: str(x)[:limit-3]+"..." if len(str(x))>limit else str(x)
                fmt=lambda a,k: f"""{trunc(a)[1:-1]}{','.join([f"{k}={trunc(v)}" for k,v in k.items()])}"""
                try:
                    reponse=None
                    name,a,k = pickle.loads(question)
                    if name=="STOP":
                        logger.debug(">>> STOP")
                    else:
                        method = getattr(instance, name)
                        logger.debug(">>> %s.%s( %s )", instance.__class__.__name__,name, fmt(a,k))
                        if asyncio.iscoroutinefunction(method):
                            reponse = await method(*a,**k)
                        else:
                            reponse = method(*a,**k)
                    logger.debug("<<< %s", trunc(reponse))
                except Exception as e:
                    logger.error("Error calling %s(...) : %s" % (name,e))
                    reponse=e

                data=pickle.dumps(reponse)
                logger.debug("Send size: %s",len(data))
                writer.write(data)
                await writer.drain()
                writer.write_eof()

                writer.close()
                await writer.wait_closed()
            
            ###########################################################################
            try:
                self._server = asyncio.start_server( serve, self._host, self._port)
                self._task=await asyncio.create_task( self._server )
                logger.info("ServeUnique: instance of %s on %s:%s",instance.__class__,self._host,self._port)
                return True
            except Exception as e:
                del instance
                self._task=None
                return False
        else:
            raise Exception("Already started")

    async def stop(self):
        if self._task:
            try:
                await self.STOP()   # private method
            except:
                pass
            self._task.close()
            await self._task.wait_closed()
            self._task=None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    def __getattr__(self,name:str):
        async def _(*a,**k):
            reader, writer = await asyncio.open_connection(self._host,self._port)
            question = pickle.dumps( (name,a,k) )
            # logger.debug('Sending data of size: %s',len(question))
            writer.write(question)
            await writer.drain()
            writer.write_eof()
            data = await reader.read()
            # logger.debug('recept data of size: %s',len(data))
            reponse = pickle.loads( data )
            writer.close()
            await writer.wait_closed()
            if isinstance(reponse,Exception):
                raise reponse
            else:
                return reponse
        return _

    def __repr__(self):
        return f"<ServeUnique '{self._klass}()' on {self._host}:{self._port} ({self.is_server() and 'server' or 'client|notStarted'})>"

def f(klass,port):
    async def loop():
        async with ServeUnique( klass, port=port ) as m:
            assert not m.is_server()
            
            d=await m.get("uid")
            d["nb"]+=1
            await m.set("uid",d)
        
    asyncio.run(loop()) 


if __name__=="__main__":
    import pytest
    import logging
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)
    
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
            
    async def test_exception_are_well_managed():
        # ensure exception are well managed
        async with ServeUnique( BuggedObject, port=19999 ) as m:
            with pytest.raises(ZeroDivisionError):
                await m.testko()
                
            # it works after crash
            assert 42==await m.testok()

    async def test_async_methods_on_object():
        # ensure object can have async methods
        async with ServeUnique( TestObject, port=19999 ) as m:
            assert 42==await m.test()
            buf=500_000*"x"
            assert buf==await m.testsize(buf)    # work better than redys

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
            
           
    asyncio.run( test_manual_start_stop() )
    asyncio.run( test_classical_use() )
    asyncio.run( test_exception_are_well_managed() )
    asyncio.run( test_async_methods_on_object() )
    asyncio.run( test_compatibility_in_inner_thread() )
    asyncio.run( test_compatibility_in_multiprocessing() )
