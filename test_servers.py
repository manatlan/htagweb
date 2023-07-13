import pytest,asyncio
from htag import Tag
from htagweb import findfqn,WebServer,WebServerWS,Users
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

class User: # helper
    def __init__(self,client,uid):
        self._client=client
        self.uid=uid
    def get(self,path):
        return self._client.get(path,headers={"cookie":"session=%s" % self.uid})
    def post(self,path,dico):
        return self._client.post(path,headers={"cookie":"session=%s" % self.uid},json=dico)
    @property
    def session(self):
        return Users.get(self.uid).session


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

def test_basics_webserver_and_webserverws(app):
    with TestClient(app) as client:
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

#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
# new way
#/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\

from starlette.responses import HTMLResponse,JSONResponse

@pytest.fixture
def appses():
    app=WebServer()
    async def handlePath(request):
        return await request.app.serve(request, "test_hr.App")
    async def set(request):
        for k,v in request.query_params.items():
            request.session[k]=v
        return HTMLResponse( "ok" )
    async def info(request):
        d=dict(uid=request['uid'],session=dict(request['session']))
        return JSONResponse( d )

    app.add_route("/", handlePath )
    app.add_route("/set",  set)
    app.add_route("/info",  info)

    return app

def test_users_sessions( appses ):
    with TestClient(appses) as client:
        U1=User(client,"user1")
        U2=User(client,"user2")

        info= U1.get("/info").json()
        assert info["uid"]==U1.uid
        assert info["session"]=={}

        info= U2.get("/info").json()
        assert info["uid"]==U2.uid
        assert info["session"]=={}

        #####################################################
        ## CHANGE SESSION BEFORE REQUEST
        #####################################################
        U2.session["cpt"]="X"

        info= U2.get("/info").json()
        assert info["session"]["cpt"]=="X"

        #####################################################
        ## CHANGE SESSION AFTER REQUEST
        #####################################################
        U2.get("/set?cpt=Y")

        # the real session is modified        
        assert U2.session["cpt"]=="Y"

        # verify on http too
        info= U2.get("/info?2").json()
        assert info["session"]["cpt"] == "Y"


        #####################################################
        ## CHANGE SESSION BEFORE HTAG APP
        #####################################################
        U2.get("/set?cpt=42")

        # the real session is modified        
        assert U2.session["cpt"]=="42"

        # assert this var is visible from an htag
        response = U2.get('/')
        assert response.status_code == 200
        assert ">42</cpt>" in response.text

        # and assert the interaction inc it
        fqn="test_hr.App"
        dico=dict(id="ut",method="doit",args=(),kargs={})
        response = U2.post("/"+fqn, dico)
        assert response.status_code == 200

        # the real session is modified        
        assert U2.session["cpt"]==43

        # verify on http too
        info= U2.get("/info?2").json()
        assert info["session"]["cpt"] == 43


        #####################################################
        # stupid test
        #####################################################
        # ensure u1 session is not modified
        info= U1.get("/info").json()
        assert info["session"]=={}


def test_bad_htag( appses ):

    with TestClient(appses) as client:
        U1=User(client,"user1")

        # try to post an interaction on an non instancied htag app
        fqn="test_hr.App"
        dico=dict(id="ut",method="doit",args=(),kargs={})
        response = U1.post("/"+fqn, dico)
        assert response.status_code == 200
        assert response.text == ""

def test_ensure_uid_is_created_on_1st_http( appses ):

    with TestClient(appses) as client:
        x=client.get("/info")
        uid = x.json()['uid']

        assert Users.get(uid).session == {}
        assert uid in str(x.cookies)


if __name__=="__main__":
    test_fqn()
