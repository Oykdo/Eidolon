"""
Eidolon Daemon Service
Background service managing API server and vault operations.
"""

import os
import sys
import signal
import threading
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import get_data_root, get_keys_dir

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("eidolon.daemon")


@dataclass
class DaemonConfig:
    host: str = "127.0.0.1"
    port: int = 8420
    pid_file: str = ""
    log_file: str = ""
    data_dir: str = ""
    
    def __post_init__(self):
        data_root = get_data_root()
        if not self.pid_file:
            self.pid_file = str(data_root / "daemon" / "eidolon.pid")
        if not self.log_file:
            self.log_file = str(data_root / "daemon" / "eidolon.log")
        if not self.data_dir:
            self.data_dir = str(data_root)


@dataclass
class DaemonStatus:
    running: bool
    pid: Optional[int]
    uptime_seconds: Optional[float]
    api_url: Optional[str]
    vaults_registered: int
    version: str


class EidolonDaemon:
    """Background daemon for Eidolon ecosystem."""
    
    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or DaemonConfig()
        self._server_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._start_time: Optional[float] = None
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Ensure daemon directories exist."""
        Path(self.config.pid_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self.config.log_file).parent.mkdir(parents=True, exist_ok=True)
    
    def _write_pid(self):
        """Write PID file."""
        with open(self.config.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def _remove_pid(self):
        """Remove PID file."""
        try:
            os.remove(self.config.pid_file)
        except FileNotFoundError:
            pass
    
    def _read_pid(self) -> Optional[int]:
        """Read PID from file."""
        try:
            with open(self.config.pid_file, 'r') as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return None
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running."""
        if sys.platform == 'win32':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    
    def _run_api_server(self):
        """Run the API server in a thread."""
        try:
            import uvicorn
            from src.api.server import create_app
            
            app = create_app()
            
            config = uvicorn.Config(
                app,
                host=self.config.host,
                port=self.config.port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)
            
            while not self._shutdown_event.is_set():
                server.run()
                break
                
        except Exception as e:
            logger.error(f"API server error: {e}")
    
    def start(self, foreground: bool = False) -> bool:
        """
        Start the daemon.
        
        Args:
            foreground: Run in foreground (blocking) instead of background
            
        Returns:
            True if started successfully
        """
        existing_pid = self._read_pid()
        if existing_pid and self._is_process_running(existing_pid):
            logger.warning(f"Daemon already running (PID {existing_pid})")
            return False
        
        logger.info("Starting Eidolon daemon...")
        self._start_time = time.time()
        self._write_pid()
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self._server_thread = threading.Thread(target=self._run_api_server, daemon=True)
        self._server_thread.start()
        
        time.sleep(0.5)
        
        if self._server_thread.is_alive():
            logger.info(f"Daemon started on http://{self.config.host}:{self.config.port}")
            
            if foreground:
                try:
                    while not self._shutdown_event.is_set():
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
                finally:
                    self.stop()
            
            return True
        else:
            logger.error("Failed to start API server")
            self._remove_pid()
            return False
    
    def stop(self) -> bool:
        """Stop the daemon."""
        logger.info("Stopping Eidolon daemon...")
        self._shutdown_event.set()
        
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5)
        
        self._remove_pid()
        logger.info("Daemon stopped")
        return True
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.stop()
        sys.exit(0)
    
    def status(self) -> DaemonStatus:
        """Get daemon status."""
        pid = self._read_pid()
        running = pid is not None and self._is_process_running(pid)
        
        vaults_count = 0
        try:
            from src.identity.vault_identity import VaultIdentityManager
            manager = VaultIdentityManager()
            vaults_count = len(manager.list_vaults())
        except Exception:
            pass
        
        uptime = None
        if running and self._start_time:
            uptime = time.time() - self._start_time
        
        return DaemonStatus(
            running=running,
            pid=pid if running else None,
            uptime_seconds=uptime,
            api_url=f"http://{self.config.host}:{self.config.port}" if running else None,
            vaults_registered=vaults_count,
            version="1.0.0"
        )


def get_daemon(config: Optional[DaemonConfig] = None) -> EidolonDaemon:
    """Get daemon instance."""
    return EidolonDaemon(config)
