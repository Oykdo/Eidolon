"""
Exceptions pour le SDK Eidolon
"""


class PSNXError(Exception):
    """Erreur de base du SDK"""
    pass


class AuthenticationError(PSNXError):
    """Erreur d'authentification"""
    pass


class EncryptionError(PSNXError):
    """Erreur de chiffrement"""
    pass


class DecryptionError(PSNXError):
    """Erreur de dechiffrement"""
    pass


class NetworkError(PSNXError):
    """Erreur reseau"""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class ValidationError(PSNXError):
    """Erreur de validation"""
    pass


class KeyError(PSNXError):
    """Erreur de cle"""
    pass


class ShareError(PSNXError):
    """Erreur de partage de secret"""
    pass
