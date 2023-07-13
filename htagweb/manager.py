# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################
import asyncio
import logging,pickle

logger = logging.getLogger(__name__)

async def manager_server(reader, writer):
    try:
        from htagweb.uidprocess import Users
    except ImportError:
        from uidprocess import Users

    def ht_create(uid, fqn,js,init_params=None,renew=False): # -> str
        p=Users.use(uid)    # create a user if needed
        html = p.ht_create(fqn,js,init_params=init_params,renew=renew)
        return html
    def ht_interact(uid, fqn,data): # -> dict
        p=Users.use(uid)    # create a user if needed
        actions = p.ht_interact(fqn,data)
        if isinstance(actions,dict):
            return actions
        else:
            return ""   # code for dead session js/side
    def ping(msg):
        return f"hello {msg}"
    def killall():
        Users.killall()
        return True
    def all():
        return Users.all()

    methods=locals()

    question = await reader.read()

    logger.debug("Received from %s, size: %s",writer.get_extra_info('peername'),len(question))

    try:
        name,a,k = pickle.loads(question)
        method = methods[name]
        logger.debug("Call self.%s(...)", name)
        if asyncio.iscoroutinefunction(method):
            reponse = await method(*a,**k)
        else:
            reponse = method(*a,**k)
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


class Manager:
    def __init__(self,port=17788):
        self.port=port
        self._srv=None

    def is_server(self):
        return self._srv!=None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    async def start(self):
        """ start server part """
        if self._srv==None:
            try:
                self._srv = await asyncio.start_server( manager_server, '127.0.0.1', self.port)
                return True
            except:
                self._srv=None
                return False
        else:
            raise Exception("Already started")
            
    async def stop(self):
        if self._srv:
            try:
                await self.killall()
            except:
                pass
            await asyncio.sleep(0.1)
            self._srv.close()
            await self._srv.wait_closed()
            self._srv=None

    def __getattr__(self,name:str):
        async def _(*a,**k):
            reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
            question = pickle.dumps( (name,a,k) )
            # logger.debug('Sending data of size: %s',len(question))
            writer.write(question)
            await writer.drain()
            writer.write_eof()
            data = await reader.read()
            # logger.debug('recept data of size: %s',len(data))
            reponse = pickle.loads( data )
            if isinstance(reponse,Exception):
                raise reponse
            writer.close()
            await writer.wait_closed()
            return reponse
        return _


if __name__=="__main__":
    async def main():
        async with Manager() as m:
            x=await m.ping("bob")
            print(x)
    asyncio.run( main() )
