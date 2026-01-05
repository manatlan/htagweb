import pytest
import asyncio
import time
from htagweb import manage
from htagweb.hrclient import HrClient

@pytest.mark.asyncio
async def test_manage():
    # Nettoyage initial plus agressif
    await HrClient.clean()
    await asyncio.sleep(0.1)  # Donner le temps aux processus de se terminer
    
    # Vérifier que tout est propre
    users_before = manage.users()
    for user in users_before:
        user.kill()
    await asyncio.sleep(0.1)
    
    assert manage.users() == []

    try:
        hr=HrClient("ut2_manage_test","examples.simple.App")

        # Vérifier que la liste est toujours vide avant de créer
        assert manage.users() == []

        htm=await hr.create("//js") # will create fifo/process

        # Attendre un peu pour que le processus soit complètement démarré
        await asyncio.sleep(0.2)

        ll=manage.users()
        assert len(ll) == 1

        assert ll[0].uid == "ut2_manage_test"

        assert ll[0].apps[0].cdate
        assert ll[0].apps[0].mdate
        ll[0].apps[0].kill()

        # Attendre que le processus soit tué
        await asyncio.sleep(0.2)

        assert manage.users() == []

    finally:
        await HrClient.clean()
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_manage_kill_user():
    # Nettoyage initial plus agressif
    await HrClient.clean()
    await asyncio.sleep(0.1)  # Donner le temps aux processus de se terminer
    
    # Vérifier que tout est propre
    users_before = manage.users()
    for user in users_before:
        user.kill()
    await asyncio.sleep(0.1)
    
    assert manage.users() == []

    try:
        hr=HrClient("ut2_kill_test","examples.simple.App")

        # Vérifier que la liste est toujours vide avant de créer
        assert manage.users() == []

        htm=await hr.create("//js") # will create fifo/process

        # Attendre un peu pour que le processus soit complètement démarré
        await asyncio.sleep(0.2)

        ll=manage.users()
        assert len(ll) == 1

        assert ll[0].uid == "ut2_kill_test"

        ll[0].kill()

        # Attendre que le processus soit tué
        await asyncio.sleep(0.2)

        assert manage.users() == []

    finally:
        await HrClient.clean()
        await asyncio.sleep(0.1)