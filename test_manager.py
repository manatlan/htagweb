import pytest
import re
import asyncio
from datetime import datetime

from htagweb.manager import Manager,AppProcess,AppProcessException,shm


#=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

from htag import Tag
class Appz(Tag.div):
    def do(self):
        self+= "hello"

class Nimp: pass

class AppKo(Tag.div):
    def init(self):
        self+= 42/0

#=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-


@pytest.mark.asyncio
async def test_AppProcess():

    a=AppProcess("u1","test_manager.Appz",( [], {}),js="/*js*/",appkey="apppkkkk")
    assert a.is_alive()

    # get the html (first render)
    html=await a.render()

    # ensure hello is not here
    assert ">hello<" not in html

    # find the @id of the instance tag
    id=int(re.findall( 'body id="(\d+)"',html )[0])

    # invoke the "do" method
    actions=await a.interact( dict(id=id,method="do",args=[],kargs={}) )

    # ensure an update action
    assert ">hello<" in actions["update"][id]

    # ensure the full redering is good
    assert ">hello<" in await a.render()

    # force quit
    a.quit()

    # and wait before testing is not alive anymore
    await asyncio.sleep(0.1)
    assert not a.is_alive()

    print("test_AppProcess ok")


@pytest.mark.asyncio
async def test_AppProcess_ko():

    # test a class with bug during init process
    app=AppProcess("u1","test_manager.AppKo",( [], {}),js="/*js*/",appkey="apppkkkk")
    # will print the stacktrace on stdout ;-(
    # (exception is bypassed, and render a html error page ;-( )
    # so we need to force quit the process
    app.quit()

    # test unknown fqn
    with pytest.raises( AppProcessException ):
        AppProcess("u1","__NIMP__.NIMP",( [], {}),js="/*js*/",appkey="apppkkkk")

    # test an existing class, but not htag one
    with pytest.raises( AppProcessException ):
        AppProcess("u1","test_manager.Nimp",( [], {}),js="/*js*/",appkey="apppkkkk")



@pytest.mark.asyncio
async def test_manager():
    uid,fqn="u1","test_manager.Appz"
    m=Manager(17777)

    #!!!!!!!!!!!!!!!!!!!!!!!!!!! register request for uid
    scope={}
    scope["uid"] = uid
    scope["session"] = shm.session(uid) # create a smd

    # declare session
    glob=shm.wses()
    glob[uid]=datetime.now()
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!


    h=await m.ht_render(uid,fqn,( [], {}), js="/*js*/")

    u=m.users.get_user(uid)
    app=u.get_app(fqn)
    assert app.is_alive()
    hh=await app.render()

    assert hh==h

    await asyncio.sleep(2)
    m.seskeeper(1) # kill user'sessions older than 1 sec ;-)

    await asyncio.sleep(0.1) # wait a little bit

    # user should be destroyed
    assert not m.users.get_user(uid)
    # and its apps too.
    assert not app.is_alive()



if __name__=="__main__":

    import logging
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    asyncio.run( test_AppProcess() )
    asyncio.run( test_AppProcess_ko() )
    asyncio.run( test_manager() )

    print("ok")

