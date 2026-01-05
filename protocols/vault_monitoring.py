"""
Système de Monitoring Complet pour Vault NFT/Objets Fixes
Surveillance temps réel, alertes, métriques et notifications

Fonctionnalités:
- Monitoring temps réel des vaults et sceaux
- Système d'alertes configurable
- Métriques exportables (Prometheus-compatible)
- Webhooks et notifications
- Historique des événements NFT
- API de monitoring
"""

import hashlib
import json
import time
import threading
import queue
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import secrets


class AlertSeverity(Enum):
    """Niveaux de sévérité des alertes"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(Enum):
    """Types d'événements monitored"""
    # Vault events
    VAULT_ACCESS = "vault_access"
    VAULT_ACCESS_DENIED = "vault_access_denied"
    VAULT_KEY_CREATED = "vault_key_created"
    VAULT_KEY_ROTATED = "vault_key_rotated"
    VAULT_KEY_REVOKED = "vault_key_revoked"
    
    # NFT/Document events
    NFT_MINTED = "nft_minted"
    NFT_TRANSFERRED = "nft_transferred"
    NFT_LOCKED = "nft_locked"
    NFT_UNLOCKED = "nft_unlocked"
    DOCUMENT_ESCROWED = "document_escrowed"
    DOCUMENT_RETRIEVED = "document_retrieved"
    
    # Seal events
    SEAL_CREATED = "seal_created"
    SEAL_VERIFIED = "seal_verified"
    SEAL_COMPROMISED = "seal_compromised"
    SEAL_EXPIRED = "seal_expired"
    
    # Security events
    SECURITY_BREACH_ATTEMPT = "security_breach_attempt"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"
    AUTHORITY_ROTATION = "authority_rotation"
    EMERGENCY_ACCESS = "emergency_access"
    
    # System events
    SYSTEM_HEALTH_CHECK = "system_health_check"
    SYSTEM_ERROR = "system_error"


@dataclass
class MonitoringEvent:
    """Événement de monitoring"""
    event_id: str
    event_type: EventType
    timestamp: str
    severity: AlertSeverity
    source: str
    user_id: Optional[str]
    resource_id: Optional[str]
    details: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp,
            'severity': self.severity.value,
            'source': self.source,
            'user_id': self.user_id,
            'resource_id': self.resource_id,
            'details': self.details,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class Alert:
    """Alerte générée par le système"""
    alert_id: str
    severity: AlertSeverity
    title: str
    message: str
    source_event: MonitoringEvent
    created_at: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'source_event_id': self.source_event.event_id,
            'created_at': self.created_at,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }


@dataclass
class MetricPoint:
    """Point de métrique"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_prometheus(self) -> str:
        """Format Prometheus"""
        labels_str = ','.join(f'{k}="{v}"' for k, v in self.labels.items())
        if labels_str:
            return f'{self.name}{{{labels_str}}} {self.value} {int(self.timestamp * 1000)}'
        return f'{self.name} {self.value} {int(self.timestamp * 1000)}'


@dataclass
class NFTRecord:
    """Enregistrement d'un NFT/objet fixe"""
    nft_id: str
    document_hash: str
    owner_id: str
    created_at: str
    seal_id: Optional[str]
    vault_id: Optional[str]
    status: str  # "active", "locked", "transferred", "burned"
    transfer_history: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertRule:
    """Règle d'alerte configurable"""
    
    def __init__(self, rule_id: str, name: str,
                 event_types: List[EventType],
                 condition: Callable[[MonitoringEvent], bool],
                 severity: AlertSeverity,
                 title_template: str,
                 message_template: str,
                 cooldown_seconds: int = 60):
        self.rule_id = rule_id
        self.name = name
        self.event_types = event_types
        self.condition = condition
        self.severity = severity
        self.title_template = title_template
        self.message_template = message_template
        self.cooldown_seconds = cooldown_seconds
        self.last_triggered: Dict[str, float] = {}
    
    def evaluate(self, event: MonitoringEvent) -> Optional[Alert]:
        """Évalue la règle et génère une alerte si nécessaire"""
        if event.event_type not in self.event_types:
            return None
        
        if not self.condition(event):
            return None
        
        # Vérifier le cooldown
        cooldown_key = f"{event.resource_id or 'global'}"
        last_time = self.last_triggered.get(cooldown_key, 0)
        now = time.time()
        
        if now - last_time < self.cooldown_seconds:
            return None
        
        self.last_triggered[cooldown_key] = now
        
        # Générer l'alerte
        title = self.title_template.format(
            event_type=event.event_type.value,
            user_id=event.user_id or 'unknown',
            resource_id=event.resource_id or 'unknown'
        )
        
        message = self.message_template.format(
            **event.details,
            timestamp=event.timestamp,
            source=event.source
        )
        
        return Alert(
            alert_id=secrets.token_hex(16),
            severity=self.severity,
            title=title,
            message=message,
            source_event=event,
            created_at=datetime.utcnow().isoformat()
        )


class WebhookNotifier:
    """Notificateur par webhook"""
    
    def __init__(self):
        self.webhooks: Dict[str, Dict] = {}
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def register_webhook(self, webhook_id: str, url: str,
                         events: List[EventType] = None,
                         min_severity: AlertSeverity = AlertSeverity.INFO,
                         headers: Dict[str, str] = None):
        """Enregistre un webhook"""
        self.webhooks[webhook_id] = {
            'url': url,
            'events': events,  # None = tous les événements
            'min_severity': min_severity,
            'headers': headers or {},
            'enabled': True,
            'failure_count': 0
        }
    
    def unregister_webhook(self, webhook_id: str):
        """Supprime un webhook"""
        self.webhooks.pop(webhook_id, None)
    
    def notify(self, event: MonitoringEvent):
        """Ajoute une notification à la queue"""
        self._queue.put(event)
    
    def notify_alert(self, alert: Alert):
        """Notifie une alerte"""
        # Convertir l'alerte en événement pour la queue
        self._queue.put(('alert', alert))
    
    def start(self):
        """Démarre le worker de notification"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()
    
    def stop(self):
        """Arrête le worker"""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
    
    def _worker(self):
        """Worker de notification"""
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=1)
                self._send_notifications(item)
            except queue.Empty:
                continue
    
    def _send_notifications(self, item):
        """Envoie les notifications aux webhooks"""
        if isinstance(item, tuple) and item[0] == 'alert':
            payload = {'type': 'alert', 'data': item[1].to_dict()}
            severity = item[1].severity
        else:
            payload = {'type': 'event', 'data': item.to_dict()}
            severity = item.severity
        
        for webhook_id, webhook in self.webhooks.items():
            if not webhook['enabled']:
                continue
            
            # Vérifier la sévérité minimale
            severity_order = [AlertSeverity.INFO, AlertSeverity.WARNING, 
                           AlertSeverity.ERROR, AlertSeverity.CRITICAL]
            if severity_order.index(severity) < severity_order.index(webhook['min_severity']):
                continue
            
            # Vérifier le filtre d'événements
            if webhook['events'] is not None:
                if isinstance(item, MonitoringEvent) and item.event_type not in webhook['events']:
                    continue
            
            # Simuler l'envoi (en production, utiliser requests)
            self._simulate_send(webhook_id, webhook['url'], payload)
    
    def _simulate_send(self, webhook_id: str, url: str, payload: Dict):
        """Simule l'envoi d'un webhook (à remplacer par requests en production)"""
        # En production:
        # response = requests.post(url, json=payload, headers=webhook['headers'])
        print(f"[WEBHOOK {webhook_id}] -> {url}: {payload['type']}")


class MetricsCollector:
    """Collecteur de métriques"""
    
    def __init__(self, retention_hours: int = 24):
        self._metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._retention_seconds = retention_hours * 3600
        self._lock = threading.Lock()
    
    def increment_counter(self, name: str, value: float = 1.0,
                         labels: Dict[str, str] = None):
        """Incrémente un compteur"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value
            self._record_metric(name, self._counters[key], labels)
    
    def set_gauge(self, name: str, value: float,
                  labels: Dict[str, str] = None):
        """Définit une jauge"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            self._record_metric(name, value, labels)
    
    def observe_histogram(self, name: str, value: float,
                         labels: Dict[str, str] = None):
        """Observe une valeur pour un histogramme"""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            # Garder les 1000 dernières valeurs
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Crée une clé unique pour une métrique"""
        if labels:
            labels_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
            return f'{name}{{{labels_str}}}'
        return name
    
    def _record_metric(self, name: str, value: float,
                       labels: Dict[str, str] = None):
        """Enregistre un point de métrique"""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            labels=labels or {}
        )
        self._metrics[name].append(point)
        self._cleanup_old_metrics(name)
    
    def _cleanup_old_metrics(self, name: str):
        """Nettoie les métriques anciennes"""
        cutoff = time.time() - self._retention_seconds
        self._metrics[name] = [
            m for m in self._metrics[name] if m.timestamp > cutoff
        ]
    
    def get_metrics_prometheus(self) -> str:
        """Exporte les métriques au format Prometheus"""
        lines = []
        
        with self._lock:
            # Compteurs
            for key, value in self._counters.items():
                lines.append(f'{key} {value}')
            
            # Jauges
            for key, value in self._gauges.items():
                lines.append(f'{key} {value}')
            
            # Histogrammes (statistiques de base)
            for key, values in self._histograms.items():
                if values:
                    lines.append(f'{key}_count {len(values)}')
                    lines.append(f'{key}_sum {sum(values)}')
                    lines.append(f'{key}_avg {sum(values)/len(values)}')
        
        return '\n'.join(lines)
    
    def get_metric_history(self, name: str, 
                          since_hours: float = 1) -> List[Dict]:
        """Récupère l'historique d'une métrique"""
        cutoff = time.time() - since_hours * 3600
        with self._lock:
            return [
                {'value': m.value, 'timestamp': m.timestamp, 'labels': m.labels}
                for m in self._metrics.get(name, [])
                if m.timestamp > cutoff
            ]


class NFTRegistry:
    """Registre des NFT/objets fixes"""
    
    def __init__(self):
        self._nfts: Dict[str, NFTRecord] = {}
        self._by_owner: Dict[str, List[str]] = defaultdict(list)
        self._by_vault: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def register_nft(self, nft_id: str, document_hash: str,
                     owner_id: str, seal_id: str = None,
                     vault_id: str = None,
                     metadata: Dict = None) -> NFTRecord:
        """Enregistre un nouveau NFT"""
        with self._lock:
            record = NFTRecord(
                nft_id=nft_id,
                document_hash=document_hash,
                owner_id=owner_id,
                created_at=datetime.utcnow().isoformat(),
                seal_id=seal_id,
                vault_id=vault_id,
                status="active",
                metadata=metadata or {}
            )
            
            self._nfts[nft_id] = record
            self._by_owner[owner_id].append(nft_id)
            if vault_id:
                self._by_vault[vault_id].append(nft_id)
            
            return record
    
    def transfer_nft(self, nft_id: str, new_owner_id: str,
                     transfer_metadata: Dict = None) -> NFTRecord:
        """Transfère un NFT"""
        with self._lock:
            if nft_id not in self._nfts:
                raise ValueError(f"NFT {nft_id} non trouvé")
            
            record = self._nfts[nft_id]
            old_owner = record.owner_id
            
            # Mettre à jour les index
            self._by_owner[old_owner].remove(nft_id)
            self._by_owner[new_owner_id].append(nft_id)
            
            # Enregistrer le transfert
            record.transfer_history.append({
                'from': old_owner,
                'to': new_owner_id,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': transfer_metadata or {}
            })
            
            record.owner_id = new_owner_id
            return record
    
    def get_nft(self, nft_id: str) -> Optional[NFTRecord]:
        """Récupère un NFT"""
        return self._nfts.get(nft_id)
    
    def get_nfts_by_owner(self, owner_id: str) -> List[NFTRecord]:
        """Récupère les NFTs d'un propriétaire"""
        with self._lock:
            return [self._nfts[nft_id] for nft_id in self._by_owner.get(owner_id, [])]
    
    def get_nfts_by_vault(self, vault_id: str) -> List[NFTRecord]:
        """Récupère les NFTs d'un vault"""
        with self._lock:
            return [self._nfts[nft_id] for nft_id in self._by_vault.get(vault_id, [])]
    
    def lock_nft(self, nft_id: str) -> NFTRecord:
        """Verrouille un NFT"""
        with self._lock:
            if nft_id not in self._nfts:
                raise ValueError(f"NFT {nft_id} non trouvé")
            self._nfts[nft_id].status = "locked"
            return self._nfts[nft_id]
    
    def unlock_nft(self, nft_id: str) -> NFTRecord:
        """Déverrouille un NFT"""
        with self._lock:
            if nft_id not in self._nfts:
                raise ValueError(f"NFT {nft_id} non trouvé")
            self._nfts[nft_id].status = "active"
            return self._nfts[nft_id]


class VaultMonitoringSystem:
    """Système de monitoring complet pour le Vault NFT"""
    
    def __init__(self):
        self.events: List[MonitoringEvent] = []
        self.alerts: List[Alert] = []
        self.alert_rules: List[AlertRule] = []
        
        self.metrics = MetricsCollector()
        self.webhooks = WebhookNotifier()
        self.nft_registry = NFTRegistry()
        
        self._event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        
        # Initialiser les règles d'alerte par défaut
        self._setup_default_alert_rules()
        
        # Démarrer le worker de webhooks
        self.webhooks.start()
    
    def _setup_default_alert_rules(self):
        """Configure les règles d'alerte par défaut"""
        
        # Alerte sur accès refusé
        self.add_alert_rule(AlertRule(
            rule_id="access_denied",
            name="Accès Vault Refusé",
            event_types=[EventType.VAULT_ACCESS_DENIED],
            condition=lambda e: True,
            severity=AlertSeverity.WARNING,
            title_template="Accès refusé - {user_id}",
            message_template="Tentative d'accès refusée. Score: {match_score:.2%}",
            cooldown_seconds=30
        ))
        
        # Alerte sur tentative de breach
        self.add_alert_rule(AlertRule(
            rule_id="security_breach",
            name="Tentative de Breach Sécurité",
            event_types=[EventType.SECURITY_BREACH_ATTEMPT],
            condition=lambda e: True,
            severity=AlertSeverity.CRITICAL,
            title_template="ALERTE SÉCURITÉ - {resource_id}",
            message_template="Tentative de breach détectée depuis {source}",
            cooldown_seconds=0  # Toujours alerter
        ))
        
        # Alerte sur fingerprint mismatch répétés
        self.add_alert_rule(AlertRule(
            rule_id="fingerprint_mismatch",
            name="Mismatch Empreinte",
            event_types=[EventType.FINGERPRINT_MISMATCH],
            condition=lambda e: e.details.get('match_score', 1.0) < 0.5,
            severity=AlertSeverity.ERROR,
            title_template="Empreinte non reconnue - {user_id}",
            message_template="Score de correspondance très bas: {match_score:.2%}",
            cooldown_seconds=60
        ))
        
        # Alerte sur sceau compromis
        self.add_alert_rule(AlertRule(
            rule_id="seal_compromised",
            name="Sceau Compromis",
            event_types=[EventType.SEAL_COMPROMISED],
            condition=lambda e: True,
            severity=AlertSeverity.CRITICAL,
            title_template="SCEAU COMPROMIS - {resource_id}",
            message_template="Intégrité du sceau compromise. Action immédiate requise.",
            cooldown_seconds=0
        ))
        
        # Alerte sur accès d'urgence
        self.add_alert_rule(AlertRule(
            rule_id="emergency_access",
            name="Accès d'Urgence",
            event_types=[EventType.EMERGENCY_ACCESS],
            condition=lambda e: True,
            severity=AlertSeverity.WARNING,
            title_template="Accès d'urgence activé - {user_id}",
            message_template="Procédure d'urgence initiée. Vérifier la légitimité.",
            cooldown_seconds=0
        ))
    
    def add_alert_rule(self, rule: AlertRule):
        """Ajoute une règle d'alerte"""
        self.alert_rules.append(rule)
    
    def remove_alert_rule(self, rule_id: str):
        """Supprime une règle d'alerte"""
        self.alert_rules = [r for r in self.alert_rules if r.rule_id != rule_id]
    
    def register_event_handler(self, event_type: EventType,
                               handler: Callable[[MonitoringEvent], None]):
        """Enregistre un handler pour un type d'événement"""
        self._event_handlers[event_type].append(handler)
    
    def emit_event(self, event_type: EventType,
                   source: str,
                   details: Dict[str, Any],
                   user_id: str = None,
                   resource_id: str = None,
                   severity: AlertSeverity = AlertSeverity.INFO,
                   metadata: Dict = None) -> MonitoringEvent:
        """Émet un événement de monitoring"""
        
        event = MonitoringEvent(
            event_id=secrets.token_hex(16),
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            severity=severity,
            source=source,
            user_id=user_id,
            resource_id=resource_id,
            details=details,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.events.append(event)
            
            # Garder les 10000 derniers événements
            if len(self.events) > 10000:
                self.events = self.events[-10000:]
        
        # Mettre à jour les métriques
        self._update_metrics(event)
        
        # Évaluer les règles d'alerte
        self._evaluate_alert_rules(event)
        
        # Appeler les handlers
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                print(f"Erreur handler: {e}")
        
        # Notifier les webhooks
        self.webhooks.notify(event)
        
        return event
    
    def _update_metrics(self, event: MonitoringEvent):
        """Met à jour les métriques basées sur l'événement"""
        
        # Compteur d'événements par type
        self.metrics.increment_counter(
            'vault_events_total',
            labels={'event_type': event.event_type.value}
        )
        
        # Compteur par sévérité
        self.metrics.increment_counter(
            'vault_events_by_severity',
            labels={'severity': event.severity.value}
        )
        
        # Métriques spécifiques par type
        if event.event_type == EventType.VAULT_ACCESS:
            self.metrics.increment_counter('vault_access_total')
            if 'match_score' in event.details:
                self.metrics.observe_histogram(
                    'vault_access_match_score',
                    event.details['match_score']
                )
        
        elif event.event_type == EventType.VAULT_ACCESS_DENIED:
            self.metrics.increment_counter('vault_access_denied_total')
        
        elif event.event_type == EventType.NFT_MINTED:
            self.metrics.increment_counter('nft_minted_total')
        
        elif event.event_type == EventType.NFT_TRANSFERRED:
            self.metrics.increment_counter('nft_transferred_total')
    
    def _evaluate_alert_rules(self, event: MonitoringEvent):
        """Évalue les règles d'alerte"""
        for rule in self.alert_rules:
            alert = rule.evaluate(event)
            if alert:
                with self._lock:
                    self.alerts.append(alert)
                
                # Notifier l'alerte
                self.webhooks.notify_alert(alert)
                
                print(f"[ALERT {alert.severity.value.upper()}] {alert.title}")
    
    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acquitte une alerte"""
        with self._lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_by = user_id
                    alert.acknowledged_at = datetime.utcnow().isoformat()
                    return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Résout une alerte"""
        with self._lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = datetime.utcnow().isoformat()
                    return True
        return False
    
    def get_active_alerts(self, severity: AlertSeverity = None) -> List[Alert]:
        """Récupère les alertes actives"""
        with self._lock:
            alerts = [a for a in self.alerts if not a.resolved]
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            return alerts
    
    def get_events(self, event_type: EventType = None,
                   since_hours: float = 24,
                   user_id: str = None,
                   resource_id: str = None) -> List[MonitoringEvent]:
        """Récupère les événements filtrés"""
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        cutoff_str = cutoff.isoformat()
        
        with self._lock:
            events = [e for e in self.events if e.timestamp > cutoff_str]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if resource_id:
            events = [e for e in events if e.resource_id == resource_id]
        
        return events
    
    def get_health_status(self) -> Dict:
        """Retourne l'état de santé du système"""
        with self._lock:
            total_events = len(self.events)
            active_alerts = len([a for a in self.alerts if not a.resolved])
            critical_alerts = len([
                a for a in self.alerts 
                if not a.resolved and a.severity == AlertSeverity.CRITICAL
            ])
        
        # Événements des dernières 24h
        recent_events = self.get_events(since_hours=24)
        access_denied = len([
            e for e in recent_events 
            if e.event_type == EventType.VAULT_ACCESS_DENIED
        ])
        
        # Calcul du score de santé
        health_score = 100
        if critical_alerts > 0:
            health_score -= 40
        if active_alerts > 5:
            health_score -= 20
        if access_denied > 10:
            health_score -= 10
        
        health_score = max(0, health_score)
        
        return {
            'status': 'healthy' if health_score > 70 else 'degraded' if health_score > 30 else 'critical',
            'health_score': health_score,
            'total_events_stored': total_events,
            'active_alerts': active_alerts,
            'critical_alerts': critical_alerts,
            'events_24h': len(recent_events),
            'access_denied_24h': access_denied,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict:
        """Retourne les données pour un dashboard"""
        health = self.get_health_status()
        
        # Statistiques des dernières 24h
        recent = self.get_events(since_hours=24)
        
        event_counts = defaultdict(int)
        for e in recent:
            event_counts[e.event_type.value] += 1
        
        # Top utilisateurs actifs
        user_activity = defaultdict(int)
        for e in recent:
            if e.user_id:
                user_activity[e.user_id] += 1
        
        top_users = sorted(user_activity.items(), key=lambda x: -x[1])[:10]
        
        return {
            'health': health,
            'event_counts_24h': dict(event_counts),
            'top_active_users': top_users,
            'active_alerts': [a.to_dict() for a in self.get_active_alerts()],
            'recent_events': [e.to_dict() for e in recent[-20:]],
            'metrics_prometheus': self.metrics.get_metrics_prometheus()
        }
    
    def shutdown(self):
        """Arrête le système de monitoring"""
        self.webhooks.stop()


# Factory function
def create_vault_monitoring() -> VaultMonitoringSystem:
    """Crée et configure un système de monitoring"""
    return VaultMonitoringSystem()
