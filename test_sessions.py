import pytest,asyncio,sys
from htagweb.sessions import FileDict,FilePersistentDict,MemDict
from test_server import server


def session_test(factory):
    session = factory("uid")
    try:
        # bad way to clone
        with pytest.raises(Exception):
            dict(session)

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

    finally:
        session.clear()

@pytest.mark.asyncio
async def test_sessions_mem( server ):  # need redys.v2 runned
    session_test( MemDict )

def test_sessions_file():
    session_test( FileDict )

@pytest.mark.asyncio
def test_sessions_filepersitent():
    session_test( FilePersistentDict )



if __name__=="__main__":
    import logging,multiprocessing,threading
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    # asyncio.run( test_sessions_basics() )