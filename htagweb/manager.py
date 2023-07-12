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

    def getsession(uid):
        p=Users.use(uid)
        x=p.session
        print("GETSESSION",x)
        return x
    def setsession(uid,session):
        print("SETSESSION",session)
        p=Users.use(uid)
        p.session.clear()
        p.session.update(session)
    def ht_create(uid, fqn,js,init_params=None,renew=False): # -> str
        p=Users.use(uid)
        html = p.ht_create(fqn,js,init_params=init_params,renew=renew)
        return html
    def ht_interact(uid, fqn,data): # -> dict
        p=Users.use(uid)
        actions = p.ht_interact(fqn,data)
        return actions
    def ping(msg):
        return f"hello {msg}"
    def killall():
        Users.kill()
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
        # use tcp server (on port) to be able to have just an unique source of truth
        self._task = asyncio.create_task( asyncio.start_server( manager_server, '127.0.0.1', self.port) )
        asyncio.ensure_future( self._task )

    async def stop(self):
        await self.killall()
        self._task.cancel()

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

    def session(self,uid):
        class sm:
            def __init__(this, uid):
                this.uid=uid

            async def __aenter__(this):
                d = await self.getsession( this.uid )
                this._d=d
                return d

            async def __aexit__(this, *args):
                await self.setsession( this.uid, this._d )

        return sm(uid)


if __name__=="__main__":
    async def main():
        m=Manager()
        await asyncio.sleep(0.1)
        x=await m.ping("bob")
        print(x)
        await m.stop()
    asyncio.run( main() )