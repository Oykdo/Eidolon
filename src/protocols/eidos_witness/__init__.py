"""Témoin Eidos — le vérifieur public (Tier 1) du pont Eidolon ↔ Eidos.

Eidos (Oykdo/Eidos, Apache-2.0) est une chaîne fédérée post-quantique par
hachage pur : WOTS+ pour les dépenses, XMSS pour les validateurs, SHA-256
partout, bibliothèque standard seulement. Ce paquet en porte, à l'octet, ce
qu'il faut pour **juger sans rejouer** — comme la page Témoin de l'atelier :

- ``wots``    la dérivation d'Eidos (``graine_n = SHA-256("maitre/n")``, clé
              WOTS+ tweakée par ADRS, arbre L, adresse = SHA-256(gp ‖ racine)[:20]),
              la signature d'un condensat et la reconstruction de la clé ;
- ``xmss``    la vérification d'une signature de validateur (feuille i, chemin) ;
- ``tete``    la tête signée d'``etat.json`` : en-tête fédéré, ``id_bloc``,
              signature XMSS contre ``federation.json`` ;
- ``preuve``  la racine UTXO, la preuve d'inclusion d'une sortie, le verdict ;
- ``etat``    la lecture d'``etat.json`` et les sorties d'un coffre ;
- ``envoi``   la transaction : cœur canonique, témoins, sérialisation,
              encapsulation base64, signature des entrées d'un coffre ;
- ``carnet``  ``eidos.carnet`` (``eidos-carnet/1``), le format d'échange avec
              l'atelier, écrit et relu à l'octet ;
- ``actif``   le dossier d'un actif Eidos rangé dans une voûte : tête signée +
              sortie + preuve, jugé hors ligne.

Rien ici ne dérive, ne stocke ni ne touche une clé de voûte : la graine
maîtresse n'entre qu'en octets opaques, et sa dérivation depuis la voûte est
ailleurs (cœur fermé). Ce paquet n'importe jamais ``src.crypto`` ni
``src.holo``. Il ne parle pas au réseau : ``etat.json`` et ``federation.json``
lui sont donnés.

Vecteurs : ``tests/vectors/eidos_vecteurs.json`` (famille par famille, les
mêmes que ``vecteurs.json`` d'Eidos, partagés Python ↔ TypeScript).
"""
from . import actif, carnet, envoi, etat, preuve, tete, wots, xmss

__all__ = ["wots", "xmss", "tete", "preuve", "etat", "envoi", "carnet", "actif"]
