import asyncio
from htagweb.sessions.memory import startServer

async def server():
    startServer()
    while 1:
        await asyncio.sleep(1)

asyncio.run( server() )
