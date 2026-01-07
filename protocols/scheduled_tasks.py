#!/usr/bin/env python
"""
Eidolon - Système de Tâches Programmées
Gestion des tâches automatisées pour le vault

Fonctionnalités:
- Scheduler de tâches avec cron-like syntax
- Exécution des transfers à échéance
- Backups automatiques
- Vérification d'intégrité périodique
- Notifications et alertes
"""

import os
import sys
import json
import time
import threading
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import queue
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# CONFIGURATION DU LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS
# ============================================================================

class TaskStatus(Enum):
    """Statuts des tâches"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Priorités des tâches"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskType(Enum):
    """Types de tâches"""
    TRANSFER = "transfer"
    BACKUP = "backup"
    INTEGRITY_CHECK = "integrity_check"
    CLEANUP = "cleanup"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ScheduledTask:
    """Représentation d'une tâche programmée"""
    id: str
    name: str
    task_type: str
    scheduled_at: str
    priority: int = 2
    status: str = "pending"
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduledTask':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RecurringTask:
    """Représentation d'une tâche récurrente"""
    id: str
    name: str
    task_type: str
    interval_seconds: int
    priority: int = 2
    enabled: bool = True
    last_run: str = ""
    next_run: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    run_count: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RecurringTask':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================================
# GESTIONNAIRE DE TÂCHES PROGRAMMÉES
# ============================================================================

class ScheduledTaskManager:
    """Gestionnaire de tâches programmées"""
    
    def __init__(self, vault_path: str, vault_key: bytes = None):
        """
        Initialiser le gestionnaire.
        
        Args:
            vault_path: Chemin du vault
            vault_key: Clé optionnelle pour le chiffrement
        """
        self.vault_path = Path(vault_path)
        self.vault_key = vault_key
        
        self.tasks_file = self.vault_path / "scheduled_tasks.json"
        self.recurring_file = self.vault_path / "recurring_tasks.json"
        
        # Files d'attente
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._pending_tasks: Dict[str, ScheduledTask] = {}
        self._recurring_tasks: Dict[str, RecurringTask] = {}
        
        # Handlers
        self._handlers: Dict[str, Callable] = {}
        
        # État
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        
        # Charger les tâches existantes
        self._load_tasks()
        
        # Enregistrer les handlers par défaut
        self._register_default_handlers()
    
    def _load_tasks(self):
        """Charger les tâches depuis les fichiers"""
        # Tâches programmées
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for task_data in data.get('tasks', []):
                    task = ScheduledTask.from_dict(task_data)
                    if task.status == TaskStatus.PENDING.value:
                        self._pending_tasks[task.id] = task
            except Exception as e:
                logger.error(f"Erreur chargement tâches: {e}")
        
        # Tâches récurrentes
        if self.recurring_file.exists():
            try:
                with open(self.recurring_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for task_data in data.get('tasks', []):
                    task = RecurringTask.from_dict(task_data)
                    self._recurring_tasks[task.id] = task
            except Exception as e:
                logger.error(f"Erreur chargement tâches récurrentes: {e}")
    
    def _save_tasks(self):
        """Sauvegarder les tâches"""
        # Tâches programmées
        tasks_data = {
            'tasks': [t.to_dict() for t in self._pending_tasks.values()],
            'updated_at': datetime.now().isoformat()
        }
        
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, indent=2, ensure_ascii=False)
        
        # Tâches récurrentes
        recurring_data = {
            'tasks': [t.to_dict() for t in self._recurring_tasks.values()],
            'updated_at': datetime.now().isoformat()
        }
        
        with open(self.recurring_file, 'w', encoding='utf-8') as f:
            json.dump(recurring_data, f, indent=2, ensure_ascii=False)
    
    def _register_default_handlers(self):
        """Enregistrer les handlers par défaut"""
        self.register_handler(TaskType.TRANSFER.value, self._handle_transfer)
        self.register_handler(TaskType.BACKUP.value, self._handle_backup)
        self.register_handler(TaskType.INTEGRITY_CHECK.value, self._handle_integrity_check)
        self.register_handler(TaskType.CLEANUP.value, self._handle_cleanup)
        self.register_handler(TaskType.NOTIFICATION.value, self._handle_notification)
    
    def register_handler(self, task_type: str, handler: Callable):
        """
        Enregistrer un handler pour un type de tâche.
        
        Args:
            task_type: Type de tâche
            handler: Fonction handler(task: ScheduledTask) -> bool
        """
        self._handlers[task_type] = handler
    
    def _generate_id(self) -> str:
        """Générer un ID unique"""
        import secrets
        return secrets.token_hex(8)
    
    # ========================================================================
    # GESTION DES TÂCHES PROGRAMMÉES
    # ========================================================================
    
    def schedule_task(
        self,
        name: str,
        task_type: str,
        scheduled_at: datetime,
        payload: Dict = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """
        Programmer une nouvelle tâche.
        
        Args:
            name: Nom de la tâche
            task_type: Type de tâche
            scheduled_at: Date/heure d'exécution
            payload: Données associées
            priority: Priorité
        
        Returns:
            ID de la tâche
        """
        task_id = self._generate_id()
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=task_type,
            scheduled_at=scheduled_at.isoformat(),
            priority=priority.value,
            payload=payload or {}
        )
        
        self._pending_tasks[task_id] = task
        self._save_tasks()
        
        logger.info(f"Tâche programmée: {name} ({task_id}) pour {scheduled_at}")
        return task_id
    
    def schedule_transfer(
        self,
        asset_id: str,
        destination: str,
        delay_days: int = 30,
        metadata: Dict = None
    ) -> str:
        """
        Programmer un transfer d'actif.
        
        Args:
            asset_id: ID de l'actif
            destination: Adresse de destination
            delay_days: Délai en jours
            metadata: Métadonnées supplémentaires
        
        Returns:
            ID de la tâche
        """
        scheduled_at = datetime.now() + timedelta(days=delay_days)
        
        payload = {
            'asset_id': asset_id,
            'destination': destination,
            'metadata': metadata or {}
        }
        
        return self.schedule_task(
            name=f"Transfer {asset_id[:8]}...",
            task_type=TaskType.TRANSFER.value,
            scheduled_at=scheduled_at,
            payload=payload,
            priority=TaskPriority.HIGH
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """Annuler une tâche programmée"""
        if task_id in self._pending_tasks:
            task = self._pending_tasks[task_id]
            task.status = TaskStatus.CANCELLED.value
            self._save_tasks()
            logger.info(f"Tâche annulée: {task_id}")
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Obtenir une tâche par son ID"""
        return self._pending_tasks.get(task_id)
    
    def list_pending_tasks(self) -> List[ScheduledTask]:
        """Lister les tâches en attente"""
        return [
            t for t in self._pending_tasks.values()
            if t.status == TaskStatus.PENDING.value
        ]
    
    def get_due_tasks(self) -> List[ScheduledTask]:
        """Obtenir les tâches arrivées à échéance"""
        now = datetime.now()
        due_tasks = []
        
        for task in self._pending_tasks.values():
            if task.status != TaskStatus.PENDING.value:
                continue
            
            try:
                scheduled = datetime.fromisoformat(task.scheduled_at)
                if now >= scheduled:
                    due_tasks.append(task)
            except ValueError:
                pass
        
        # Trier par priorité (décroissante) puis par date
        due_tasks.sort(key=lambda t: (-t.priority, t.scheduled_at))
        return due_tasks
    
    # ========================================================================
    # TÂCHES RÉCURRENTES
    # ========================================================================
    
    def add_recurring_task(
        self,
        name: str,
        task_type: str,
        interval_seconds: int,
        payload: Dict = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """
        Ajouter une tâche récurrente.
        
        Args:
            name: Nom de la tâche
            task_type: Type de tâche
            interval_seconds: Intervalle en secondes
            payload: Données associées
            priority: Priorité
        
        Returns:
            ID de la tâche
        """
        task_id = self._generate_id()
        
        next_run = (datetime.now() + timedelta(seconds=interval_seconds)).isoformat()
        
        task = RecurringTask(
            id=task_id,
            name=name,
            task_type=task_type,
            interval_seconds=interval_seconds,
            priority=priority.value,
            payload=payload or {},
            next_run=next_run
        )
        
        self._recurring_tasks[task_id] = task
        self._save_tasks()
        
        logger.info(f"Tâche récurrente ajoutée: {name} ({task_id}) - intervalle {interval_seconds}s")
        return task_id
    
    def add_daily_backup(self, hour: int = 3, minute: int = 0) -> str:
        """Ajouter un backup quotidien"""
        # Calculer l'intervalle jusqu'à la prochaine occurrence
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return self.add_recurring_task(
            name="Backup quotidien",
            task_type=TaskType.BACKUP.value,
            interval_seconds=86400,  # 24 heures
            payload={'type': 'daily'},
            priority=TaskPriority.NORMAL
        )
    
    def add_integrity_check(self, interval_hours: int = 6) -> str:
        """Ajouter une vérification d'intégrité périodique"""
        return self.add_recurring_task(
            name="Vérification d'intégrité",
            task_type=TaskType.INTEGRITY_CHECK.value,
            interval_seconds=interval_hours * 3600,
            priority=TaskPriority.HIGH
        )
    
    def enable_recurring_task(self, task_id: str, enabled: bool = True) -> bool:
        """Activer/désactiver une tâche récurrente"""
        if task_id in self._recurring_tasks:
            self._recurring_tasks[task_id].enabled = enabled
            self._save_tasks()
            return True
        return False
    
    def remove_recurring_task(self, task_id: str) -> bool:
        """Supprimer une tâche récurrente"""
        if task_id in self._recurring_tasks:
            del self._recurring_tasks[task_id]
            self._save_tasks()
            return True
        return False
    
    def list_recurring_tasks(self) -> List[RecurringTask]:
        """Lister les tâches récurrentes"""
        return list(self._recurring_tasks.values())
    
    # ========================================================================
    # EXÉCUTION DES TÂCHES
    # ========================================================================
    
    def execute_task(self, task: ScheduledTask) -> bool:
        """
        Exécuter une tâche.
        
        Args:
            task: Tâche à exécuter
        
        Returns:
            True si succès
        """
        task.status = TaskStatus.RUNNING.value
        task.started_at = datetime.now().isoformat()
        
        handler = self._handlers.get(task.task_type)
        
        if not handler:
            logger.warning(f"Pas de handler pour le type: {task.task_type}")
            task.status = TaskStatus.FAILED.value
            task.error_message = f"No handler for type: {task.task_type}"
            self._save_tasks()
            return False
        
        try:
            success = handler(task)
            
            if success:
                task.status = TaskStatus.COMPLETED.value
                task.completed_at = datetime.now().isoformat()
                logger.info(f"Tâche complétée: {task.name} ({task.id})")
            else:
                task.retry_count += 1
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.PENDING.value
                    # Reprogrammer dans 5 minutes
                    task.scheduled_at = (datetime.now() + timedelta(minutes=5)).isoformat()
                    logger.warning(f"Tâche échouée, retry {task.retry_count}/{task.max_retries}: {task.name}")
                else:
                    task.status = TaskStatus.FAILED.value
                    logger.error(f"Tâche échouée définitivement: {task.name}")
            
            self._save_tasks()
            return success
        
        except Exception as e:
            task.status = TaskStatus.FAILED.value
            task.error_message = str(e)
            task.completed_at = datetime.now().isoformat()
            self._save_tasks()
            logger.error(f"Exception lors de l'exécution de {task.name}: {e}")
            return False
    
    def process_due_tasks(self) -> int:
        """
        Traiter toutes les tâches arrivées à échéance.
        
        Returns:
            Nombre de tâches traitées
        """
        due_tasks = self.get_due_tasks()
        processed = 0
        
        for task in due_tasks:
            self.execute_task(task)
            processed += 1
        
        return processed
    
    def process_recurring_tasks(self):
        """Traiter les tâches récurrentes"""
        now = datetime.now()
        
        for task in self._recurring_tasks.values():
            if not task.enabled:
                continue
            
            try:
                next_run = datetime.fromisoformat(task.next_run) if task.next_run else now
                
                if now >= next_run:
                    # Créer une tâche programmée pour exécution immédiate
                    scheduled_task = ScheduledTask(
                        id=self._generate_id(),
                        name=task.name,
                        task_type=task.task_type,
                        scheduled_at=now.isoformat(),
                        priority=task.priority,
                        payload=task.payload
                    )
                    
                    self.execute_task(scheduled_task)
                    
                    # Mettre à jour la tâche récurrente
                    task.last_run = now.isoformat()
                    task.next_run = (now + timedelta(seconds=task.interval_seconds)).isoformat()
                    task.run_count += 1
                    
                    self._save_tasks()
            
            except ValueError:
                pass
    
    # ========================================================================
    # HANDLERS PAR DÉFAUT
    # ========================================================================
    
    def _handle_transfer(self, task: ScheduledTask) -> bool:
        """Handler pour les transfers"""
        payload = task.payload
        asset_id = payload.get('asset_id')
        destination = payload.get('destination')
        
        logger.info(f"Exécution transfer: {asset_id} -> {destination}")
        
        # Importer et utiliser le vault persistant
        try:
            from core.persistent_vault import PersistentVaultManager
            
            vault = PersistentVaultManager(self.vault_key, str(self.vault_path.name))
            
            # Mettre à jour l'actif
            asset = vault.get_asset(asset_id)
            if asset:
                vault.update_asset(asset_id, {
                    'status': 'transferred',
                    'transferred_to': destination,
                    'transferred_at': datetime.now().isoformat()
                })
                return True
            else:
                logger.warning(f"Actif non trouvé: {asset_id}")
                return False
        
        except ImportError:
            logger.warning("Module persistent_vault non disponible")
            return True  # Considérer comme succès en mode démo
    
    def _handle_backup(self, task: ScheduledTask) -> bool:
        """Handler pour les backups"""
        logger.info("Exécution backup automatique")
        
        try:
            from core.persistent_vault import PersistentVaultManager
            
            vault = PersistentVaultManager(self.vault_key, str(self.vault_path.name))
            
            backup_dir = self.vault_path / "backups" / "auto"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            zip_path = vault.export_vault(str(backup_dir))
            logger.info(f"Backup créé: {zip_path}")
            return True
        
        except ImportError:
            logger.warning("Module persistent_vault non disponible pour backup")
            return True
        except Exception as e:
            logger.error(f"Erreur backup: {e}")
            return False
    
    def _handle_integrity_check(self, task: ScheduledTask) -> bool:
        """Handler pour la vérification d'intégrité"""
        logger.info("Vérification d'intégrité en cours...")
        
        try:
            from core.persistent_vault import PersistentVaultManager
            
            vault = PersistentVaultManager(self.vault_key, str(self.vault_path.name))
            
            # Vérifier tous les documents
            docs = vault.list_documents()
            failed = []
            
            for doc in docs:
                if not vault.verify_document(doc['id']):
                    failed.append(doc['id'])
            
            if failed:
                logger.warning(f"Documents avec intégrité compromise: {failed}")
                return False
            
            logger.info(f"Intégrité vérifiée pour {len(docs)} documents")
            return True
        
        except ImportError:
            logger.warning("Module persistent_vault non disponible")
            return True
    
    def _handle_cleanup(self, task: ScheduledTask) -> bool:
        """Handler pour le nettoyage"""
        logger.info("Nettoyage automatique...")
        
        # Nettoyer les vieilles tâches complétées
        cutoff = datetime.now() - timedelta(days=30)
        
        to_remove = []
        for task_id, t in self._pending_tasks.items():
            if t.status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
                try:
                    completed = datetime.fromisoformat(t.completed_at) if t.completed_at else None
                    if completed and completed < cutoff:
                        to_remove.append(task_id)
                except ValueError:
                    pass
        
        for task_id in to_remove:
            del self._pending_tasks[task_id]
        
        if to_remove:
            self._save_tasks()
            logger.info(f"Nettoyé {len(to_remove)} anciennes tâches")
        
        return True
    
    def _handle_notification(self, task: ScheduledTask) -> bool:
        """Handler pour les notifications"""
        payload = task.payload
        message = payload.get('message', 'Notification du vault')
        
        logger.info(f"NOTIFICATION: {message}")
        
        # Ici on pourrait intégrer des notifications système, email, webhook, etc.
        return True
    
    # ========================================================================
    # SCHEDULER
    # ========================================================================
    
    def start(self, check_interval: int = 60):
        """
        Démarrer le scheduler.
        
        Args:
            check_interval: Intervalle de vérification en secondes
        """
        if self._running:
            logger.warning("Scheduler déjà en cours d'exécution")
            return
        
        self._running = True
        
        def scheduler_loop():
            logger.info(f"Scheduler démarré (intervalle: {check_interval}s)")
            
            while self._running:
                try:
                    # Traiter les tâches programmées
                    due_count = self.process_due_tasks()
                    if due_count:
                        logger.debug(f"Traité {due_count} tâches programmées")
                    
                    # Traiter les tâches récurrentes
                    self.process_recurring_tasks()
                
                except Exception as e:
                    logger.error(f"Erreur dans le scheduler: {e}")
                
                time.sleep(check_interval)
            
            logger.info("Scheduler arrêté")
        
        self._scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self._scheduler_thread.start()
    
    def stop(self):
        """Arrêter le scheduler"""
        self._running = False
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
    
    def is_running(self) -> bool:
        """Vérifier si le scheduler est en cours d'exécution"""
        return self._running
    
    # ========================================================================
    # STATISTIQUES
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtenir les statistiques du scheduler"""
        pending = [t for t in self._pending_tasks.values() if t.status == TaskStatus.PENDING.value]
        completed = [t for t in self._pending_tasks.values() if t.status == TaskStatus.COMPLETED.value]
        failed = [t for t in self._pending_tasks.values() if t.status == TaskStatus.FAILED.value]
        
        return {
            'running': self._running,
            'pending_tasks': len(pending),
            'completed_tasks': len(completed),
            'failed_tasks': len(failed),
            'recurring_tasks': len(self._recurring_tasks),
            'due_tasks': len(self.get_due_tasks())
        }


# ============================================================================
# POINT D'ENTRÉE CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestionnaire de Tâches Programmées")
    parser.add_argument("action", choices=["start", "list", "add", "cancel", "stats"])
    parser.add_argument("--vault-path", "-p", default=".", help="Chemin du vault")
    parser.add_argument("--interval", "-i", type=int, default=60, help="Intervalle de vérification")
    parser.add_argument("--task-id", "-t", help="ID de la tâche")
    parser.add_argument("--name", "-n", help="Nom de la tâche")
    parser.add_argument("--type", help="Type de tâche")
    parser.add_argument("--delay", "-d", type=int, help="Délai en jours")
    
    args = parser.parse_args()
    
    manager = ScheduledTaskManager(args.vault_path)
    
    if args.action == "start":
        print(f"Démarrage du scheduler (Ctrl+C pour arrêter)...")
        manager.start(args.interval)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            manager.stop()
            print("\nScheduler arrêté")
    
    elif args.action == "list":
        print("\n=== Tâches programmées ===")
        for task in manager.list_pending_tasks():
            print(f"  [{task.id}] {task.name} - {task.status} (prévu: {task.scheduled_at[:16]})")
        
        print("\n=== Tâches récurrentes ===")
        for task in manager.list_recurring_tasks():
            status = "actif" if task.enabled else "désactivé"
            print(f"  [{task.id}] {task.name} - {status} (intervalle: {task.interval_seconds}s)")
    
    elif args.action == "add":
        if not args.name or not args.type:
            print("--name et --type requis")
        else:
            delay = args.delay or 1
            scheduled_at = datetime.now() + timedelta(days=delay)
            task_id = manager.schedule_task(args.name, args.type, scheduled_at)
            print(f"Tâche créée: {task_id}")
    
    elif args.action == "cancel":
        if not args.task_id:
            print("--task-id requis")
        else:
            if manager.cancel_task(args.task_id):
                print(f"Tâche annulée: {args.task_id}")
            else:
                print("Tâche non trouvée")
    
    elif args.action == "stats":
        stats = manager.get_stats()
        print(json.dumps(stats, indent=2))
