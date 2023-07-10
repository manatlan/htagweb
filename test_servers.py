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


if __name__=="__main__":
    # test_fqn()
    # test_app_webserver_basic()
    pass
