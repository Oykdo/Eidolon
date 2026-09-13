"""Le grand livre de vesting doit suivre config/paths.py, pas l'arborescence source.

Regression du 2026-09-09 : `RunesVestingManager.__init__` retombait sur
`Path(__file__).parent.parent.parent / "runes_vesting"`, un chemin relatif au
code et aveugle a EIDOLON_DATA_DIR. Chaque `register_vault` — y compris depuis
un test dont le registre part dans un repertoire temporaire — ecrivait une
allocation PSNX reelle dans le grand livre du depot. Cinq coffres distincts y
portaient le numero 1, a 105 000 PSNX chacun.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from config.paths import get_runes_vesting_dir
from src.holo.runes_vesting import RunesVestingManager


SOURCE_TREE_LEDGER = Path(__file__).parent.parent / "runes_vesting"


@pytest.fixture
def data_dir(monkeypatch):
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("EIDOLON_DATA_DIR", tmp)
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def test_default_storage_follows_data_dir(data_dir):
    """Sans argument, le manager range ses fichiers sous EIDOLON_DATA_DIR."""
    mgr = RunesVestingManager()
    assert data_dir in mgr.storage_path.parents or mgr.storage_path == data_dir / "data" / "runes_vesting"
    assert mgr.storage_path == get_runes_vesting_dir()


def test_writing_a_schedule_stays_out_of_the_source_tree(data_dir):
    """Creer un echeancier ne doit rien ecrire a cote du code."""
    before = _ledger_snapshot()

    mgr = RunesVestingManager()
    mgr.create_vesting_schedule(vault_id="b" * 64, vault_number=1)

    written = mgr.storage_path / "vesting_schedules.json"
    assert written.exists(), "l'echeancier n'a pas ete ecrit dans le repertoire configure"
    assert str(data_dir) in str(written)
    assert _ledger_snapshot() == before, "le grand livre de l'arborescence source a ete touche"


def test_explicit_storage_path_still_wins(data_dir, tmp_path):
    """Un chemin explicite reste prioritaire (utilise par test_api_http_contract)."""
    explicit = tmp_path / "ailleurs"
    assert RunesVestingManager(storage_path=explicit).storage_path == explicit


def _ledger_snapshot():
    """Etat du grand livre de l'arborescence source : absent, ou son contenu."""
    ledger = SOURCE_TREE_LEDGER / "vesting_schedules.json"
    if not ledger.exists():
        return None
    return ledger.read_bytes()
