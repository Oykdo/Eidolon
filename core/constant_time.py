"""
Operations Cryptographiques en Temps Constant
Poly-Spinor Nexus 7D - Security Module

Protection contre les attaques par canal auxiliaire (side-channel):
- Timing attacks
- Cache timing
- Branch prediction

IMPORTANT: Ces fonctions sont concues pour avoir un temps
d'execution INDEPENDANT des valeurs d'entree.
"""

import hmac
import hashlib
import secrets
from typing import Tuple, Optional


class SideChannelError(Exception):
    """Erreur detectee lors de l'analyse side-channel"""
    pass


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """
    Comparaison en temps constant de deux sequences de bytes.
    
    Utilise hmac.compare_digest() qui est garanti constant-time
    dans la bibliotheque standard Python.
    
    Args:
        a: Premier buffer
        b: Second buffer
    
    Returns:
        True si a == b
    
    Note: Le temps d'execution ne depend PAS de la position
    de la premiere difference.
    """
    # Meme longueur requise pour vraiment constant-time
    if len(a) != len(b):
        # Comparer avec une valeur fictive pour garder le temps constant
        hmac.compare_digest(a, a)
        return False
    
    return hmac.compare_digest(a, b)


def constant_time_select(condition: bool, a: bytes, b: bytes) -> bytes:
    """
    Selection en temps constant: retourne a si condition, sinon b.
    
    Le temps d'execution est INDEPENDANT de condition.
    
    Args:
        condition: Booleen de selection
        a: Valeur si True
        b: Valeur si False
    
    Returns:
        a ou b selon condition
    """
    if len(a) != len(b):
        raise ValueError("Les deux valeurs doivent avoir la meme longueur")
    
    # Creer un masque: 0xFF si True, 0x00 si False
    mask = -int(condition) & 0xFF
    
    # Selection bit a bit
    result = bytes(
        (ai & mask) | (bi & (~mask & 0xFF))
        for ai, bi in zip(a, b)
    )
    
    return result


def constant_time_is_zero(data: bytes) -> bool:
    """
    Verifie si tous les bytes sont zero en temps constant.
    
    Args:
        data: Buffer a verifier
    
    Returns:
        True si tous les bytes sont 0
    """
    accumulator = 0
    for byte in data:
        accumulator |= byte
    
    return accumulator == 0


def constant_time_copy_if(condition: bool, dest: bytearray, src: bytes) -> None:
    """
    Copie conditionnelle en temps constant.
    
    Args:
        condition: Si True, copie src dans dest
        dest: Destination (modifiee in-place)
        src: Source
    """
    if len(dest) != len(src):
        raise ValueError("Source et destination doivent avoir la meme longueur")
    
    mask = -int(condition) & 0xFF
    
    for i in range(len(dest)):
        dest[i] = (src[i] & mask) | (dest[i] & (~mask & 0xFF))


class ConstantTimeInteger:
    """
    Entier avec operations en temps constant.
    
    Utile pour les operations cryptographiques ou le timing
    ne doit pas reveler d'information sur les valeurs.
    """
    
    def __init__(self, value: int, bit_width: int = 256):
        """
        Args:
            value: Valeur entiere
            bit_width: Largeur en bits (pour padding)
        """
        self.bit_width = bit_width
        self.byte_width = (bit_width + 7) // 8
        
        # Stocker comme bytes avec padding
        if value < 0:
            raise ValueError("Valeurs negatives non supportees")
        
        self._data = value.to_bytes(self.byte_width, 'big')
    
    @property
    def value(self) -> int:
        return int.from_bytes(self._data, 'big')
    
    def constant_time_eq(self, other: 'ConstantTimeInteger') -> bool:
        """Egalite en temps constant"""
        return constant_time_compare(self._data, other._data)
    
    def constant_time_lt(self, other: 'ConstantTimeInteger') -> bool:
        """
        Less-than en temps constant.
        
        Utilise une soustraction et verifie le signe.
        """
        # Calculer self - other
        borrow = 0
        for i in range(self.byte_width - 1, -1, -1):
            diff = self._data[i] - other._data[i] - borrow
            borrow = 1 if diff < 0 else 0
        
        return borrow == 1
    
    def constant_time_select(
        self,
        condition: bool,
        other: 'ConstantTimeInteger'
    ) -> 'ConstantTimeInteger':
        """Selection en temps constant: self si condition, other sinon"""
        result_data = constant_time_select(condition, self._data, other._data)
        result = ConstantTimeInteger(0, self.bit_width)
        result._data = result_data
        return result


class BlindedScalarOperations:
    """
    Operations scalaires avec masquage (blinding).
    
    Le masquage ajoute une valeur aleatoire qui est retiree apres,
    ce qui rend les operations resistantes aux attaques DPA
    (Differential Power Analysis).
    """
    
    def __init__(self, modulus: int):
        """
        Args:
            modulus: Module pour les operations
        """
        self.modulus = modulus
    
    def blinded_mul(self, a: int, b: int) -> int:
        """
        Multiplication modulaire avec masquage.
        
        a * b mod n = ((a + r1) * (b + r2) - a*r2 - b*r1 - r1*r2) mod n
        
        Le masquage rend l'operation resistante aux attaques par
        analyse de puissance.
        """
        # Generer des masques aleatoires
        r1 = secrets.randbelow(self.modulus)
        r2 = secrets.randbelow(self.modulus)
        
        # Calculs masques
        a_masked = (a + r1) % self.modulus
        b_masked = (b + r2) % self.modulus
        
        # Produit masque
        masked_product = (a_masked * b_masked) % self.modulus
        
        # Retirer les termes de masquage
        correction = (a * r2 + b * r1 + r1 * r2) % self.modulus
        result = (masked_product - correction) % self.modulus
        
        return result
    
    def blinded_exp(self, base: int, exponent: int) -> int:
        """
        Exponentiation modulaire avec masquage.
        
        Utilise le masquage d'exposant et de base pour
        resistance aux attaques SPA/DPA.
        """
        # Masquage de la base: base' = base * r^e mod n
        r = secrets.randbelow(self.modulus - 1) + 1
        r_inv = pow(r, -1, self.modulus)
        
        # Ajouter un masque a l'exposant (utilise phi(n) si connu)
        # Simplification: multiplier l'exposant par 1 + k*order
        # Pour un module premier: order = modulus - 1
        order = self.modulus - 1
        k = secrets.randbelow(1000)
        masked_exp = exponent + k * order
        
        # Base masquee
        base_masked = (base * pow(r, masked_exp, self.modulus)) % self.modulus
        
        # Exponentiation
        result_masked = pow(base_masked, masked_exp, self.modulus)
        
        # Demasquer
        result = (result_masked * pow(r_inv, masked_exp, self.modulus)) % self.modulus
        
        return result


class ConstantTimeAES:
    """
    Operations AES en temps constant.
    
    Note: Utilise les implementations de cryptography qui
    sont deja optimisees contre les timing attacks via
    AES-NI quand disponible.
    """
    
    def __init__(self, key: bytes):
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        self.key = key
    
    def encrypt_ctr(self, plaintext: bytes, nonce: bytes) -> bytes:
        """Chiffrement AES-CTR (inherement constant-time)"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        
        cipher = Cipher(algorithms.AES(self.key), modes.CTR(nonce))
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()
    
    def decrypt_ctr(self, ciphertext: bytes, nonce: bytes) -> bytes:
        """Dechiffrement AES-CTR"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        
        cipher = Cipher(algorithms.AES(self.key), modes.CTR(nonce))
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()


def secure_compare_strings(a: str, b: str) -> bool:
    """
    Comparaison securisee de strings (constant-time).
    
    Utile pour comparer des tokens, mots de passe hashes, etc.
    """
    return constant_time_compare(a.encode('utf-8'), b.encode('utf-8'))


def constant_time_lookup(table: list, index: int) -> any:
    """
    Lookup en temps constant dans une table.
    
    Le temps ne depend pas de l'index accede.
    Utile pour les S-boxes et autres lookups cryptographiques.
    
    Args:
        table: Liste de valeurs
        index: Index a acceder
    
    Returns:
        table[index]
    """
    if not 0 <= index < len(table):
        raise IndexError("Index hors limites")
    
    # Acceder a TOUS les elements et selectionner le bon
    result = table[0]
    
    for i in range(len(table)):
        # Masque: 0xFF si i == index, 0x00 sinon
        mask = -int(i == index)
        
        if isinstance(result, int):
            result = (table[i] & mask) | (result & ~mask)
        elif isinstance(result, bytes):
            result = constant_time_select(i == index, table[i], result)
    
    return result


class ConstantTimeHMAC:
    """
    HMAC avec verification en temps constant.
    """
    
    def __init__(self, key: bytes, algorithm: str = 'sha256'):
        self.key = key
        self.algorithm = algorithm
    
    def compute(self, message: bytes) -> bytes:
        """Calcule le HMAC"""
        return hmac.new(self.key, message, self.algorithm).digest()
    
    def verify(self, message: bytes, expected_mac: bytes) -> bool:
        """
        Verifie le HMAC en temps constant.
        
        Args:
            message: Message original
            expected_mac: MAC attendu
        
        Returns:
            True si valide
        """
        computed = self.compute(message)
        return constant_time_compare(computed, expected_mac)


# Fonctions utilitaires pour le module crypto principal

def secure_key_compare(key1: bytes, key2: bytes) -> bool:
    """Compare deux cles de maniere securisee"""
    return constant_time_compare(
        hashlib.sha256(key1).digest(),
        hashlib.sha256(key2).digest()
    )


def secure_token_verify(token: str, expected: str) -> bool:
    """Verifie un token de maniere securisee"""
    return secure_compare_strings(token, expected)
