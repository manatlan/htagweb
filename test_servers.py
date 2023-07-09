import pytest
from htag import Tag
from htagweb import findfqn,WebServer,WebServerWS
import htagweb
import sys
from starlette.testclient import TestClient

class MyTag(Tag.div): pass
class App(Tag.div): pass

class Hello(Tag.div):
    def init(self,p="nobody"):
        self.set(f"hello {p}")

class Nimp: pass

def test_fqn():
    with pytest.raises( Exception ):
        findfqn(42)

    with pytest.raises( Exception ):
        findfqn("mod_name")

    with pytest.raises( Exception ):
        findfqn(Nimp)

    assert findfqn("mod.name") == "mod.name"
    assert findfqn(MyTag) in ["__main__.MyTag","test_servers.MyTag"]
    assert findfqn(sys.modules[__name__]) in ["__main__.App","test_servers.App"]

def test_app_served():

    htagweb.MANAGER = htagweb.Manager()

    try:
        for HTServer in [WebServer,WebServerWS]:
            app=HTServer( Hello )
            client = TestClient(app)

            response = client.get('/')
            assert response.status_code == 200
            assert "hello nobody" in response.text

            response = client.get('/?p=world')
            assert response.status_code == 200
            assert "hello world" in response.text

            response = client.get('/?kiki')
            assert response.status_code == 200
            assert "hello kiki" in response.text
    finally:
        htagweb.MANAGER.shutdown()

def test_app_with_serve():
    htagweb.MANAGER = htagweb.Manager()

    try:
        for HTServer in [WebServer,WebServerWS]:
            app=HTServer()
            async def handlePath(request):
                return await request.app.serve(request, Hello)
            app.add_route("/", handlePath )

            client = TestClient(app)

            response = client.get('/')
            assert response.status_code == 200
            assert "hello nobody" in response.text

            response = client.get('/?p=world')
            assert response.status_code == 200
            assert "hello world" in response.text

            response = client.get('/?kiki')
            assert response.status_code == 200
            assert "hello kiki" in response.text
    finally:
        htagweb.MANAGER.shutdown()

if __name__=="__main__":
    # test_fqn()
    test_app_served()
    # test_app_with_serve()
