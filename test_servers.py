import pytest
from htag import Tag
from htagweb import findfqn,WebServer,WebServerWS
import sys
from starlette.testclient import TestClient

class MyTag(Tag.div): pass
class App(Tag.div): pass

def test_fqn():
    with pytest.raises( Exception ):
        findfqn(42)

    with pytest.raises( Exception ):
        findfqn("mod_name")

    assert findfqn("mod.name") == "mod.name"
    assert findfqn(MyTag) in ["__main__.MyTag","test_servers.MyTag"]
    assert findfqn(sys.modules[__name__]) in ["__main__.App","test_servers.App"]

def test_app_served():
    class Hello(Tag.div):
        def init(self,p="nobody"):
            self.set(f"hello {p}")

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

def test_app_with_serve():
    class Hello(Tag.div):
        def init(self,p="nobody"):
            self.set(f"hello {p}")

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

if __name__=="__main__":
    test_fqn()
    test_app_served()
    test_app_with_serve()
