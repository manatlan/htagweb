import pytest,asyncio
from htagweb.sessions import createFile, createShm

@pytest.mark.asyncio
async def test_sessions_basics():
    # for method in [createFile, createShm, createMem ]:
    for method in [createFile, createShm ]:

        session = await method("uid")
        try:
            session["nb"]=session.get("nb",0) + 1

            # ensure persistance is present
            session = await method("uid")
            assert session["nb"]==1
        finally:
            session.clear()

# @pytest.mark.asyncio
# async def test_sessions_memory():

#     session = await createMem("uid")
#     session["nb"]=session.get("nb",0) + 1

#     await asyncio.sleep(1)
#     # ensure persistance is present
#     session = await createMem("uid")

#     assert session["nb"]==1
#     await asyncio.sleep(1)

if __name__=="__main__":
    import logging,multiprocessing,threading
    logging.basicConfig(format='[%(levelname)-5s] %(name)s: %(message)s',level=logging.DEBUG)

    asyncio.run( test_sessions_basics() )