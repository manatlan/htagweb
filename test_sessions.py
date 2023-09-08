import pytest,asyncio,sys
from htagweb.sessions import createFile, createFilePersistent, createShm, createMem

# @pytest.fixture( params=["createFile", "createFilePersistent"] )
# @pytest.fixture( params=["createFile", "createFilePersistent", "createMem"] )
# @pytest.fixture( params=["createFile", "createFilePersistent", "createShm", "createMem"] )
# def method_session(request):
#    if request.param=="createFile":
#         return createFile
#    elif request.param=="createFilePersistent":
#         return createFilePersistent
#    elif request.param=="createShm":
#         return createShm
#    elif request.param=="createMem":
        # from htagweb.sessions.memory import startServer
        # assert asyncio.get_event_loop()
        # startServer()
        # return createMem


async def session_test(method_session):
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



@pytest.mark.asyncio
async def test_sessions_file():
    await session_test( createFile )

@pytest.mark.asyncio
async def test_sessions_filepersitent():
    await session_test( createFilePersistent )

# @pytest.mark.asyncio
# async def test_sessions_memory():
#     from htagweb.sessions.memory import startServer,PX
#     startServer()

#     await session_test( createMem )


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