import pytest
from htagweb import manage
from htagweb.hrclient import HrClient

@pytest.mark.asyncio
async def test_manage():
    assert manage.users() == []

    try:
        hr=HrClient("ut2","examples.simple.App")

        assert manage.users() == []

        htm=await hr.create("//js") # will create fifo/process

        ll=manage.users()
        assert len(ll) == 1

        assert ll[0].uid == "ut2"

        assert ll[0].apps[0].cdate
        assert ll[0].apps[0].mdate
        ll[0].apps[0].kill()

        assert manage.users() == []

    finally:
        await HrClient.clean()



@pytest.mark.asyncio
async def test_manage_kill_user():
    assert manage.users() == []

    try:
        hr=HrClient("ut2","examples.simple.App")

        assert manage.users() == []

        htm=await hr.create("//js") # will create fifo/process

        ll=manage.users()
        assert len(ll) == 1

        assert ll[0].uid == "ut2"

        ll[0].kill()

        assert manage.users() == []

    finally:
        await HrClient.clean()
