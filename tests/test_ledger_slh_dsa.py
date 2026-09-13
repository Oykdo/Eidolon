"""SLH-DSA : la signature de l'émetteur, séparée par usage."""
from __future__ import annotations

import pytest

from src.protocols.sphere_ledger import slh_dsa


@pytest.fixture(scope="module")
def kp():
    return slh_dsa.SlhDsaKeyPair.generate()


def test_sign_verify_and_purpose_separation(kp):
    payload = b"\x11" * 32
    sig = kp.sign("mint", payload)
    assert len(sig) == slh_dsa.SIGNATURE_SIZE
    assert slh_dsa.verify(kp.public_key, "mint", payload, sig)
    assert not slh_dsa.verify(kp.public_key, "receipt", payload, sig), "même octets, autre usage : refusé"
    assert not slh_dsa.verify(kp.public_key, "mint", b"\x12" * 32, sig)
    assert not slh_dsa.verify(kp.public_key, "mint", payload, sig[:-1] + bytes([sig[-1] ^ 1]))


def test_secret_round_trip_and_wrong_key(kp):
    again = slh_dsa.SlhDsaKeyPair.from_secret_dict(kp.to_secret_dict())
    sig = again.sign("checkpoint", b"\x00" * 32)
    assert slh_dsa.verify(kp.public_key, "checkpoint", b"\x00" * 32, sig)
    assert not slh_dsa.verify(b"\x00" * 32, "checkpoint", b"\x00" * 32, sig)
    with pytest.raises(ValueError):
        slh_dsa.SlhDsaKeyPair.from_secret_dict({"algorithm": "autre", "public_key": "", "secret_key": ""})
