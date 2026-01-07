"""
Client API REST pour Eidolon
Exemple d'utilisation de l'API avec authentification JWT + ZKP

Usage:
    from api.client import VaultAPIClient
    
    # Avec vault_key existante
    client = VaultAPIClient("http://localhost:8000", vault_key)
    
    # Login
    client.login("user_123")
    
    # Utiliser l'API
    info = client.get_vault_info()
    encrypted = client.encrypt(b"secret data")
"""

import os
import sys
import base64
from typing import Optional, Dict, Any
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# HTTP client
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    try:
        import requests as httpx
        HTTPX_AVAILABLE = True
    except ImportError:
        HTTPX_AVAILABLE = False
        print("[WARNING] httpx or requests not installed")

from api.auth import ZKPClientAuth


class APIError(Exception):
    """Erreur API"""
    def __init__(self, status_code: int, message: str, detail: str = ""):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(f"[{status_code}] {message}: {detail}")


@dataclass
class APISession:
    """Session API"""
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str


class VaultAPIClient:
    """
    Client pour l'API Eidolon.
    
    Gere automatiquement:
    - Authentification ZKP
    - Tokens JWT
    - Refresh automatique
    
    Usage:
        client = VaultAPIClient("http://localhost:8000", vault_key)
        client.login("my_user_id")
        
        # API calls
        info = client.get_vault_info()
        encrypted = client.encrypt(b"my secret data")
        decrypted = client.decrypt(encrypted)
        shares = client.create_shares(threshold=3, total=5)
    """
    
    def __init__(self, base_url: str, vault_key: bytes):
        """
        Args:
            base_url: URL de base de l'API (ex: "http://localhost:8000")
            vault_key: Cle du vault (32 bytes)
        """
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx or requests required: pip install httpx")
        
        self.base_url = base_url.rstrip("/")
        self._zkp_auth = ZKPClientAuth(vault_key)
        self._session: Optional[APISession] = None
        self._client = httpx.Client(timeout=30.0) if hasattr(httpx, 'Client') else None
    
    @property
    def public_key(self) -> str:
        """Cle publique ZKP"""
        return self._zkp_auth.get_public_key_hex()
    
    @property
    def is_authenticated(self) -> bool:
        """True si authentifie"""
        return self._session is not None
    
    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        auth: bool = True
    ) -> Dict:
        """Execute une requete HTTP"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if auth and self._session:
            headers["Authorization"] = f"Bearer {self._session.access_token}"
        
        if self._client:
            # httpx
            response = self._client.request(
                method, url, json=json, headers=headers
            )
        else:
            # requests
            response = httpx.request(
                method, url, json=json, headers=headers
            )
        
        if response.status_code >= 400:
            try:
                error = response.json()
                raise APIError(
                    response.status_code,
                    error.get("error", "Unknown error"),
                    error.get("detail", "")
                )
            except ValueError:
                raise APIError(
                    response.status_code,
                    "Request failed",
                    response.text
                )
        
        return response.json()
    
    def login(self, user_id: str) -> APISession:
        """
        Authentification complete (challenge + ZKP + tokens).
        
        Args:
            user_id: Identifiant utilisateur
        
        Returns:
            Session avec tokens
        """
        # Etape 1: Demander un challenge
        challenge_resp = self._request(
            "POST",
            "/auth/challenge",
            json={"public_key": self.public_key},
            auth=False
        )
        challenge = challenge_resp["challenge"]
        
        # Etape 2: Creer la preuve ZKP
        proof = self._zkp_auth.create_proof(challenge)
        
        # Etape 3: Login
        login_resp = self._request(
            "POST",
            "/auth/login",
            json={
                "public_key": self.public_key,
                "proof": proof,
                "user_id": user_id
            },
            auth=False
        )
        
        self._session = APISession(
            access_token=login_resp["access_token"],
            refresh_token=login_resp["refresh_token"],
            expires_in=login_resp["expires_in"],
            user_id=user_id
        )
        
        return self._session
    
    def refresh(self) -> APISession:
        """Rafraichit le token"""
        if not self._session:
            raise APIError(401, "Not authenticated", "Call login() first")
        
        resp = self._request(
            "POST",
            "/auth/refresh",
            json={"refresh_token": self._session.refresh_token},
            auth=False
        )
        
        self._session.access_token = resp["access_token"]
        self._session.expires_in = resp["expires_in"]
        
        return self._session
    
    def logout(self):
        """Deconnexion"""
        if self._session:
            try:
                self._request("POST", "/auth/logout")
            except APIError:
                pass
            self._session = None
    
    def get_vault_info(self) -> Dict:
        """Recupere les infos du vault"""
        return self._request("GET", "/vault/info")
    
    def encrypt(self, data: bytes, metadata: Optional[Dict] = None) -> Dict:
        """
        Chiffre des donnees.
        
        Args:
            data: Donnees a chiffrer
            metadata: Metadonnees optionnelles
        
        Returns:
            {ciphertext, nonce, tag} en base64
        """
        return self._request(
            "POST",
            "/vault/encrypt",
            json={
                "data": base64.b64encode(data).decode(),
                "metadata": metadata
            }
        )
    
    def decrypt(self, encrypted: Dict) -> bytes:
        """
        Dechiffre des donnees.
        
        Args:
            encrypted: {ciphertext, nonce, tag}
        
        Returns:
            Donnees dechiffrees
        """
        resp = self._request(
            "POST",
            "/vault/decrypt",
            json=encrypted
        )
        return base64.b64decode(resp["data"])
    
    def create_shares(
        self,
        threshold: int = 3,
        total: int = 5,
        guardian_names: Optional[list] = None
    ) -> Dict:
        """
        Cree des parts Shamir.
        
        Args:
            threshold: Minimum de parts pour reconstruire
            total: Nombre total de parts
            guardian_names: Noms des gardiens
        
        Returns:
            Configuration avec les parts
        """
        return self._request(
            "POST",
            "/vault/shares",
            json={
                "threshold": threshold,
                "total": total,
                "guardian_names": guardian_names
            }
        )
    
    def health(self) -> Dict:
        """Health check"""
        return self._request("GET", "/health", auth=False)
    
    def close(self):
        """Ferme le client"""
        if self._client:
            self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# =============================================================================
# Demo / Test
# =============================================================================

def demo():
    """Demo du client API"""
    import secrets
    
    print("="*60)
    print("  DEMO CLIENT API EIDOLON")
    print("="*60)
    
    # Creer une vault_key pour la demo
    vault_key = secrets.token_bytes(32)
    print(f"\n[1] Vault key generee: {vault_key[:8].hex()}...")
    
    # Creer le client
    base_url = "http://localhost:8000"
    print(f"[2] Connexion a: {base_url}")
    
    try:
        client = VaultAPIClient(base_url, vault_key)
        
        # Health check
        print("\n[3] Health check...")
        try:
            health = client.health()
            print(f"    Status: {health['status']}")
        except Exception as e:
            print(f"    Serveur non disponible: {e}")
            print("\n    Lancez le serveur avec:")
            print("    python api/server.py")
            return
        
        # Login
        print("\n[4] Login avec ZKP...")
        session = client.login("demo_user")
        print(f"    Access token: {session.access_token[:50]}...")
        print(f"    Expires in: {session.expires_in}s")
        
        # Vault info
        print("\n[5] Vault info...")
        info = client.get_vault_info()
        print(f"    User: {info.get('user_id')}")
        print(f"    Initialized: {info.get('vault_initialized')}")
        
        # Encrypt
        print("\n[6] Encryption...")
        secret_data = b"Hello, Poly-Spinor Nexus!"
        encrypted = client.encrypt(secret_data)
        print(f"    Original: {secret_data}")
        print(f"    Ciphertext: {encrypted['ciphertext'][:32]}...")
        
        # Decrypt
        print("\n[7] Decryption...")
        decrypted = client.decrypt(encrypted)
        print(f"    Decrypted: {decrypted}")
        assert decrypted == secret_data, "Decryption failed!"
        print("    [OK] Match!")
        
        # Shamir shares
        print("\n[8] Creating Shamir shares (3/5)...")
        shares = client.create_shares(
            threshold=3,
            total=5,
            guardian_names=["Alice", "Bob", "Charlie", "David", "Eve"]
        )
        print(f"    Scheme: {shares['scheme']}")
        print(f"    Threshold: {shares['threshold']}/{shares['total']}")
        for s in shares['shares']:
            print(f"    - {s['guardian']}: {s['data'][:16]}...")
        
        # Logout
        print("\n[9] Logout...")
        client.logout()
        print("    Done!")
        
        print("\n" + "="*60)
        print("  DEMO COMPLETE - ALL TESTS PASSED")
        print("="*60)
        
    except APIError as e:
        print(f"\n[ERROR] API Error: {e}")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo()
