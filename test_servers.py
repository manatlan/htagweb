import pytest
from htag import Tag
from htagweb import findfqn,WebServer,WebServerWS
import htagweb
import sys,json
from starlette.testclient import TestClient

class MyTag(Tag.div): pass
class App(Tag.body):
    def init(self,p="nobody"):
        self.b=Tag.Button("say hello",_onclick=self.bind.doit() )

        self+=(f"hello {p}")
        self+=self.b
    def doit(self):
        self+="hello"


class Nimp: pass

def test_fqn():
    with pytest.raises( Exception ):
        findfqn(42)

    with pytest.raises( Exception ):
        findfqn("mod_name")

    with pytest.raises( Exception ):
        findfqn(Nimp)

    with pytest.raises( Exception ):
        findfqn(sys)

    assert findfqn("mod.name") == "mod.name"
    assert findfqn(MyTag) in ["__main__.MyTag","test_servers.MyTag"]
    assert findfqn(sys.modules[__name__]) in ["__main__.App","test_servers.App"]

@pytest.fixture( params=["wh_solo","wh_served","ws_solo","ws_served"] )
def app(request):
    if request.param=="wh_solo":
        return WebServer( App )

    elif request.param=="ws_solo":
        return WebServerWS( App )

    elif request.param=="wh_served":
        app=WebServer()
        async def handlePath(request):
            return await request.app.serve(request, App)
        app.add_route("/", handlePath )
        return app

    elif request.param=="ws_served":
        app=WebServerWS()
        async def handlePath(request):
            return await request.app.serve(request, App)
        app.add_route("/", handlePath )
        return app

def test_app_webserver_basic(app):

    htagweb.MANAGER = htagweb.Manager()

    try:
        client=TestClient(app)

        response = client.get('/')
        assert response.status_code == 200
        assert "hello nobody" in response.text

        response = client.get('/?p=world')
        assert response.status_code == 200
        assert "hello world" in response.text

        response = client.get('/?kiki')
        assert response.status_code == 200
        assert "hello kiki" in response.text

        fqn=findfqn( App )
        msg=dict(id="ut",method="doit",args=(),kargs={})
        if isinstance( app, WebServer):
            response = client.post("/"+fqn,json=msg)
            assert response.status_code == 200
            assert "update" in response.json()
        else:
            with client.websocket_connect('/ws?fqn='+fqn) as websocket:
                websocket.send_text( json.dumps(msg) )
                data = websocket.receive_text()
                assert "update" in json.loads(data)
    finally:
        htagweb.MANAGER.shutdown()

#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
from starlette.responses import HTMLResponse

class SesApp(Tag.body):
    def init(self,p="nobody"):
        self.b=Tag.Button("say hello",_onclick=self.bind.doit() )
        self+=self.b+Tag.cpt( self.session["cpt"] )
    def doit(self):
        self.session["cpt"]+=1

@pytest.fixture
def appses():
    app=WebServer()
    async def handlePath(request):
        return await request.app.serve(request, SesApp)
    async def getcpt(request):
        return HTMLResponse( f"{request.session['cpt']}" )
    async def resetcpt(request):
        request.session["cpt"]=0
        return HTMLResponse( "ok" )
    async def inccpt(request):
        request.session["cpt"]+=1
        return HTMLResponse( "ok" )
    async def ping(request):
        return HTMLResponse( "pong" )

    app.add_route("/", handlePath )
    app.add_route("/ping", ping )
    app.add_route("/cpt",  getcpt)
    app.add_route("/reset",  resetcpt)
    app.add_route("/inc",  inccpt)
    return app

def test_session_http_before( appses ): # the main goal

    htagweb.MANAGER = htagweb.Manager()

    try:
        client=TestClient(appses)

        # create a first exchange, to get the unique uid
        response = client.get('/ping')
        assert response.status_code == 200
        assert response.text == "pong"

        # get the unique uid in session
        keys=list(htagweb.MANAGER.SESSIONS.keys())
        assert len(keys)==1
        uid=keys[0]

        # set a var in session
        ses=htagweb.MANAGER.SESSIONS[uid]
        ses["cpt"]="X"

        # assert this var is visible from an api
        response = client.get('/cpt')
        assert response.status_code == 200
        assert response.text == "X"

    finally:
        htagweb.MANAGER.shutdown()



def test_session_http_after( appses ): # the main goal

    htagweb.MANAGER = htagweb.Manager()

    try:
        client=TestClient(appses)

        # create a first exchange, to get the unique uid
        response = client.get('/ping')
        assert response.status_code == 200
        assert response.text == "pong"

        # get the unique uid in session
        keys=list(htagweb.MANAGER.SESSIONS.keys())
        assert len(keys)==1
        uid=keys[0]

        # assert the var is not present in session
        assert "cpt" not in htagweb.MANAGER.SESSIONS[uid]

        # request the api which init the var
        response = client.get('/reset')
        assert response.status_code == 200

        # assert the var is init
        assert htagweb.MANAGER.SESSIONS[uid]["cpt"]==0

    finally:
        htagweb.MANAGER.shutdown()



def test_session_htag_before( appses ): # the main goal

    htagweb.MANAGER = htagweb.Manager()

    try:
        client=TestClient(appses)

        # create a first exchange, to get the unique uid
        response = client.get('/ping')
        assert response.status_code == 200
        assert response.text == "pong"

        # get the unique uid in session
        keys=list(htagweb.MANAGER.SESSIONS.keys())
        assert len(keys)==1
        uid=keys[0]

        # set a var in session
        htagweb.MANAGER.SESSIONS[uid]["cpt"]=42

        # assert this var is visible from an htag
        response = client.get('/')
        assert response.status_code == 200
        assert ">42</cpt>" in response.text


        # and assert the interaction inc it
        fqn=findfqn( SesApp )
        msg=dict(id="ut",method="doit",args=(),kargs={})
        response = client.post("/"+fqn,json=msg)
        assert response.status_code == 200

        assert htagweb.MANAGER.SESSIONS[uid]["cpt"]==43

    finally:
        htagweb.MANAGER.shutdown()

#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\


if __name__=="__main__":
    test_fqn()
    # test_session_base()
    # test_app_webserver_basic()
    # test_session_basic( appses() )
    # test_session_base( appses() )