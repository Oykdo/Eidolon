"""
Sources d'Entropie Quantique Reelles
Eidolon - Security Module

Sources supportees:
- ANU QRNG API (Australian National University)
- Random.org (atmospherique)
- Hardware QRNG (Quantis, ID Quantique)
- Fallback: OS entropy + timing jitter

IMPORTANT: L'entropie quantique est MIXEE avec l'entropie locale
pour une defense en profondeur (ne jamais faire confiance a une seule source)
"""

import hashlib
import secrets
import time
import struct
import asyncio
import threading
from typing import Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import os

# Import conditionnel pour les requetes HTTP
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class EntropyQuality(Enum):
    """Qualite de l'entropie"""
    QUANTUM = 5      # QRNG hardware/API verifiee
    ATMOSPHERIC = 4  # Random.org
    HARDWARE = 3     # /dev/random, CryptGenRandom
    TIMING = 2       # Jitter timing
    PRNG = 1         # Pseudo-aleatoire (fallback)


@dataclass
class EntropyResult:
    """Resultat d'une collecte d'entropie"""
    data: bytes
    quality: EntropyQuality
    source: str
    timestamp: float
    bits_collected: int
    
    def __repr__(self):
        return f"EntropyResult({self.bits_collected} bits from {self.source}, quality={self.quality.name})"


class EntropySource(ABC):
    """Interface abstraite pour sources d'entropie"""
    
    @abstractmethod
    def get_entropy(self, num_bytes: int) -> Optional[EntropyResult]:
        """Collecte de l'entropie"""
        pass
    
    @property
    @abstractmethod
    def quality(self) -> EntropyQuality:
        """Qualite de la source"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nom de la source"""
        pass


class ANUQuantumSource(EntropySource):
    """
    ANU Quantum Random Numbers API
    https://qrng.anu.edu.au/
    
    Vraie source quantique basee sur les fluctuations du vide quantique.
    Gratuit, limite a 1024 nombres par requete.
    """
    
    API_URL = "https://qrng.anu.edu.au/API/jsonI.php"
    MAX_PER_REQUEST = 1024
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._last_request = 0
        self._min_interval = 1.0  # Rate limiting
    
    @property
    def quality(self) -> EntropyQuality:
        return EntropyQuality.QUANTUM
    
    @property
    def name(self) -> str:
        return "ANU QRNG"
    
    def get_entropy(self, num_bytes: int) -> Optional[EntropyResult]:
        if not HTTPX_AVAILABLE:
            return None
        
        # Rate limiting
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        
        try:
            # ANU retourne des uint16, donc on demande num_bytes/2 nombres
            length = min((num_bytes + 1) // 2, self.MAX_PER_REQUEST)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    self.API_URL,
                    params={
                        "length": length,
                        "type": "uint16"
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            self._last_request = time.time()
            
            if not data.get("success"):
                return None
            
            # Convertir les uint16 en bytes
            numbers = data["data"]
            entropy_bytes = b''.join(
                struct.pack('>H', n) for n in numbers
            )[:num_bytes]
            
            return EntropyResult(
                data=entropy_bytes,
                quality=self.quality,
                source=self.name,
                timestamp=time.time(),
                bits_collected=len(entropy_bytes) * 8
            )
            
        except Exception as e:
            return None


class RandomOrgSource(EntropySource):
    """
    Random.org API
    Entropie atmospherique (bruit radio).
    Gratuit avec limites, API key pour usage intensif.
    """
    
    API_URL = "https://www.random.org/integers/"
    
    def __init__(self, api_key: Optional[str] = None, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout
    
    @property
    def quality(self) -> EntropyQuality:
        return EntropyQuality.ATMOSPHERIC
    
    @property
    def name(self) -> str:
        return "Random.org"
    
    def get_entropy(self, num_bytes: int) -> Optional[EntropyResult]:
        if not HTTPX_AVAILABLE:
            return None
        
        try:
            # Random.org limite a 10000 entiers par requete
            num_ints = min(num_bytes, 10000)
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    self.API_URL,
                    params={
                        "num": num_ints,
                        "min": 0,
                        "max": 255,
                        "col": 1,
                        "base": 10,
                        "format": "plain",
                        "rnd": "new"
                    }
                )
                response.raise_for_status()
            
            # Parser la reponse (un entier par ligne)
            lines = response.text.strip().split('\n')
            entropy_bytes = bytes(int(line) for line in lines if line.strip())
            
            return EntropyResult(
                data=entropy_bytes[:num_bytes],
                quality=self.quality,
                source=self.name,
                timestamp=time.time(),
                bits_collected=len(entropy_bytes[:num_bytes]) * 8
            )
            
        except Exception:
            return None


class OSEntropySource(EntropySource):
    """
    Entropie du systeme d'exploitation.
    - Linux: /dev/urandom (avec /dev/random blocking si disponible)
    - Windows: CryptGenRandom
    - macOS: /dev/urandom + SecRandomCopyBytes
    """
    
    def __init__(self):
        pass
    
    @property
    def quality(self) -> EntropyQuality:
        return EntropyQuality.HARDWARE
    
    @property
    def name(self) -> str:
        return "OS Entropy"
    
    def get_entropy(self, num_bytes: int) -> Optional[EntropyResult]:
        try:
            # secrets.token_bytes utilise la meilleure source OS
            entropy_bytes = secrets.token_bytes(num_bytes)
            
            return EntropyResult(
                data=entropy_bytes,
                quality=self.quality,
                source=self.name,
                timestamp=time.time(),
                bits_collected=num_bytes * 8
            )
        except Exception:
            return None


class TimingJitterSource(EntropySource):
    """
    Entropie basee sur le jitter de timing.
    Collecte les variations de temps d'execution.
    """
    
    def __init__(self, iterations_per_byte: int = 100):
        self.iterations = iterations_per_byte
    
    @property
    def quality(self) -> EntropyQuality:
        return EntropyQuality.TIMING
    
    @property
    def name(self) -> str:
        return "Timing Jitter"
    
    def get_entropy(self, num_bytes: int) -> Optional[EntropyResult]:
        try:
            entropy_bits = []
            
            for _ in range(num_bytes * 8):
                # Mesurer le jitter
                times = []
                for _ in range(self.iterations):
                    start = time.perf_counter_ns()
                    # Operation avec timing variable
                    _ = hashlib.sha256(os.urandom(32)).digest()
                    end = time.perf_counter_ns()
                    times.append(end - start)
                
                # LSB de la variance
                variance = sum((t - sum(times)//len(times))**2 for t in times)
                entropy_bits.append(variance & 1)
            
            # Convertir bits en bytes
            entropy_bytes = bytes(
                sum(entropy_bits[i*8:(i+1)*8][j] << j for j in range(8))
                for i in range(num_bytes)
            )
            
            return EntropyResult(
                data=entropy_bytes,
                quality=self.quality,
                source=self.name,
                timestamp=time.time(),
                bits_collected=num_bytes * 8
            )
            
        except Exception:
            return None


class HybridEntropyPool:
    """
    Pool d'entropie hybride combinant plusieurs sources.
    
    Principe: Ne jamais faire confiance a une seule source.
    Toutes les sources sont mixees avec XOR + HKDF.
    
    Usage:
        pool = HybridEntropyPool()
        entropy = pool.get_entropy(64)  # 64 bytes d'entropie mixee
    """
    
    def __init__(
        self,
        use_quantum: bool = True,
        use_atmospheric: bool = True,
        timeout: float = 5.0
    ):
        self.sources: List[EntropySource] = []
        
        # Toujours inclure OS entropy
        self.sources.append(OSEntropySource())
        
        # Sources optionnelles
        if use_quantum and HTTPX_AVAILABLE:
            self.sources.append(ANUQuantumSource(timeout=timeout))
        
        if use_atmospheric and HTTPX_AVAILABLE:
            self.sources.append(RandomOrgSource(timeout=timeout))
        
        # Timing jitter comme backup
        self.sources.append(TimingJitterSource())
        
        # Pool interne
        self._pool = bytearray()
        self._pool_lock = threading.Lock()
        self._results: List[EntropyResult] = []
    
    def _mix_entropy(self, sources: List[bytes], extra_data: bytes = b'') -> bytes:
        """
        Mixe plusieurs sources d'entropie.
        
        Methode:
        1. XOR de toutes les sources (meme taille)
        2. HKDF pour uniformiser
        """
        if not sources:
            raise ValueError("Aucune source d'entropie")
        
        # Determiner la taille maximale
        max_len = max(len(s) for s in sources)
        
        # XOR de toutes les sources (padding avec zeros)
        mixed = bytearray(max_len)
        for source in sources:
            for i, byte in enumerate(source):
                mixed[i] ^= byte
        
        # Ajouter extra_data
        combined = bytes(mixed) + extra_data
        
        # HKDF pour uniformiser
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes
        
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=max_len,
            salt=b'PSNX_ENTROPY_MIX_v1',
            info=b'hybrid_entropy_pool'
        )
        
        return hkdf.derive(combined)
    
    def get_entropy(
        self,
        num_bytes: int,
        min_sources: int = 2,
        require_quantum: bool = False
    ) -> bytes:
        """
        Collecte de l'entropie mixee de plusieurs sources.
        
        Args:
            num_bytes: Nombre de bytes requis
            min_sources: Nombre minimum de sources requises
            require_quantum: Exiger au moins une source quantique
        
        Returns:
            Entropie mixee de haute qualite
        """
        collected: List[bytes] = []
        self._results = []
        has_quantum = False
        
        # Collecter depuis toutes les sources disponibles
        for source in self.sources:
            result = source.get_entropy(num_bytes)
            if result and len(result.data) >= num_bytes:
                collected.append(result.data[:num_bytes])
                self._results.append(result)
                if result.quality == EntropyQuality.QUANTUM:
                    has_quantum = True
        
        # Verifier les contraintes
        if len(collected) < min_sources:
            # Fallback: augmenter avec timing jitter
            jitter = TimingJitterSource(iterations_per_byte=200)
            for _ in range(min_sources - len(collected)):
                result = jitter.get_entropy(num_bytes)
                if result:
                    collected.append(result.data)
                    self._results.append(result)
        
        if require_quantum and not has_quantum:
            raise ValueError("Source quantique requise mais non disponible")
        
        # Ajouter timestamp et compteur comme extra entropy
        extra = struct.pack('>dQ', time.time(), id(self))
        
        # Mixer toutes les sources
        return self._mix_entropy(collected, extra)
    
    def get_entropy_async(
        self,
        num_bytes: int,
        callback: Callable[[bytes], None]
    ) -> None:
        """
        Collecte asynchrone d'entropie.
        
        Args:
            num_bytes: Nombre de bytes requis
            callback: Fonction appelee avec l'entropie
        """
        def worker():
            entropy = self.get_entropy(num_bytes)
            callback(entropy)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def get_collection_report(self) -> dict:
        """Retourne un rapport sur la derniere collecte"""
        return {
            'sources_used': len(self._results),
            'total_bits': sum(r.bits_collected for r in self._results),
            'quality_breakdown': {
                q.name: sum(1 for r in self._results if r.quality == q)
                for q in EntropyQuality
            },
            'sources': [
                {
                    'name': r.source,
                    'quality': r.quality.name,
                    'bits': r.bits_collected
                }
                for r in self._results
            ]
        }


class QuantumEntropyManager:
    """
    Gestionnaire d'entropie quantique pour le generateur de cles.
    
    Usage:
        qem = QuantumEntropyManager()
        seed = qem.generate_quantum_seed(64)
        print(qem.get_quality_report())
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        # Singleton
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.pool = HybridEntropyPool(
            use_quantum=True,
            use_atmospheric=True,
            timeout=5.0
        )
        self._total_generated = 0
        self._quantum_bits = 0
        self._initialized = True
    
    def generate_quantum_seed(
        self,
        size: int = 64,
        require_quantum: bool = False
    ) -> bytes:
        """
        Genere une seed avec entropie quantique.
        
        Args:
            size: Taille en bytes
            require_quantum: Exiger une source quantique (peut echouer)
        
        Returns:
            Seed de haute qualite
        """
        entropy = self.pool.get_entropy(
            size,
            min_sources=2,
            require_quantum=require_quantum
        )
        
        # Stats
        self._total_generated += size * 8
        for result in self.pool._results:
            if result.quality == EntropyQuality.QUANTUM:
                self._quantum_bits += result.bits_collected
        
        return entropy
    
    def get_quality_report(self) -> dict:
        """Retourne un rapport de qualite"""
        collection = self.pool.get_collection_report()
        return {
            **collection,
            'total_generated_bits': self._total_generated,
            'quantum_bits_collected': self._quantum_bits,
            'quantum_percentage': (
                (self._quantum_bits / self._total_generated * 100)
                if self._total_generated > 0 else 0
            )
        }


# Fonction utilitaire pour usage simple
def get_quantum_entropy(num_bytes: int = 64) -> bytes:
    """
    Obtient de l'entropie quantique mixee.
    
    Args:
        num_bytes: Nombre de bytes requis
    
    Returns:
        Entropie de haute qualite
    """
    manager = QuantumEntropyManager()
    return manager.generate_quantum_seed(num_bytes)
