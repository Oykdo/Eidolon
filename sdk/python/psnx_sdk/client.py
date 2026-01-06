"""
Client API pour le SDK Poly-Spinor Nexus 7D
"""

import base64
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    try:
        import requests as httpx
        HTTP_CLIENT = "requests"
    except ImportError:
        httpx = None
        HTTP_CLIENT = None

from .vault import Vault, EncryptedData
from .zkp import ZKPProver
from .sharing import SecretSharing, Share
from .exceptions import (
    NetworkError, AuthenticationError, PSNXError
)


@dataclass
class Session:
    """Session API"""
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str


class PSNXClient:
    """
    Client pour l'API Poly-Spinor Nexus 7D.
    
    Usage:
        client = PSNXClient("https://api.example.com", vault_key)
        
        # Login
        client.login("user_id")
        
        # Operations
        info = client.vault_info()
        encrypted = client.encrypt(b"data")
        decrypted = client.decrypt(encrypted)
        
        # Logout
        client.logout()
    
    Context manager:
        with PSNXClient(url, key) as client:
            client.login("user")
            ...
    """
    
    def __init__(
        self,
        base_url: str,
        vault_key: bytes,
        timeout: float = 30.0
    ):
        """
        Args:
            base_url: URL de l'API
            vault_key: Cle du vault
            timeout: Timeout des requetes
        """
        if httpx is None:
            raise ImportError("httpx or requests required: pip install httpx")
        
        self.base_url = base_url.rstrip("/")
        self._vault = Vault(vault_key)
        self._zkp = ZKPProver(vault_key)
        self._session: Optional[Session] = None
        self._timeout = timeout
        
        if HTTP_CLIENT == "httpx":
            self._client = httpx.Client(timeout=timeout)
        else:
            self._client = None
    
    @property
    def is_authenticated(self) -> bool:
        """True si connecte"""
        return self._session is not None
    
    @property
    def public_key(self) -> str:
        """Cle publique ZKP"""
        return self._zkp.get_public_key_hex()
    
    @property
    def fingerprint(self) -> str:
        """Empreinte du vault"""
        return self._vault.get_fingerprint()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        auth: bool = True
    ) -> Dict:
        """Execute une requete HTTP"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if auth and self._session:
            headers["Authorization"] = f"Bearer {self._session.access_token}"
        
        try:
            if self._client:
                response = self._client.request(
                    method, url, json=json, headers=headers
                )
            else:
                response = httpx.request(
                    method, url, json=json, headers=headers,
                    timeout=self._timeout
                )
            
            if response.status_code == 401:
                raise AuthenticationError("Authentication required or token expired")
            
            if response.status_code >= 400:
                try:
                    error = response.json()
                    raise NetworkError(
                        error.get("detail", "Request failed"),
                        response.status_code
                    )
                except ValueError:
                    raise NetworkError(response.text, response.status_code)
            
            return response.json()
            
        except (httpx.RequestError if HTTP_CLIENT == "httpx" else Exception) as e:
            if isinstance(e, (NetworkError, AuthenticationError)):
                raise
            raise NetworkError(f"Request failed: {e}")
    
    # =========================================================================
    # Authentication
    # =========================================================================
    
    def login(self, user_id: str) -> Session:
        """
        Authentification ZKP.
        
        Args:
            user_id: Identifiant utilisateur
        
        Returns:
            Session avec tokens
        """
        # 1. Demander challenge
        challenge_resp = self._request(
            "POST", "/auth/challenge",
            json={"public_key": self.public_key},
            auth=False
        )
        challenge = challenge_resp["challenge"]
        
        # 2. Creer preuve ZKP
        proof = self._zkp.create_proof(challenge)
        
        # 3. Login
        login_resp = self._request(
            "POST", "/auth/login",
            json={
                "public_key": self.public_key,
                "proof": proof,
                "user_id": user_id
            },
            auth=False
        )
        
        self._session = Session(
            access_token=login_resp["access_token"],
            refresh_token=login_resp["refresh_token"],
            expires_in=login_resp["expires_in"],
            user_id=user_id
        )
        
        return self._session
    
    def refresh(self) -> Session:
        """Rafraichit le token"""
        if not self._session:
            raise AuthenticationError("Not authenticated")
        
        resp = self._request(
            "POST", "/auth/refresh",
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
            except:
                pass
            self._session = None
    
    # =========================================================================
    # Vault Operations
    # =========================================================================
    
    def vault_info(self) -> Dict:
        """Informations du vault"""
        return self._request("GET", "/vault/info")
    
    def encrypt(
        self,
        data: bytes,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Chiffre des donnees via l'API.
        
        Note: Pour un chiffrement local (plus securise),
        utilisez self._vault.encrypt() directement.
        """
        return self._request(
            "POST", "/vault/encrypt",
            json={
                "data": base64.b64encode(data).decode(),
                "metadata": metadata
            }
        )
    
    def decrypt(self, encrypted: Dict) -> bytes:
        """Dechiffre des donnees via l'API"""
        resp = self._request("POST", "/vault/decrypt", json=encrypted)
        return base64.b64decode(resp["data"])
    
    def encrypt_local(self, data: bytes) -> EncryptedData:
        """Chiffrement local (cle ne quitte pas le client)"""
        return self._vault.encrypt(data)
    
    def decrypt_local(self, encrypted: EncryptedData) -> bytes:
        """Dechiffrement local"""
        return self._vault.decrypt(encrypted)
    
    # =========================================================================
    # Secret Sharing
    # =========================================================================
    
    def create_shares(
        self,
        threshold: int = 3,
        total: int = 5,
        guardian_names: Optional[List[str]] = None
    ) -> Dict:
        """Cree des parts Shamir via l'API"""
        return self._request(
            "POST", "/vault/shares",
            json={
                "threshold": threshold,
                "total": total,
                "guardian_names": guardian_names
            }
        )
    
    def create_shares_local(
        self,
        threshold: int = 3,
        total: int = 5
    ) -> List[Share]:
        """Cree des parts Shamir localement"""
        # Utiliser la cle derivee, pas la cle principale
        share_key = self._vault.derive_subkey("sharing")
        ss = SecretSharing(threshold, total)
        return ss.split(share_key)
    
    # =========================================================================
    # Health
    # =========================================================================
    
    def health(self) -> Dict:
        """Health check"""
        return self._request("GET", "/health", auth=False)
    
    def ping(self) -> bool:
        """Verifie la connectivite"""
        try:
            self.health()
            return True
        except:
            return False
    
    # =========================================================================
    # Context Manager
    # =========================================================================
    
    def close(self):
        """Ferme le client"""
        self.logout()
        if self._client:
            self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# =============================================================================
# Async Client (optional)
# =============================================================================

try:
    import asyncio
    
    class AsyncPSNXClient:
        """Version asynchrone du client (necessite httpx)"""
        
        def __init__(self, base_url: str, vault_key: bytes):
            if HTTP_CLIENT != "httpx":
                raise ImportError("Async client requires httpx")
            
            self.base_url = base_url.rstrip("/")
            self._vault = Vault(vault_key)
            self._zkp = ZKPProver(vault_key)
            self._session: Optional[Session] = None
            self._client = httpx.AsyncClient()
        
        async def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
            url = f"{self.base_url}{endpoint}"
            headers = kwargs.pop("headers", {})
            
            if self._session and kwargs.pop("auth", True):
                headers["Authorization"] = f"Bearer {self._session.access_token}"
            
            response = await self._client.request(
                method, url, headers=headers, **kwargs
            )
            
            if response.status_code >= 400:
                raise NetworkError(response.text, response.status_code)
            
            return response.json()
        
        async def login(self, user_id: str) -> Session:
            # Challenge
            resp = await self._request(
                "POST", "/auth/challenge",
                json={"public_key": self._zkp.get_public_key_hex()},
                auth=False
            )
            
            # Proof
            proof = self._zkp.create_proof(resp["challenge"])
            
            # Login
            resp = await self._request(
                "POST", "/auth/login",
                json={
                    "public_key": self._zkp.get_public_key_hex(),
                    "proof": proof,
                    "user_id": user_id
                },
                auth=False
            )
            
            self._session = Session(**resp, user_id=user_id)
            return self._session
        
        async def close(self):
            await self._client.aclose()
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            await self.close()

except ImportError:
    AsyncPSNXClient = None
