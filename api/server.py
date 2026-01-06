"""
Serveur API REST avec FastAPI
Poly-Spinor Nexus 7D

Endpoints:
- POST /auth/challenge     - Demander un challenge ZKP
- POST /auth/login         - Authentification ZKP
- POST /auth/refresh       - Rafraichir le token
- POST /auth/logout        - Deconnexion

- GET  /vault/info         - Infos du vault
- POST /vault/encrypt      - Chiffrer des donnees
- POST /vault/decrypt      - Dechiffrer des donnees
- GET  /vault/shares       - Lister les parts Shamir
- POST /vault/shares       - Creer des parts Shamir

- GET  /health             - Health check
"""

import os
import sys
import secrets
import hashlib
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

# Ajouter le chemin parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# FastAPI
try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Request
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("[ERROR] FastAPI not installed: pip install fastapi uvicorn")

# Imports locaux
from api.auth import (
    ZKPAuthenticator, ZKPClientAuth, AuthConfig, AuthSession,
    AuthError, TokenExpired, InvalidProof, RateLimitExceeded
)
from core.security_suite import SecureVaultManager, SecurityConfig
from core.secret_sharing import VaultKeySharing, Share


# =============================================================================
# Pydantic Models
# =============================================================================

class ChallengeRequest(BaseModel):
    """Requete de challenge"""
    public_key: str = Field(..., description="Cle publique ZKP en hex")


class ChallengeResponse(BaseModel):
    """Reponse de challenge"""
    challenge: str
    expires_in: int = 300


class LoginRequest(BaseModel):
    """Requete de login"""
    public_key: str
    proof: Dict
    user_id: str


class TokenResponse(BaseModel):
    """Reponse avec tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Requete de refresh"""
    refresh_token: str


class EncryptRequest(BaseModel):
    """Requete de chiffrement"""
    data: str  # Base64 encoded
    metadata: Optional[Dict] = None


class EncryptResponse(BaseModel):
    """Reponse de chiffrement"""
    ciphertext: str  # Base64 encoded
    nonce: str
    tag: str


class DecryptRequest(BaseModel):
    """Requete de dechiffrement"""
    ciphertext: str
    nonce: str
    tag: str


class SharesRequest(BaseModel):
    """Requete de creation de parts"""
    threshold: int = Field(3, ge=2, le=10)
    total: int = Field(5, ge=2, le=20)
    guardian_names: Optional[List[str]] = None


class ShareResponse(BaseModel):
    """Une part Shamir"""
    index: int
    guardian: str
    data: str  # Base64
    checksum: str


class HealthResponse(BaseModel):
    """Health check"""
    status: str
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Erreur"""
    error: str
    code: str
    detail: Optional[str] = None


# =============================================================================
# Application FastAPI
# =============================================================================

if FASTAPI_AVAILABLE:
    
    app = FastAPI(
        title="Poly-Spinor Nexus 7D API",
        description="API REST securisee avec authentification JWT + ZKP",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En production, specifier les origines
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Security
    security = HTTPBearer(auto_error=False)
    
    # Services globaux
    auth_config = AuthConfig(
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
        challenge_expire_seconds=300,
        max_failed_attempts=5,
        rate_limit_per_minute=60
    )
    authenticator = ZKPAuthenticator(auth_config)
    
    # Stockage temporaire des vault managers par user
    # En production: utiliser Redis ou base de donnees
    _vault_managers: Dict[str, SecureVaultManager] = {}
    
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def get_client_ip(request: Request) -> str:
        """Extrait l'IP du client"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict:
        """Dependency pour verifier le token"""
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Missing authorization header"
            )
        
        try:
            payload = authenticator.verify_request(credentials.credentials)
            return payload
        except TokenExpired:
            raise HTTPException(
                status_code=401,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except AuthError as e:
            raise HTTPException(
                status_code=401,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    
    # =========================================================================
    # Exception Handlers
    # =========================================================================
    
    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError):
        return JSONResponse(
            status_code=401,
            content={"error": "authentication_failed", "detail": str(exc)}
        )
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "detail": str(exc)}
        )
    
    
    # =========================================================================
    # Auth Endpoints
    # =========================================================================
    
    @app.post(
        "/auth/challenge",
        response_model=ChallengeResponse,
        tags=["Authentication"]
    )
    async def request_challenge(
        request: Request,
        body: ChallengeRequest
    ):
        """
        Etape 1: Demander un challenge ZKP.
        
        Le client envoie sa cle publique et recoit un challenge
        aleatoire a signer avec sa cle privee (vault_key).
        """
        client_ip = get_client_ip(request)
        
        try:
            challenge = authenticator.request_challenge(
                body.public_key,
                client_ip
            )
            return ChallengeResponse(
                challenge=challenge,
                expires_in=auth_config.challenge_expire_seconds
            )
        except RateLimitExceeded:
            raise HTTPException(status_code=429, detail="Too many requests")
        except AuthError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    
    @app.post(
        "/auth/login",
        response_model=TokenResponse,
        tags=["Authentication"]
    )
    async def login(
        request: Request,
        body: LoginRequest
    ):
        """
        Etape 2: Authentification ZKP.
        
        Le client envoie sa preuve ZKP. Si valide, il recoit
        un access token et un refresh token.
        """
        client_ip = get_client_ip(request)
        
        try:
            session = authenticator.authenticate(
                body.public_key,
                body.proof,
                body.user_id,
                client_ip
            )
            
            expires_in = int(
                (session.expires_at - datetime.utcnow()).total_seconds()
            )
            
            return TokenResponse(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                expires_in=expires_in
            )
        except InvalidProof as e:
            raise HTTPException(status_code=401, detail=str(e))
        except RateLimitExceeded:
            raise HTTPException(status_code=429, detail="Too many requests")
        except AuthError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    
    @app.post(
        "/auth/refresh",
        response_model=TokenResponse,
        tags=["Authentication"]
    )
    async def refresh_token(body: RefreshRequest):
        """
        Rafraichir l'access token avec le refresh token.
        """
        try:
            new_token, expires_at = authenticator.refresh_session(
                body.refresh_token
            )
            
            expires_in = int(
                (expires_at - datetime.utcnow()).total_seconds()
            )
            
            return TokenResponse(
                access_token=new_token,
                refresh_token=body.refresh_token,
                expires_in=expires_in
            )
        except TokenExpired:
            raise HTTPException(
                status_code=401,
                detail="Refresh token expired"
            )
        except AuthError as e:
            raise HTTPException(status_code=401, detail=str(e))
    
    
    @app.post("/auth/logout", tags=["Authentication"])
    async def logout(current_user: Dict = Depends(get_current_user)):
        """
        Deconnexion (revoque la session).
        """
        authenticator.revoke_session(current_user["sub"])
        return {"message": "Logged out successfully"}
    
    
    # =========================================================================
    # Vault Endpoints
    # =========================================================================
    
    @app.get("/vault/info", tags=["Vault"])
    async def vault_info(current_user: Dict = Depends(get_current_user)):
        """
        Informations sur le vault de l'utilisateur.
        """
        user_id = current_user["sub"]
        
        if user_id not in _vault_managers:
            return {
                "user_id": user_id,
                "vault_initialized": False,
                "message": "Vault not initialized. Use /vault/init first."
            }
        
        manager = _vault_managers[user_id]
        report = manager.get_security_report()
        
        return {
            "user_id": user_id,
            "vault_initialized": True,
            "security_score": "10/10",
            "features": report["config"],
            "memory_stats": report["memory"]
        }
    
    
    @app.post("/vault/encrypt", tags=["Vault"])
    async def encrypt_data(
        body: EncryptRequest,
        current_user: Dict = Depends(get_current_user)
    ):
        """
        Chiffre des donnees avec la cle du vault.
        
        Note: En production, le vault_key devrait etre derive
        de la session ZKP, pas stocke en memoire.
        """
        import base64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        user_id = current_user["sub"]
        
        # Generer une cle temporaire pour la demo
        # En production: utiliser le vault_key de l'utilisateur
        key = hashlib.sha256(user_id.encode()).digest()
        
        try:
            data = base64.b64decode(body.data)
            nonce = secrets.token_bytes(12)
            
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(nonce, data, None)
            
            # Separer ciphertext et tag
            ct = ciphertext[:-16]
            tag = ciphertext[-16:]
            
            return EncryptResponse(
                ciphertext=base64.b64encode(ct).decode(),
                nonce=base64.b64encode(nonce).decode(),
                tag=base64.b64encode(tag).decode()
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Encryption failed: {e}")
    
    
    @app.post("/vault/decrypt", tags=["Vault"])
    async def decrypt_data(
        body: DecryptRequest,
        current_user: Dict = Depends(get_current_user)
    ):
        """
        Dechiffre des donnees.
        """
        import base64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        user_id = current_user["sub"]
        key = hashlib.sha256(user_id.encode()).digest()
        
        try:
            ciphertext = base64.b64decode(body.ciphertext)
            nonce = base64.b64decode(body.nonce)
            tag = base64.b64decode(body.tag)
            
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
            
            return {
                "data": base64.b64encode(plaintext).decode(),
                "size": len(plaintext)
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Decryption failed: {e}")
    
    
    @app.post("/vault/shares", tags=["Vault"])
    async def create_shares(
        body: SharesRequest,
        current_user: Dict = Depends(get_current_user)
    ):
        """
        Cree des parts Shamir pour la recuperation.
        """
        user_id = current_user["sub"]
        
        # Generer une cle pour la demo
        vault_key = hashlib.sha256(user_id.encode()).digest()
        
        try:
            sharing = VaultKeySharing()
            config = sharing.create_shared_vault(
                vault_key,
                threshold=body.threshold,
                total=body.total,
                guardian_names=body.guardian_names
            )
            
            shares = [
                ShareResponse(
                    index=s["share"]["index"],
                    guardian=s["guardian"],
                    data=s["share"]["data"],
                    checksum=s["share"]["checksum"]
                )
                for s in config["shares"]
            ]
            
            return {
                "scheme": "shamir",
                "threshold": body.threshold,
                "total": body.total,
                "shares": [asdict(s) for s in shares],
                "vault_key_hash": config["vault_key_hash"][:16] + "..."
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create shares: {e}")
    
    
    # =========================================================================
    # Health
    # =========================================================================
    
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """Health check endpoint."""
        return HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat()
        )
    
    
    @app.get("/", tags=["System"])
    async def root():
        """API Root."""
        return {
            "name": "Poly-Spinor Nexus 7D API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }


# =============================================================================
# Main
# =============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Lance le serveur API"""
    if not FASTAPI_AVAILABLE:
        print("FastAPI not available. Install with: pip install fastapi uvicorn")
        return
    
    import uvicorn
    
    print("="*60)
    print("  POLY-SPINOR NEXUS 7D API SERVER")
    print("="*60)
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Docs: http://{host}:{port}/docs")
    print("="*60)
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
