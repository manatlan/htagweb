import pytest,asyncio,sys
from htagweb.sessions import createFile, createFilePersistent, createShm


async def session_test(method_session):
    session = await method_session("uid")
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
        session = await method_session("uid")
        assert session["nb"]==1

        session["x"]=42

        assert len(session)==2

        del session["x"]
        assert len(session)==1
        session.clear()
        assert len(session)==0

        session = await method_session("uid")
        assert len(session.items())==0

    finally:
        session.clear()



@pytest.mark.asyncio
async def test_sessions_file():
    await session_test( createFile )

@pytest.mark.asyncio
async def test_sessions_filepersitent():
    await session_test( createFilePersistent )


@pytest.mark.asyncio
async def test_sessions_shm():
    try:
        import shared_memory_dict
        await session_test( createShm )
    except:
        pass



if __name__=="__main__":
    import logging,multiprocessing,threading
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    # asyncio.run( test_sessions_basics() )