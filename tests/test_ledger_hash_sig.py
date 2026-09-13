"""WOTS+ : une clé, une signature, et rien d'autre que du hachage.

Ces tests ne verifient pas seulement qu'une signature valide passe. Ils
verifient ce qui fait la securite d'une signature a usage unique : qu'une
alteration du message ou de la signature est refusee, que la somme de
controle empeche de « monter » les chaines, que la cle refuse de resigner,
et qu'une signature d'une cle ne verifie pas sous une autre.
"""
from __future__ import annotations

import os

import pytest

from src.protocols.sphere_ledger import hash_sig as hs


def _kp(seed=b"\x01" * 32, pub=b"\x02" * 32, idx=0):
    return hs.WotsKeyPair(secret_seed=seed, public_seed=pub, ots_index=idx)


def test_sign_then_verify_round_trip():
    kp = _kp()
    m = hs.digest(b"sphere 42 -> voute B")
    sig = kp.sign(m)
    assert len(sig.sig) == hs.LEN and all(len(s) == hs.N for s in sig.sig)
    assert hs.verify(kp.public_key, m, sig)


def test_signature_is_deterministic_for_a_given_key():
    m = hs.digest(b"meme message")
    a = _kp().sign(m).to_bytes()
    b = _kp().sign(m).to_bytes()
    assert a == b
    assert _kp().public_key.root == _kp().public_key.root


def test_tampered_message_is_rejected():
    kp = _kp()
    m = hs.digest(b"original")
    sig = kp.sign(m)
    assert not hs.verify(kp.public_key, hs.digest(b"altere"), sig)


def test_tampered_signature_byte_is_rejected():
    kp = _kp()
    m = hs.digest(b"message")
    raw = bytearray(kp.sign(m).to_bytes())
    raw[5 * hs.N + 3] ^= 0x01
    assert not hs.verify(kp.public_key, m, hs.WotsSignature.from_bytes(bytes(raw)))


def test_checksum_blocks_forging_a_higher_digit():
    """Avancer une chaine d'un pas donne une signature valide pour un chiffre
    plus grand ; la somme de controle, elle, devrait alors descendre, ce qu'un
    faussaire ne sait pas faire. Le message construit ici a un chiffre 0 en
    tete, le cas le plus favorable a l'attaque."""
    kp = _kp()
    m = bytes([0x0F]) + b"\x00" * 31
    sig = kp.sign(m)
    forged_m = bytes([0x1F]) + b"\x00" * 31      # premier chiffre 0 -> 1
    adrs = hs.Address()
    adrs.set_ots(0)
    adrs.set_chain(0)
    forged = list(sig.sig)
    forged[0] = hs._chain(sig.sig[0], 0, 1, kp.public_seed, adrs)
    assert not hs.verify(kp.public_key, forged_m, hs.WotsSignature(forged))


def test_a_key_signs_exactly_once():
    kp = _kp()
    kp.sign(hs.digest(b"premier"))
    with pytest.raises(hs.HashSigError):
        kp.sign(hs.digest(b"second"))
    assert kp.used


def test_signature_does_not_verify_under_another_key():
    a = _kp(seed=b"\x0a" * 32)
    b = _kp(seed=b"\x0b" * 32)
    m = hs.digest(b"message")
    sig = a.sign(m)
    assert not hs.verify(b.public_key, m, sig)


def test_public_seed_and_index_are_part_of_the_key():
    m = hs.digest(b"message")
    kp = _kp(idx=7)
    sig = kp.sign(m)
    other_seed = hs.WotsPublicKey(b"\x03" * 32, 7, kp.public_key.root)
    other_index = hs.WotsPublicKey(kp.public_seed, 8, kp.public_key.root)
    assert not hs.verify(other_seed, m, sig)
    assert not hs.verify(other_index, m, sig)


def test_wrong_digest_length_is_rejected():
    kp = _kp()
    with pytest.raises(hs.HashSigError):
        kp.sign(b"trop court")


def test_signature_serialisation_round_trip():
    kp = _kp()
    m = hs.digest(b"message")
    sig = kp.sign(m)
    again = hs.WotsSignature.from_bytes(sig.to_bytes())
    assert hs.verify(kp.public_key, m, again)
    with pytest.raises(hs.HashSigError):
        hs.WotsSignature.from_bytes(sig.to_bytes()[:-1])


def test_message_digits_cover_base_w_and_checksum():
    digits = hs._message_digits(b"\xff" * 32)
    assert len(digits) == hs.LEN
    assert all(d == 15 for d in digits[:hs.LEN_1])
    assert digits[hs.LEN_1:] == [0, 0, 0], "somme de controle nulle quand tous les chiffres sont maximaux"
    digits = hs._message_digits(b"\x00" * 32)
    assert all(d == 0 for d in digits[:hs.LEN_1])
    # 64 * 15 = 960 = 0x3C0, decale de 4 bits -> 0x3C00 -> chiffres 3, 12, 0
    assert digits[hs.LEN_1:] == [3, 12, 0]


def test_random_keys_and_messages():
    for _ in range(5):
        kp = hs.WotsKeyPair()
        m = hs.digest(os.urandom(64))
        sig = kp.sign(m)
        assert hs.verify(kp.public_key, m, sig)
        assert not hs.verify(kp.public_key, hs.digest(os.urandom(64)), sig)
