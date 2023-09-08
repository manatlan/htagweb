import pytest,asyncio
from htagweb.sessions import createFile, createFilePersistent, createShm, createMem

@pytest.mark.asyncio
async def test_sessions_basics():
    for method in [createFile, createFilePersistent, createShm, createMem ]:

        session = await method("uid")
        try:
            session["nb"]=session.get("nb",0) + 1

            # ensure persistance is present
            session = await method("uid")
            assert session["nb"]==1

            assert len(session.items())>0
            session.clear()

            session = await method("uid")
            assert len(session.items())==0

        finally:
            session.clear()


if __name__=="__main__":
    import logging,multiprocessing,threading
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    asyncio.run( test_sessions_basics() )