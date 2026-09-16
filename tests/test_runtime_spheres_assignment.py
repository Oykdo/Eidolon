"""Assignation des spheres runtime : l'attribution doit etre idempotente.

Regression du 2026-09-09 : un coffre local portait 80 enregistrements pour 4
`sphere_id` uniques — la meme distribution rejouee 20 fois par les redemarrages
`tsx watch` du bridge Cipher. Les doublons ne sont pas cosmetiques :
`sphere_resonance_bridge` compte les spheres en evolution pour alimenter la
resonance et `yield_processor` applique leurs multiplicateurs.
"""

import shutil
import tempfile

import pytest

from src.holo.runtime_spheres import RuntimeSphereManager, SphereState


VAULT_ID = "a" * 64
VAULT_NUMBER = 1


@pytest.fixture
def data_dir(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("EIDOLON_DATA_DIR", tmp)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_assign_sphere_is_idempotent(data_dir):
    """Rejouer une distribution n'empile pas de doublons."""
    mgr = RuntimeSphereManager(VAULT_ID, VAULT_NUMBER)
    first = mgr.assign_sphere("MYTHICAL_052__I00062", "mythic", "MYTHICAL_052")

    for _ in range(19):
        mgr.assign_sphere("MYTHICAL_052__I00062", "mythic", "MYTHICAL_052")

    spheres = mgr.list_spheres()
    assert len(spheres) == 1, f"{len(spheres)} spheres au lieu d'une seule"
    assert spheres[0]["sphere_id"] == first["sphere_id"]


def test_assign_sphere_preserves_progress(data_dir):
    """Une sphere deja detenue n'est pas remise a zero par une redistribution."""
    mgr = RuntimeSphereManager(VAULT_ID, VAULT_NUMBER)
    mgr.assign_sphere("LEGENDARY_007__I00001", "legendary")

    sphere = mgr.get_sphere("LEGENDARY_007__I00001")
    sphere["state"] = SphereState.EVOLVING.value
    sphere["activation_count"] = 3
    sphere["completed_cycles"] = 2

    mgr.assign_sphere("LEGENDARY_007__I00001", "legendary")

    after = mgr.get_sphere("LEGENDARY_007__I00001")
    assert after["state"] == SphereState.EVOLVING.value
    assert after["activation_count"] == 3
    assert after["completed_cycles"] == 2


def test_distinct_spheres_still_accumulate(data_dir):
    """La deduplication ne doit pas empecher d'attribuer des spheres differentes."""
    mgr = RuntimeSphereManager(VAULT_ID, VAULT_NUMBER)
    for i in range(4):
        mgr.assign_sphere(f"EPIC_00{i}__I0000{i}", "epic")

    assert len(mgr.list_spheres()) == 4


def test_assignment_survives_a_reload(data_dir):
    """Un nouveau manager relit le fichier : le rejeu ne doit pas dupliquer non plus."""
    RuntimeSphereManager(VAULT_ID, VAULT_NUMBER).assign_sphere("GENESIS_001__I00001", "genesis")
    RuntimeSphereManager(VAULT_ID, VAULT_NUMBER).assign_sphere("GENESIS_001__I00001", "genesis")

    assert len(RuntimeSphereManager(VAULT_ID, VAULT_NUMBER).list_spheres()) == 1
