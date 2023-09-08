import pytest,asyncio
from htagweb.sessions import createFile, createFilePersistent, createShm, createMem

@pytest.fixture( params=["createFile", "createFilePersistent", "createShm"] )
#@pytest.fixture( params=["createFile", "createFilePersistent", "createShm", "createMem"] )
def method_session(request):
   if request.param=="createFile":
        return createFile
   elif request.param=="createFilePersistent":
        return createFilePersistent
   elif request.param=="createShm":
        return createShm
   elif request.param=="createMem":
        return createMem


@pytest.mark.asyncio
async def test_sessions_basics(method_session):

        if method_session == createMem:
            from htagweb.sessions.memory import startServer
            startServer()


        session = await method_session("uid")
        try:
            session["nb"]=session.get("nb",0) + 1

            # ensure persistance is present
            session = await method_session("uid")
            assert session["nb"]==1

            assert len(session.items())>0
            session.clear()

            session = await method_session("uid")
            assert len(session.items())==0

        finally:
            session.clear()


if __name__=="__main__":
    import logging,multiprocessing,threading
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    # asyncio.run( test_sessions_basics() )