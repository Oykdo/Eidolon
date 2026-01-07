"""
Protection Memoire Avancee pour Cles Cryptographiques
Eidolon - Security Module

Features:
- Verrouillage en RAM (anti-swap)
- Effacement securise multi-passes
- Masquage XOR rotatif
- Protection contre cold boot attacks
"""

import ctypes
import secrets
import atexit
import platform
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


class SecureZeroMethod(Enum):
    """Methodes d'effacement securise"""
    SIMPLE = 1      # 1 pass zeros
    DOD_3 = 3       # DoD 5220.22-M (3 passes)
    DOD_7 = 7       # DoD 5220.22-M ECE (7 passes)
    GUTMANN = 35    # Gutmann method (35 passes)


@dataclass
class MemoryStats:
    """Statistiques de la memoire securisee"""
    total_allocated: int = 0
    total_freed: int = 0
    active_buffers: int = 0
    locked_bytes: int = 0
    rotation_count: int = 0


class SecureMemoryError(Exception):
    """Erreur de memoire securisee"""
    pass


class SecureBuffer:
    """
    Buffer memoire securise avec protection avancee.
    
    Features:
    - Verrouillage en RAM (evite le swap sur disque)
    - Effacement garanti a la destruction (multi-passes)
    - Masquage XOR rotatif (protection cold boot)
    - Thread-safe
    
    Usage:
        with SecureBuffer(32) as buf:
            buf.write(secret_key)
            key = buf.read()
    """
    
    _global_stats = MemoryStats()
    _stats_lock = threading.Lock()
    
    def __init__(self, size: int, auto_rotate_seconds: int = 60):
        """
        Args:
            size: Taille du buffer en bytes
            auto_rotate_seconds: Intervalle de rotation du masque (0 = desactive)
        """
        if size <= 0 or size > 1024 * 1024:  # Max 1MB
            raise ValueError("Taille invalide (1 byte - 1MB)")
        
        self.size = size
        self._buffer = ctypes.create_string_buffer(size)
        self._mask = bytearray(secrets.token_bytes(size))
        self._data_length = 0
        self._locked = False
        self._destroyed = False
        self._lock = threading.RLock()
        
        # Verrouiller en memoire
        self._lock_memory()
        
        # Rotation automatique du masque
        self._rotation_timer: Optional[threading.Timer] = None
        if auto_rotate_seconds > 0:
            self._start_rotation_timer(auto_rotate_seconds)
        
        # Enregistrer le nettoyage
        atexit.register(self._cleanup)
        
        # Stats
        with SecureBuffer._stats_lock:
            SecureBuffer._global_stats.total_allocated += size
            SecureBuffer._global_stats.active_buffers += 1
    
    def _lock_memory(self):
        """Verrouille la memoire pour eviter le swap"""
        try:
            if platform.system() == 'Windows':
                kernel32 = ctypes.windll.kernel32
                result = kernel32.VirtualLock(
                    ctypes.addressof(self._buffer),
                    ctypes.c_size_t(self.size)
                )
                self._locked = result != 0
            else:
                # Linux/macOS
                libc = ctypes.CDLL(None, use_errno=True)
                result = libc.mlock(
                    ctypes.addressof(self._buffer),
                    ctypes.c_size_t(self.size)
                )
                self._locked = result == 0
            
            if self._locked:
                with SecureBuffer._stats_lock:
                    SecureBuffer._global_stats.locked_bytes += self.size
        except Exception:
            self._locked = False
    
    def _unlock_memory(self):
        """Deverrouille la memoire"""
        if not self._locked:
            return
        
        try:
            if platform.system() == 'Windows':
                kernel32 = ctypes.windll.kernel32
                kernel32.VirtualUnlock(
                    ctypes.addressof(self._buffer),
                    ctypes.c_size_t(self.size)
                )
            else:
                libc = ctypes.CDLL(None, use_errno=True)
                libc.munlock(
                    ctypes.addressof(self._buffer),
                    ctypes.c_size_t(self.size)
                )
            
            with SecureBuffer._stats_lock:
                SecureBuffer._global_stats.locked_bytes -= self.size
        except Exception:
            pass
        
        self._locked = False
    
    def _start_rotation_timer(self, interval: int):
        """Demarre le timer de rotation du masque"""
        def rotate():
            if not self._destroyed:
                self.rotate_mask()
                self._rotation_timer = threading.Timer(interval, rotate)
                self._rotation_timer.daemon = True
                self._rotation_timer.start()
        
        self._rotation_timer = threading.Timer(interval, rotate)
        self._rotation_timer.daemon = True
        self._rotation_timer.start()
    
    def write(self, data: bytes) -> None:
        """
        Ecrit des donnees dans le buffer (masquees).
        
        Args:
            data: Donnees a stocker
        """
        with self._lock:
            if self._destroyed:
                raise SecureMemoryError("Buffer detruit")
            
            if len(data) > self.size:
                raise ValueError(f"Donnees trop grandes ({len(data)} > {self.size})")
            
            # XOR avec le masque
            masked = bytes(d ^ m for d, m in zip(data, self._mask[:len(data)]))
            
            # Ecrire dans le buffer
            ctypes.memmove(self._buffer, masked, len(data))
            self._data_length = len(data)
    
    def read(self) -> bytes:
        """
        Lit et demasque les donnees.
        
        Returns:
            Donnees originales
        """
        with self._lock:
            if self._destroyed:
                raise SecureMemoryError("Buffer detruit")
            
            if self._data_length == 0:
                return b''
            
            # Lire le buffer
            masked = self._buffer.raw[:self._data_length]
            
            # Demasquer (XOR inverse)
            return bytes(d ^ m for d, m in zip(masked, self._mask[:self._data_length]))
    
    def rotate_mask(self) -> None:
        """
        Rotation du masque XOR.
        Appeler periodiquement pour protection contre cold boot.
        """
        with self._lock:
            if self._destroyed:
                return
            
            # Lire les donnees actuelles
            data = self.read()
            
            # Nouveau masque
            self._mask = bytearray(secrets.token_bytes(self.size))
            
            # Re-ecrire avec le nouveau masque
            if data:
                self.write(data)
            
            with SecureBuffer._stats_lock:
                SecureBuffer._global_stats.rotation_count += 1
    
    def secure_zero(self, method: SecureZeroMethod = SecureZeroMethod.DOD_3) -> None:
        """
        Effacement securise multi-passes.
        
        Args:
            method: Methode d'effacement
        """
        with self._lock:
            patterns = self._get_wipe_patterns(method)
            
            for pattern in patterns:
                if isinstance(pattern, int):
                    # Pattern fixe
                    ctypes.memset(ctypes.addressof(self._buffer), pattern, self.size)
                else:
                    # Pattern aleatoire
                    random_data = secrets.token_bytes(self.size)
                    ctypes.memmove(self._buffer, random_data, self.size)
            
            # Final: zeros
            ctypes.memset(ctypes.addressof(self._buffer), 0, self.size)
            
            # Effacer aussi le masque
            for i in range(len(self._mask)):
                self._mask[i] = 0
            
            self._data_length = 0
    
    def _get_wipe_patterns(self, method: SecureZeroMethod) -> list:
        """Retourne les patterns d'effacement selon la methode"""
        if method == SecureZeroMethod.SIMPLE:
            return [0]
        elif method == SecureZeroMethod.DOD_3:
            return [0x00, 0xFF, 'random']
        elif method == SecureZeroMethod.DOD_7:
            return [0x00, 0xFF, 'random', 0x00, 0xFF, 'random', 'random']
        elif method == SecureZeroMethod.GUTMANN:
            # Simplified Gutmann (selection de patterns)
            patterns = []
            for i in range(35):
                if i < 4 or i >= 31:
                    patterns.append('random')
                else:
                    patterns.append((i * 7) % 256)
            return patterns
        return [0]
    
    def _cleanup(self):
        """Nettoyage a la sortie"""
        if not self._destroyed:
            self.destroy()
    
    def destroy(self) -> None:
        """Destruction securisee du buffer"""
        with self._lock:
            if self._destroyed:
                return
            
            # Arreter le timer
            if self._rotation_timer:
                self._rotation_timer.cancel()
            
            # Effacement securise
            self.secure_zero(SecureZeroMethod.DOD_3)
            
            # Deverrouiller
            self._unlock_memory()
            
            self._destroyed = True
            
            # Stats
            with SecureBuffer._stats_lock:
                SecureBuffer._global_stats.total_freed += self.size
                SecureBuffer._global_stats.active_buffers -= 1
    
    @property
    def is_locked(self) -> bool:
        """True si la memoire est verrouillee (pas de swap)"""
        return self._locked
    
    @classmethod
    def get_stats(cls) -> MemoryStats:
        """Retourne les statistiques globales"""
        with cls._stats_lock:
            return MemoryStats(
                total_allocated=cls._global_stats.total_allocated,
                total_freed=cls._global_stats.total_freed,
                active_buffers=cls._global_stats.active_buffers,
                locked_bytes=cls._global_stats.locked_bytes,
                rotation_count=cls._global_stats.rotation_count
            )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy()
        return False
    
    def __del__(self):
        self._cleanup()


class SecureKeyStorage:
    """
    Stockage securise de multiples cles.
    
    Usage:
        storage = SecureKeyStorage()
        storage.store("master_key", master_key_bytes)
        key = storage.retrieve("master_key")
        storage.destroy_all()
    """
    
    def __init__(self, default_key_size: int = 32):
        self._keys: dict[str, SecureBuffer] = {}
        self._default_size = default_key_size
        self._lock = threading.RLock()
    
    def store(self, key_id: str, data: bytes) -> None:
        """Stocke une cle de maniere securisee"""
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].destroy()
            
            buf = SecureBuffer(max(len(data), self._default_size))
            buf.write(data)
            self._keys[key_id] = buf
    
    def retrieve(self, key_id: str) -> Optional[bytes]:
        """Recupere une cle"""
        with self._lock:
            if key_id not in self._keys:
                return None
            return self._keys[key_id].read()
    
    def delete(self, key_id: str) -> bool:
        """Supprime une cle de maniere securisee"""
        with self._lock:
            if key_id not in self._keys:
                return False
            self._keys[key_id].destroy()
            del self._keys[key_id]
            return True
    
    def destroy_all(self) -> None:
        """Detruit toutes les cles"""
        with self._lock:
            for buf in self._keys.values():
                buf.destroy()
            self._keys.clear()
    
    def __contains__(self, key_id: str) -> bool:
        return key_id in self._keys
    
    def __del__(self):
        self.destroy_all()
