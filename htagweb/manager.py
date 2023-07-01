# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################

import asyncio
import logging
import pickle,os,sys,time,hashlib
from htag.render import HRenderer
from multiprocessing import Queue,Process
from queue import Empty
from datetime import datetime
import importlib


from . import shm

logger = logging.getLogger(__name__)


def log(*a):
    print(*a,flush=True)

def _processHRenderer(uid:str,smd:dict,fqn:str,init_params,js:str,queues):
    pid=os.getpid()
    log(f"Process {pid} for {uid} : {fqn}:{init_params} Started !")
    qin,qout = queues
    try:
        #--------------------------- fqn -> module, name
        names = fqn.split(".")
        modulename,name=".".join(names[:-1]), names[-1]
        module=importlib.import_module(modulename)
        #---------------------------
        tagClass = getattr(module,name)

        def exit(x=None):
            qin.put("EXIT")

        hr = HRenderer( tagClass, js=js, init=init_params, session=smd, exit_callback=exit)
        qout.put("")
    except Exception as e:
        log(f"Process {pid} ({fqn}:{init_params}) exited --> ERROR {e}!")
        import traceback
        err=traceback.format_exc()
        qout.put(err)
        return

    async def loop():
        RENDU = str(hr)
        while True:
            # attends les ordres d'interactions
            data=qin.get()
            if data=="EXIT":
                break
            elif data=="RENDER":
                tla=time.time()
                qout.put( RENDU )
            elif data:
                tla=time.time()
                actions=await hr.interact( data["id"],data["method"],data["args"],data["kargs"],data.get("event") )

                # retourne les actions resultantes de l'interaction
                qout.put(actions)

                ##################################### redraw hack
                hr.body = str(hr.tag)  #TODO: normal ?
                RENDU = str(hr)
        log(f"Process {pid} for {uid} : {fqn}:{init_params} exited !")

    asyncio.run( loop() )


class AppProcessException(Exception): pass

class AppProcess:
    def __init__(self,uid:str, fqn:str,init_params,js:str,appkey:str):
        if not (isinstance(uid,str) and "." in fqn):
            raise AppProcessException(f"{fqn} is not a full qualified name string")

        self.fqn=fqn
        self.appkey = appkey
        self.qin = Queue()
        self.qout = Queue()


        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
        smd = shm.session(uid)
        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

        ##############################################################
        self.__process = Process(target=_processHRenderer, args=(uid,smd,fqn,init_params,js,(self.qin,self.qout)),name="AppProcess:"+fqn)
        # from threading import Thread
        # self.__process = Thread(target=_processHRenderer, args=(uid,smd,fqn,init_params,js,(self.qin,self.qout)),name="AppProcess:"+fqn)
        ##############################################################
        self.__process.start()

        # wait feedback on starting (from qout)
        feedback=self.qout.get()    #TODO: that's a blocking loop .... use _waitreturn ?!
        if feedback!="":
            raise AppProcessException(feedback)

    def is_alive(self):
        return self.__process.is_alive()

    async def _waitreturn(self):
        """ wait in async style, in process running loop """
        t1=time.time()
        while (time.time() - t1)<30:    #30s to process
            try:
                return self.qout.get_nowait()
            except Empty:
                await asyncio.sleep(0.1)
        raise AppProcessException("Interaction Timeout")

    async def render(self) -> str: # html
        self.qin.put("RENDER")
        return await self._waitreturn()  # make real async in process loop !

    async def interact(self,data) -> dict:
        self.qin.put(data)
        return await self._waitreturn()  # make real async in process loop !

    def quit(self):
        self.qin.put("EXIT")

    def __str__(self):
        return f"<AppProcess {self.__process} 'fqn:{self.fqn}' {self.is_alive()}>"

class User:
    def __init__(self,uid):
        self.uid=uid
        self.__apps={}

    def get_app(self,fqn:str) -> AppProcess: # or None
        return self.__apps.get(fqn)

    def set_app(self,app:AppProcess):
        self.__apps[app.fqn]=app

    @property
    def apps(self):
        for a in self.__apps.values():
            yield a

    def destroy(self):
        for app in self.apps:
            app.quit()

    def __str__(self):
        return f"<User {self.uid} apps:{list(self.__apps.keys())}>"

class Users:
    def __init__(self):
        self.__users={}

    def get_user(self,uid:str) -> User: # or None
        return self.__users.get(uid)

    def register(self,uid:str, app:AppProcess):
        user = self.get_user(uid)
        if not user:
            self.__users[uid]=User(uid)

        user = self.get_user(uid)
        user.set_app(app)

    def destroy(self,uid:str):
        user=self.get_user(uid)
        if user:
            user.destroy()
            del self.__users[uid]

    def __str__(self):
        ll=["USERS:"]
        for uid in self.__users.keys():
            user=self.get_user(uid)
            ll.append(f" * {uid}")
            for app in user.apps:
                ll.append(f"   - {app}")

        return "\n".join(ll)


class Manager:
    """ manager de process hrenderer """
    def __init__(self,port):
        self.users=Users()
        self.port=port

    def seskeeper(self,MAX): #SEC
        WSES=shm.wses()
        users_to_destroy=[]
        now=datetime.now()
        for idx,(uid,lastaccess) in enumerate(WSES.items()):
            idle=(now - lastaccess).seconds
            if idle > MAX:
                users_to_destroy.append(uid)
            user=self.users.get_user(uid)   # if user is None, it's a user which just access /api/ (not runned an htag's App !)
            log(f"{idx+1}/{len(WSES)} SESKEEPER WATCH:",user or uid,"idle:",idle,"/",MAX,(uid in users_to_destroy) and "--> WILL DESTROY" or "")

        for uid in users_to_destroy:
            logger.info("seskeeper: destroy %s",uid)
            # remove the uid session
            smd = shm.session(uid)
            smd.shm.close()
            smd.shm.unlink()

            # delete from globals
            del WSES[uid]

            # delete its apps
            self.users.destroy(uid)

        return users_to_destroy


    def run(self,timeout=20):
        async def handle_server(reader, writer):

            question = await reader.read()
            logger.debug("Received from %s, size: %s",writer.get_extra_info('peername'),len(question))

            try:
                name,a,k = pickle.loads(question)
                method = getattr(self,name)
                logger.debug("Call self.%s(...)", name)
                reponse = await method(*a,**k)
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


        async def loopSesKeeper(max):
            while 1:
                await asyncio.sleep(60) # check sessions every minute
                self.seskeeper(max)


        # https://stackoverflow.com/a/73884759/1284499
        if sys.version_info < (3, 10):
            loop = asyncio.get_event_loop()
        else:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()

            asyncio.set_event_loop(loop)


        try:
            server = loop.run_until_complete( asyncio.start_server( handle_server, '127.0.0.1', self.port) )

            # one server started, so we can tun the sessions keeper
            asyncio.ensure_future( loopSesKeeper(timeout) )

            log('MANAGER SERVER Serving on {}'.format(server.sockets[0].getsockname()))
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        server.close()

    async def ht_render(self, uid:str,fqn:str,init_params,js:str, renew=False) -> str:

        appkey = hashlib.sha1(f"{fqn} {init_params} {js}".encode()).hexdigest()

        user=self.users.get_user(uid)
        if user:
            # il a deja demarrer des process
            app=user.get_app(fqn)
            if app:
                # cet app est deja lance
                if app.appkey == appkey and not renew:

                    if app.is_alive():
                        logger.info(f"User {uid}, same app|init ({fqn}), return html")
                        # elle vit encore
                        # on va juste demande le rendu actuel
                        return await app.render()
                    else:
                        # elle est morte
                        # on relance
                        logger.info(f"User {uid}, same app|init ({fqn}), but process is dead, we restart it")
                else:
                    # ce n'est pas le meme init
                    # on supprime l'ancienne, et on relance avec la nouvelle init
                    logger.info(f"User {uid}, same app ({fqn}), but different init, we kill current, and restart a new one")
                    app.quit()
        else:
            logger.info(f"New user {uid}")

        # on lance l'app demande
        logger.info(f"Start Process for user {uid}, app ({fqn}), with {init_params}")
        app=AppProcess(uid, fqn,init_params,js,appkey)  # start process !
        html=await app.render()
        self.users.register( uid , app)
        return html

    async def ht_interact(self, uid:str,fqn:str, data:dict ) -> dict:
        user=self.users.get_user(uid)
        if user:
            app=user.get_app(fqn)
            if app and app.is_alive():
                logger.info(f"INTERACT for {uid}, app ({fqn}), width {data}")
                return await app.interact( data)

        logger.error(f"CAN'T INTERACT for {uid}, app ({fqn}) is DEAD !!!")

