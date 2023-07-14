import pytest
import asyncio
from htagweb.uidprocess import UidProcess,Users

def test_bad_interop_unknown_method():
    p1=UidProcess("u1")
    r = p1.unknown(42) # >> error ''unknown''
    assert isinstance(r,Exception)
    p1.quit()

def test_bad_interop_bad_signature():
    p1=UidProcess("u1")
    r=p1.ping() #  missing 1 required positional argument: 'msg''
    assert isinstance(r,Exception)
    p1.quit()


def test_ok_ping():

    p1=UidProcess("u1")
    r=p1.ping("manatlan")
    assert r == "hello manatlan"
    assert "ping" in p1.session
    p1.quit()


def test_htag_ok():

    p1=UidProcess("u1")
    p1.session["cpt"]=42
    try:
        fqn = "test_hr.App"

        x= p1.ht_create(fqn,"//jscom")
        assert isinstance(x,str)
        assert "//jscom" in x
        assert "function action(" in x
        assert ">say hello</Button>" in x
        assert ">42</cpt>" in x
        assert p1.session["created"]
        assert p1.session["cpt"]==42


        data=dict(id="ut",method="doit",args=(),kargs={})
        x=p1.ht_interact(fqn, data)
        assert isinstance(x,dict)
        assert "update" in x
        ll=list(x["update"].items())
        assert len(ll) == 1 # one update
        ido,content = ll[0]
        assert isinstance( ido, int) and ido
        assert isinstance( content, str) and content
        assert "hello" in content

        # assert the cpt var was incremented after interaction
        assert p1.session["cpt"]==43
        assert p1.session["interacted"]

    finally:
        p1.quit()


@pytest.mark.asyncio
async def test_com_after_quit():
    p1=UidProcess("u1",{})
    p1.ping("x")
    p1.quit()

    await asyncio.sleep(0.1)

    r=p1.ping("hello") # UidProxyException(f"queue is closed")
    assert isinstance(r,Exception)



@pytest.mark.asyncio
async def test_com_after_timeout_death():
    p1=UidProcess("ud1",0.5)
    p1.ping("x")

    assert p1.is_alive()

    await asyncio.sleep(1)

    assert not p1.is_alive()

    r = p1.ping("hello") # UidProxyException(f"queue is closed on process side")
    print(r)
    assert isinstance(r,Exception)

    ##assert "ud1" in Users.all()


def test_users():
    try:
        u1=Users.use("us1")
        assert "ping" not in u1.session
        u1.ping("jjj")
        assert "ping" in u1.session

        u2=Users.use("us2")
        assert "ping" not in u2.session
        u2.ping("jjj")
        assert "ping" in u2.session

        assert Users.get("us2")

        assert "us1" in Users.all()
        assert "us2" in Users.all()
    finally:
        Users.killall()

def test_user_get():
    with pytest.raises( KeyError ):
        assert Users.get("fdsfdsds") is None


def test_stress():
    import random
    for i in range(1000):
        ll=[Users.use("ustress%s"%i) for i in range( 1+int(i/100))]
        one=random.choice(ll)

        one.session["cpt"]=78

        x=random.choice([1,2])
        if x==1:
            x=one.ping( one.uid )
            print(i,x)
        else:
            fqn = "test_hr.App"
            x=one.ht_create(fqn,"//jscom")
            assert isinstance(x,str)

            data=dict(id="ut",method="doit",args=(),kargs={})
            x=one.ht_interact(fqn, data)
            assert isinstance(x,dict)
            assert "update" in x
            print(i,x)

    Users.killall()

if __name__=="__main__":
    # asyncio.run( test_bad_interop_unknown_method() )
    # asyncio.run( test_bad_interop_bad_signature() )
    # asyncio.run( test_ok_ping() )
    # asyncio.run( test_htag_ok() )
    # asyncio.run( test_com_after_quit() )
    # asyncio.run( test_com_after_timeout_death() )

    test_stress()
    # asyncio.run( test_users() )
