import pytest,asyncio,sys
from htagweb.session import Session,FileDict,FilePersistentDict,ShmDict


def session_test(factory):
    session = factory("uid")
    try:
        # good way to clone
        dict(session.items())

        assert "nb" not in session

        session["nb"]=session.get("nb",0) + 1

        assert "nb" in session
        assert session
        assert len(session)==1


        # ensure persistance is present
        session = factory("uid")
        assert session["nb"]==1

        session["x"]=42

        assert len(session)==2

        del session["x"]
        assert len(session)==1
        session.clear()
        assert len(session)==0

        session = factory("uid")
        assert len(session.items())==0

        session["k"]=42
        assert session.pop("k",12)==42
        assert session.pop("k",12)==12

    finally:
        session.clear()

def test_sessions_file():
    session_test( Session )

def test_sessions_file():
    session_test( FileDict )

def test_sessions_filepersitent():
    session_test( FilePersistentDict )

def test_sessions_ShmDict():
    session_test( ShmDict )



if __name__=="__main__":
    import logging,multiprocessing,threading
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    # asyncio.run( test_sessions_basics() )