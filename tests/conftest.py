"""Isolation du stockage pendant les tests.

Pourquoi ce fichier existe
--------------------------
Les numeros de vault sont une ressource rare et irreversible : la tranche
supreme est #1-33, et `next_vault_number` ne recule jamais. Un test qui
provisionne un vault, sollicite le registre ou rejoue un tick sans isolation
ecrit dans `%LOCALAPPDATA%/Eidolon` (ou l'equivalent POSIX) et brule un
numero de fondateur pour de bon.

Un seul fichier de tests isolait jusqu'ici (`test_api_http_contract.py`, a la
main, avec sauvegarde/restauration). `test_vault_registry_contract.py`, lui,
ne le faisait pas.

Ce conftest rend l'isolation systematique plutot que facultative :

1. `EIDOLON_DATA_DIR` est pose AVANT l'import des modules de test, car
   `config.paths` le lit a l'appel mais un module qui memorise un chemin a
   l'import capturerait sinon le vrai repertoire.
2. Une fixture de session verifie que le registre resolu se trouve bien dans
   le repertoire isole, et fait echouer la session sinon. Poser la variable
   ne suffit pas : encore faut-il prouver qu'elle a eu l'effet attendu.

Un `EIDOLON_DATA_DIR` deja pose par l'appelant est respecte -- il a deja
choisi son isolation -- mais la verification s'applique quand meme.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

_MARKER = "eidolon-tests-"

# Pose des l'import du conftest : pytest le charge avant les modules de test.
if not os.environ.get("EIDOLON_DATA_DIR"):
    _isolated = tempfile.mkdtemp(prefix=_MARKER)
    os.environ["EIDOLON_DATA_DIR"] = _isolated
    atexit.register(shutil.rmtree, _isolated, True)

EIDOLON_TEST_DATA_DIR = Path(os.environ["EIDOLON_DATA_DIR"]).resolve()


@pytest.fixture(scope="session", autouse=True)
def _refuse_to_touch_the_real_registry():
    """Echoue la session si le stockage resolu n'est pas isole.

    Le cout d'un faux negatif ici est un numero de fondateur brule sans
    retour arriere possible ; celui d'un faux positif est un message
    d'erreur. Le choix est vite fait.
    """
    try:
        from config.paths import get_vault_registry_path
    except Exception:
        # Le paquet n'est pas importable dans cet environnement de test :
        # rien a proteger, rien a signaler.
        yield
        return

    registry = Path(get_vault_registry_path()).resolve()

    if EIDOLON_TEST_DATA_DIR not in registry.parents:
        pytest.exit(
            "\nSTOCKAGE NON ISOLE : le registre resolu est\n"
            f"    {registry}\n"
            f"alors que EIDOLON_DATA_DIR vaut\n    {EIDOLON_TEST_DATA_DIR}\n\n"
            "Un test qui provisionne un vault brulerait un numero de\n"
            "fondateur reel (#1-33 = tier supreme, sans retour arriere).\n"
            "Verifier que config.paths lit bien EIDOLON_DATA_DIR.",
            returncode=1,
        )

    yield


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Un repertoire de donnees vierge pour un test qui en veut un a lui.

    L'isolation de session suffit a proteger le vrai stockage ; cette fixture
    sert quand un test a besoin de partir d'un registre vide sans subir ce
    qu'un test precedent y a laisse.
    """
    monkeypatch.setenv("EIDOLON_DATA_DIR", str(tmp_path))
    return tmp_path
