# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htagweb
# #############################################################################

import asyncio,sys
import logging,pickle
from typing import Callable

logger = logging.getLogger(__name__)

class ServeUnique: #TODO: rename to ProxyServerSingleton
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

if __name__=="__main__":

    class SessionMemory:
        def __init__(self):
            self.SESSIONS={}
        def get(self,uid:str):
            return self.SESSIONS.get(uid,{})
        def set(self,uid:str,value:dict):
            assert isinstance(value,dict)
            self.SESSIONS[uid]=value

    async def test():
        async with ServeUnique( SessionMemory, port=19999 ) as m:
            assert m.is_server()
            print(m)
            assert await m.get("uid1") == {}
            await m.set("uid1", dict(a=42))
            assert await m.get("uid1") == dict(a=42)

        assert not m.is_server()

    asyncio.run( test() )