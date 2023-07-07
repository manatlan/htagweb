# -*- coding: utf-8 -*-
# #############################################################################
# Copyright (C) 2023 manatlan manatlan[at]gmail(dot)com
#
# MIT licence
#
# https://github.com/manatlan/htag
# #############################################################################
import asyncio,sys,threading
import multiprocessing
import queue
import logging,importlib
import traceback,os
import ast
from htag.render import HRenderer
from starlette.requests import Request
from starlette.responses import Response

logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.INFO)

logger = logging.getLogger(__name__)


async def async_exec(stmts, env=None):
    parsed_stmts = ast.parse(stmts)

    fn_name = "_async_exec_f"

    fn = f"async def {fn_name}(): pass"
    parsed_fn = ast.parse(fn)

    for node in parsed_stmts.body:
        ast.increment_lineno(node)

    parsed_fn.body[0].body = parsed_stmts.body
    exec(compile(parsed_fn, filename="<ast>", mode="exec"), env)

    return await eval(f"{fn_name}()", env)


def uidprocess(uid,queues, timeout = 10*60):
    session={}
    hts={}
    qin,qout = queues

    #==========================================================
    async def ping(msg):
    #==========================================================
        return f"hello {msg}"

    #==========================================================
    async def exec(request:Request) -> Response:
    #==========================================================
        """ 'pye' feature, execute a pye/bottle python file in async/starlette context which mimics bottle requests"""

        if isinstance(request,str): # TU ONLY
            filename = "*string*"
            filecontent=request
            request=Request(dict(type="http",path=filename,headers={},method="GET"))
        else:
            filename = str(request.url)
            filecontent=open(filename).read()


        class MyResponse:
            status_code=200
            content=None
            headers={}
            content_type="text/html"

            _set_cookies=[]
            def set_cookie(self,*a,**k):
                self._set_cookies.append( (a,k) )
            _delete_cookies=[]
            def delete_cookie(self,*a,**k):
                self._delete_cookies.append( (a,k) )

        class Web: pass

        web=Web()
        web.request  = request
        web.response = MyResponse()
        try:
            if hasattr(web.request,"session"):
                web.request.session = session
        except AssertionError:
            logger.warn("Can't attach session (A SessionMiddleware must be installed to access request.session)")

        scope=dict(globals())
        scope.update({
            "__file__": filename,
            "__name__": "__main__",
            "web": web,
        })

        class StdoutProxy:
            def __init__(self):
                self.buf=[]
            def flush(self,*a):
                pass
            def write(self, text):
                self.buf.append(text)
                return len(text) # do nothing
            @property
            def content(self):
                return "".join( sys.stdout.buf )

        try:
            sys.stdout = StdoutProxy()
            await async_exec(filecontent,scope)
        finally:
            content=sys.stdout.content
            sys.stdout = sys.__stdout__

        r=Response( web.response.content or content, web.response.status_code, web.response.headers, web.response.content_type)
        for a,k in web.response._set_cookies:
            r.set_cookie(*a,**k)
        for a,k in web.response._delete_cookies:
            r.delete_cookie(*a,**k)
        return r

    #==========================================================
    async def ht_create(fqn,js,init_params=None,renew=False):        # -> str
    #==========================================================
        if init_params is None : init_params=((),{})

        #--------------------------- fqn -> module, name
        names = fqn.split(".")
        modulename,name=".".join(names[:-1]), names[-1]
        module=importlib.import_module(modulename)
        #---------------------------
        htClass = getattr(module,name)

        hr=hts.get(fqn)
        if renew or (hr is None) or str(init_params)!=str(hr.init):
            ##HRenderer(tagClass: type, js:str, exit_callback:Optional[Callable]=None, init= ((),{}), fullerror=False, statics=[], session=None ):
            hr=HRenderer( htClass,
                    js=js,
                    session=session,
                    init= init_params,
            )
            hts[fqn] = hr
        return str(hr)


    #==========================================================
    async def ht_interact(fqn,data): # -> dict
    #==========================================================
        hr=hts[fqn]

        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\ to simplify ut
        if data["id"]=="ut":
            data["id"] = id(hr.tag) #only main tag ;-(
        #/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

        return await hr.interact(data['id'],data['method'],data['args'],data['kargs'],data.get('event') )


    methods=locals()

    async def processloop():
        #process loop
        while 1:
            #TODO: here timeout on inactivity
            try:
                action,(a,k) = qin.get(timeout=timeout)
            except queue.Empty:
                logger.info("Process %s: inactivity timeout (%ssec)",uid,timeout)
                break

            if action=="quit":
                break
            else:
                try:
                    method=methods[action]
                    logger.info("Process %s: %s",uid,action)
                    r=await method(*a,**k)

                    qout.put( dict(result=r) )
                except Exception as e:
                    logger.error("Process %s: ERROR '%s'",uid,e)
                    qout.put( dict(error=traceback.format_exc(),exception=e) )


    asyncio.run( processloop() )
    logger.info("Process %s: ended",uid)


class UidProxyException(Exception): pass
class UidProxy:
    PP={}

    def __init__(self,uid, timeout = 10*60 ):
        reuse=uid in UidProxy.PP
        if reuse:
            p,qin,qout=UidProxy.PP[uid]
            reuse = p.is_alive()

        if reuse:
            logger.info("UidProxy: reuse process %s",uid)
        else:
            logger.info("UidProxy: start process %s",uid)
            qin=multiprocessing.Queue()
            qout=multiprocessing.Queue()

            p=multiprocessing.Process( target=uidprocess, args=(uid, (qin,qout), timeout), name=f"process {uid}" )
            #~ p=threading.Thread( target=uidprocess, args=(uid, (qin,qout)), name=f"process {uid}" )
            p.start()
            UidProxy.PP[uid]=p,qin,qout

        self.qin=qin
        self.qout=qout
        self.uid=uid

    def quit(self):
        """ quit process of this uid """
        self.qin.put( ('quit',( (),{} )) )
        if self.uid in UidProxy.PP:
            del UidProxy.PP[self.uid]

    @classmethod
    def shutdown(cls):
        """ terminate all UidProxy' process"""
        for uid in list(cls.PP.keys()):
            UidProxy(uid).quit()

    #~ async def _com(self,action,*a,**k):
        #~ logger.info(">> UidProxy: com %s(%s,%s)",action,a,k)
        #~ self.qin.put( (action,(a,k)) )
        #~ t1=time.time()
        #~ while (time.time() - t1)<30:    #30s to process
            #~ try:
                #~ x:dict=self.qout.get_nowait()
                #~ if "error" in x:
                    #~ raise UidProxyException(f"unknown UidProxy action {action} : {x['error']}")
                #~ else:
                    #~ r=x["result"]
                    #~ logger.info("<< UidProxy: com %s << %s",action,hasattr(r,"__len__") and len(r) or r)
                    #~ return r
            #~ except queue.Empty:
                #~ await asyncio.sleep(0.1)

    def _com(self,action,*a,**k):
        """ SYNC COM ! """
        logger.info(">> UidProxy: com %s(%s,%s)",action,a,k)
        self.qin.put( (action,(a,k)) )
        x:dict=self.qout.get(timeout=30)
        if "error" in x:
            raise UidProxyException(f"unknown UidProxy action {action} : {x['error']}")
        else:
            r=x["result"]
            logger.info("<< UidProxy: com %s << %s",action,hasattr(r,"__len__") and len(r) or r)
            return r

    def __getattr__(self,action:str):
        async def _(*a,**k):
            x=self._com( action, *a,**k )
            return x
        return _


#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\


#~ async def main():


    #~ p1=UidProxy("u1")
    #~ try:
        #~ fakefile = lambda f: os.path.isfile(f) and Request(dict(method="GET",type="http",path=f,headers={}))

        #~ x=await p1.exec( fakefile("../pscom_api.py") )
        #~ print(x.status_code, x.body)

    #~ finally: # needed if exception in try/catch --> we shutdown all process
        #~ UidProxy.shutdown()

#~ if __name__=="__main__":
    #~ asyncio.run( main() )
