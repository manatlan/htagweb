import pytest,asyncio
from htagweb.sessions import createFile, createShm, createMem

def test_sessions_basics():
    for method in [createFile, createShm]:

        state = method("uid")
        try:
            nb=state.get("nb",0)
            nb+=1
            state["nb"]=nb
            assert state["nb"]==1
        finally:
            state.clear()

# def test_sessions_memory():
#     async def test():
#         state = createMem("uid")
#         try:
#             nb=state.get("nb",0)
#             nb+=1
#             state["nb"]=nb
#             assert state["nb"]==1
#         finally:
#             state.clear()

#     asyncio.run(test())