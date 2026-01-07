"""
Authentification JWT + ZKP pour l'API REST
Eidolon

Flow d'authentification:
1. Client envoie public_key (derive de vault_key)
2. Serveur genere un challenge aleatoire
3. Client cree une preuve ZKP avec sa vault_key
4. Serveur verifie la preuve ZKP
5. Si valide, serveur emet un JWT token
6. Client utilise JWT pour les requetes suivantes
"""

import os
import time
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

# JWT
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("[WARNING] PyJWT not installed: pip install PyJWT")

# Import ZKP
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zkp_auth import VaultZKPAuth, SchnorrZKP, SchnorrProof
from core.constant_time import constant_time_compare


class AuthError(Exception):
    """Erreur d'authentification"""
    pass


class TokenExpired(AuthError):
    """Token JWT expire"""
    pass


class InvalidProof(AuthError):
    """Preuve ZKP invalide"""
    pass


class RateLimitExceeded(AuthError):
    """Limite de requetes depassee"""
    pass


@dataclass
class AuthConfig:
    """Configuration de l'authentification"""
    jwt_secret: str = ""  # Genere automatiquement si vide
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    challenge_expire_seconds: int = 300
    max_failed_attempts: int = 5
    lockout_minutes: int = 15
    rate_limit_per_minute: int = 60


@dataclass
class AuthSession:
    """Session d'authentification"""
    user_id: str
    public_key: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime


class ChallengeStore:
    """Stockage des challenges en cours"""
    
    def __init__(self, expire_seconds: int = 300):
        self._challenges: Dict[str, Tuple[str, float]] = {}
        self._expire = expire_seconds
    
    def create(self, public_key_hex: str) -> str:
        """Cree un nouveau challenge pour une cle publique"""
        challenge = secrets.token_hex(32)
        self._challenges[public_key_hex] = (challenge, time.time())
        self._cleanup()
        return challenge
    
    def verify_and_consume(self, public_key_hex: str, challenge: str) -> bool:
        """Verifie et consomme un challenge"""
        if public_key_hex not in self._challenges:
            return False
        
        stored_challenge, created_at = self._challenges[public_key_hex]
        
        # Verifier expiration
        if time.time() - created_at > self._expire:
            del self._challenges[public_key_hex]
            return False
        
        # Verifier le challenge (constant-time)
        if not constant_time_compare(
            challenge.encode(),
            stored_challenge.encode()
        ):
            return False
        
        # Consommer le challenge
        del self._challenges[public_key_hex]
        return True
    
    def _cleanup(self):
        """Nettoie les challenges expires"""
        now = time.time()
        expired = [
            k for k, (_, t) in self._challenges.items()
            if now - t > self._expire
        ]
        for k in expired:
            del self._challenges[k]


class RateLimiter:
    """Limiteur de requetes par IP/user"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self._requests: Dict[str, list] = {}
        self._max = max_requests
        self._window = window_seconds
    
    def check(self, identifier: str) -> bool:
        """Verifie si la requete est autorisee"""
        now = time.time()
        
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        # Nettoyer les anciennes requetes
        self._requests[identifier] = [
            t for t in self._requests[identifier]
            if now - t < self._window
        ]
        
        # Verifier la limite
        if len(self._requests[identifier]) >= self._max:
            return False
        
        # Enregistrer la requete
        self._requests[identifier].append(now)
        return True
    
    def reset(self, identifier: str):
        """Reset le compteur pour un identifiant"""
        if identifier in self._requests:
            del self._requests[identifier]


class FailedAttemptTracker:
    """Suivi des tentatives echouees"""
    
    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15):
        self._attempts: Dict[str, list] = {}
        self._max = max_attempts
        self._lockout = lockout_minutes * 60
    
    def record_failure(self, identifier: str):
        """Enregistre une tentative echouee"""
        now = time.time()
        if identifier not in self._attempts:
            self._attempts[identifier] = []
        self._attempts[identifier].append(now)
    
    def is_locked(self, identifier: str) -> Tuple[bool, int]:
        """Verifie si l'identifiant est verrouille"""
        if identifier not in self._attempts:
            return False, 0
        
        now = time.time()
        # Garder seulement les tentatives recentes
        recent = [t for t in self._attempts[identifier] if now - t < self._lockout]
        self._attempts[identifier] = recent
        
        if len(recent) >= self._max:
            # Calcul du temps restant
            oldest = min(recent)
            remaining = int(self._lockout - (now - oldest))
            return True, remaining
        
        return False, 0
    
    def reset(self, identifier: str):
        """Reset apres succes"""
        if identifier in self._attempts:
            del self._attempts[identifier]


class JWTManager:
    """Gestionnaire de tokens JWT"""
    
    def __init__(self, config: AuthConfig):
        if not JWT_AVAILABLE:
            raise ImportError("PyJWT required: pip install PyJWT")
        
        self.config = config
        self._secret = config.jwt_secret or secrets.token_hex(32)
        self._algorithm = config.jwt_algorithm
    
    def create_access_token(
        self,
        user_id: str,
        public_key: str,
        additional_claims: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        """Cree un access token"""
        expires = datetime.utcnow() + timedelta(
            minutes=self.config.access_token_expire_minutes
        )
        
        payload = {
            "sub": user_id,
            "pub": public_key[:32],  # Fingerprint
            "type": "access",
            "exp": expires,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return token, expires
    
    def create_refresh_token(self, user_id: str, public_key: str) -> str:
        """Cree un refresh token"""
        expires = datetime.utcnow() + timedelta(
            days=self.config.refresh_token_expire_days
        )
        
        payload = {
            "sub": user_id,
            "pub": public_key[:32],
            "type": "refresh",
            "exp": expires,
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)
        }
        
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict:
        """Verifie et decode un token"""
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm]
            )
            
            if payload.get("type") != token_type:
                raise AuthError(f"Invalid token type: expected {token_type}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise TokenExpired("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthError(f"Invalid token: {e}")
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[str, datetime]:
        """Cree un nouveau access token depuis un refresh token"""
        payload = self.verify_token(refresh_token, "refresh")
        return self.create_access_token(payload["sub"], payload["pub"])


class ZKPAuthenticator:
    """
    Authentificateur combine JWT + ZKP
    
    Usage:
        auth = ZKPAuthenticator()
        
        # 1. Client demande un challenge
        challenge = auth.request_challenge(public_key_hex)
        
        # 2. Client cree une preuve ZKP (cote client)
        # proof = vault_zkp_auth.create_auth_proof(challenge)
        
        # 3. Client envoie la preuve
        session = auth.authenticate(public_key_hex, proof_dict, user_id)
        
        # 4. Verifier les requetes suivantes
        payload = auth.verify_request(access_token)
    """
    
    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        
        self._challenges = ChallengeStore(self.config.challenge_expire_seconds)
        self._rate_limiter = RateLimiter(
            self.config.rate_limit_per_minute
        )
        self._failed_attempts = FailedAttemptTracker(
            self.config.max_failed_attempts,
            self.config.lockout_minutes
        )
        self._jwt = JWTManager(self.config)
        
        # Stockage des sessions actives
        self._sessions: Dict[str, AuthSession] = {}
    
    def request_challenge(self, public_key_hex: str, client_ip: str = "") -> str:
        """
        Etape 1: Client demande un challenge.
        
        Args:
            public_key_hex: Cle publique ZKP en hexadecimal
            client_ip: IP du client pour rate limiting
        
        Returns:
            Challenge aleatoire a signer
        """
        identifier = client_ip or public_key_hex
        
        # Rate limiting
        if not self._rate_limiter.check(identifier):
            raise RateLimitExceeded("Too many requests")
        
        # Verifier le lockout
        locked, remaining = self._failed_attempts.is_locked(identifier)
        if locked:
            raise AuthError(f"Account locked. Try again in {remaining} seconds")
        
        # Generer le challenge
        challenge = self._challenges.create(public_key_hex)
        
        return challenge
    
    def authenticate(
        self,
        public_key_hex: str,
        proof: Dict,
        user_id: str,
        client_ip: str = ""
    ) -> AuthSession:
        """
        Etape 3: Verifie la preuve ZKP et emet les tokens.
        
        Args:
            public_key_hex: Cle publique ZKP
            proof: Preuve ZKP (dictionnaire)
            user_id: Identifiant utilisateur
            client_ip: IP du client
        
        Returns:
            Session avec access et refresh tokens
        """
        identifier = client_ip or public_key_hex
        
        # Rate limiting
        if not self._rate_limiter.check(identifier):
            raise RateLimitExceeded("Too many requests")
        
        # Verifier le lockout
        locked, remaining = self._failed_attempts.is_locked(identifier)
        if locked:
            raise AuthError(f"Account locked. Try again in {remaining} seconds")
        
        try:
            # Extraire le challenge de la preuve
            challenge = proof.get('challenge', '')
            
            # Verifier que le challenge est valide
            if not self._challenges.verify_and_consume(public_key_hex, challenge):
                raise InvalidProof("Invalid or expired challenge")
            
            # Verifier la preuve ZKP
            public_key = int(public_key_hex, 16)
            valid, reason = VaultZKPAuth.verify_auth(
                public_key,
                proof,
                challenge,
                max_age_seconds=self.config.challenge_expire_seconds
            )
            
            if not valid:
                raise InvalidProof(f"ZKP verification failed: {reason}")
            
            # Succes - reset les tentatives echouees
            self._failed_attempts.reset(identifier)
            
            # Creer les tokens
            access_token, expires = self._jwt.create_access_token(
                user_id, public_key_hex
            )
            refresh_token = self._jwt.create_refresh_token(user_id, public_key_hex)
            
            # Creer la session
            session = AuthSession(
                user_id=user_id,
                public_key=public_key_hex,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires,
                created_at=datetime.utcnow()
            )
            
            self._sessions[user_id] = session
            
            return session
            
        except InvalidProof:
            self._failed_attempts.record_failure(identifier)
            raise
        except Exception as e:
            self._failed_attempts.record_failure(identifier)
            raise AuthError(f"Authentication failed: {e}")
    
    def verify_request(self, access_token: str) -> Dict:
        """
        Verifie un access token pour une requete.
        
        Args:
            access_token: Token JWT
        
        Returns:
            Payload du token decode
        """
        return self._jwt.verify_token(access_token, "access")
    
    def refresh_session(self, refresh_token: str) -> Tuple[str, datetime]:
        """
        Rafraichit un access token.
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            (new_access_token, expires_at)
        """
        return self._jwt.refresh_access_token(refresh_token)
    
    def revoke_session(self, user_id: str):
        """Revoque une session"""
        if user_id in self._sessions:
            del self._sessions[user_id]
    
    def get_session(self, user_id: str) -> Optional[AuthSession]:
        """Recupere une session active"""
        return self._sessions.get(user_id)


# =============================================================================
# Client-side helper (pour generer les preuves)
# =============================================================================

class ZKPClientAuth:
    """
    Helper cote client pour l'authentification ZKP.
    
    Usage:
        client = ZKPClientAuth(vault_key)
        
        # 1. Obtenir la cle publique a envoyer au serveur
        public_key = client.get_public_key_hex()
        
        # 2. Recevoir le challenge du serveur
        # challenge = api.request_challenge(public_key)
        
        # 3. Creer la preuve
        proof = client.create_proof(challenge)
        
        # 4. Envoyer la preuve au serveur
        # session = api.authenticate(public_key, proof, user_id)
    """
    
    def __init__(self, vault_key: bytes):
        self._auth = VaultZKPAuth(vault_key)
    
    def get_public_key_hex(self) -> str:
        """Retourne la cle publique en hexadecimal"""
        return hex(self._auth.get_public_key())
    
    def get_fingerprint(self) -> str:
        """Retourne l'empreinte de la cle"""
        return self._auth.get_key_fingerprint()
    
    def create_proof(self, challenge: str) -> Dict:
        """Cree une preuve ZKP pour un challenge"""
        return self._auth.create_auth_proof(challenge)


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    print("="*60)
    print("  TEST AUTHENTIFICATION JWT + ZKP")
    print("="*60)
    
    # Simuler une vault_key
    vault_key = secrets.token_bytes(32)
    
    # Cote client
    client = ZKPClientAuth(vault_key)
    public_key = client.get_public_key_hex()
    print(f"\n[Client] Public key: {public_key[:32]}...")
    
    # Cote serveur
    config = AuthConfig(
        access_token_expire_minutes=30,
        challenge_expire_seconds=60
    )
    server = ZKPAuthenticator(config)
    
    # 1. Demander un challenge
    print("\n[1] Requesting challenge...")
    challenge = server.request_challenge(public_key)
    print(f"    Challenge: {challenge[:32]}...")
    
    # 2. Creer la preuve (cote client)
    print("\n[2] Creating ZKP proof...")
    proof = client.create_proof(challenge)
    print(f"    Proof created at: {proof['timestamp']}")
    
    # 3. Authentifier
    print("\n[3] Authenticating...")
    try:
        session = server.authenticate(public_key, proof, "user_123")
        print(f"    Success!")
        print(f"    User ID: {session.user_id}")
        print(f"    Access token: {session.access_token[:50]}...")
        print(f"    Expires at: {session.expires_at}")
    except AuthError as e:
        print(f"    Failed: {e}")
    
    # 4. Verifier une requete
    print("\n[4] Verifying request...")
    try:
        payload = server.verify_request(session.access_token)
        print(f"    Token valid!")
        print(f"    Subject: {payload['sub']}")
        print(f"    Type: {payload['type']}")
    except AuthError as e:
        print(f"    Failed: {e}")
    
    print("\n" + "="*60)
    print("  TEST COMPLETE")
    print("="*60)
