"""
AI Security System pour Eidolon
Detection d'anomalies, analyse comportementale, et prediction de menaces

Features:
- Detection d'anomalies en temps reel
- Analyse comportementale des utilisateurs
- Machine learning pour patterns d'attaque
- Prediction de menaces
- Risk scoring dynamique
- Alertes intelligentes
"""

import os
import json
import hashlib
import math
import time
import statistics
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import deque, defaultdict
import random


# ============================================================================
# ENUMERATIONS
# ============================================================================

class ThreatLevel(Enum):
    """Niveaux de menace"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(Enum):
    """Types d'anomalies"""
    UNUSUAL_ACCESS_TIME = "unusual_access_time"
    UNUSUAL_LOCATION = "unusual_location"
    UNUSUAL_DEVICE = "unusual_device"
    HIGH_FREQUENCY = "high_frequency"
    UNUSUAL_OPERATION = "unusual_operation"
    DATA_EXFILTRATION = "data_exfiltration"
    BRUTE_FORCE = "brute_force"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"


class ActionType(Enum):
    """Types d'actions surveillees"""
    LOGIN = "login"
    LOGOUT = "logout"
    KEY_ACCESS = "key_access"
    KEY_GENERATE = "key_generate"
    KEY_EXPORT = "key_export"
    VAULT_OPEN = "vault_open"
    VAULT_SHARE = "vault_share"
    ASSET_TRANSFER = "asset_transfer"
    SETTING_CHANGE = "setting_change"
    PERMISSION_CHANGE = "permission_change"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class SecurityEvent:
    """Evenement de securite"""
    event_id: str
    timestamp: str
    user_id: str
    action: ActionType
    
    # Context
    ip_address: str = ""
    device_id: str = ""
    location: str = ""
    user_agent: str = ""
    
    # Details
    resource_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Analysis
    risk_score: float = 0.0
    anomalies: List[AnomalyType] = field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.LOW
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['action'] = self.action.value
        d['anomalies'] = [a.value for a in self.anomalies]
        d['threat_level'] = self.threat_level.value
        return d


@dataclass
class UserProfile:
    """Profil comportemental utilisateur"""
    user_id: str
    created_at: str
    last_updated: str
    
    # Patterns temporels
    typical_hours: List[int] = field(default_factory=list)  # 0-23
    typical_days: List[int] = field(default_factory=list)   # 0-6
    
    # Patterns de localisation
    known_ips: List[str] = field(default_factory=list)
    known_devices: List[str] = field(default_factory=list)
    known_locations: List[str] = field(default_factory=list)
    
    # Patterns d'action
    action_frequencies: Dict[str, float] = field(default_factory=dict)
    typical_session_duration: float = 0.0
    avg_actions_per_session: float = 0.0
    
    # Stats
    total_events: int = 0
    total_anomalies: int = 0
    risk_score_history: List[float] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ThreatIndicator:
    """Indicateur de menace"""
    indicator_id: str
    indicator_type: str  # ip, hash, pattern, etc.
    value: str
    
    # Metadata
    source: str = ""
    confidence: float = 0.0
    severity: ThreatLevel = ThreatLevel.MEDIUM
    
    # Timestamps
    first_seen: str = ""
    last_seen: str = ""
    
    # Context
    related_events: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['severity'] = self.severity.value
        return d


@dataclass
class Alert:
    """Alerte de securite"""
    alert_id: str
    timestamp: str
    
    # Classification
    threat_level: ThreatLevel
    anomaly_type: AnomalyType
    
    # Context
    user_id: str
    event_ids: List[str]
    description: str
    
    # Response
    recommended_actions: List[str] = field(default_factory=list)
    is_acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: str = ""
    
    # Resolution
    is_resolved: bool = False
    resolution_notes: str = ""
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['threat_level'] = self.threat_level.value
        d['anomaly_type'] = self.anomaly_type.value
        return d


# ============================================================================
# STATISTICAL MODELS
# ============================================================================

class GaussianModel:
    """Modele gaussien pour detection d'anomalies"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.data = deque(maxlen=window_size)
        self.mean = 0.0
        self.std = 1.0
    
    def update(self, value: float):
        """Met a jour le modele"""
        self.data.append(value)
        
        if len(self.data) >= 2:
            self.mean = statistics.mean(self.data)
            self.std = statistics.stdev(self.data) if len(self.data) > 1 else 1.0
    
    def anomaly_score(self, value: float) -> float:
        """Calcule le score d'anomalie (z-score)"""
        if self.std == 0:
            return 0.0
        
        z = abs(value - self.mean) / self.std
        return min(z / 3.0, 1.0)  # Normalize to [0, 1]
    
    def is_anomaly(self, value: float, threshold: float = 2.0) -> bool:
        """Detecte si la valeur est une anomalie"""
        if self.std == 0:
            return False
        
        z = abs(value - self.mean) / self.std
        return z > threshold


class IsolationForest:
    """Isolation Forest simplifie pour detection d'anomalies"""
    
    def __init__(self, n_trees: int = 100, sample_size: int = 256):
        self.n_trees = n_trees
        self.sample_size = sample_size
        self.trees = []
        self.fitted = False
    
    def fit(self, data: List[List[float]]):
        """Entraine le modele"""
        self.trees = []
        
        for _ in range(self.n_trees):
            # Sample data
            sample = random.sample(data, min(self.sample_size, len(data)))
            
            # Build tree
            tree = self._build_tree(sample, 0, int(math.log2(self.sample_size)))
            self.trees.append(tree)
        
        self.fitted = True
    
    def _build_tree(self, data: List[List[float]], depth: int, max_depth: int) -> dict:
        """Construit un arbre d'isolation"""
        if depth >= max_depth or len(data) <= 1:
            return {"type": "leaf", "size": len(data)}
        
        # Random split
        n_features = len(data[0]) if data else 0
        if n_features == 0:
            return {"type": "leaf", "size": len(data)}
        
        feature = random.randint(0, n_features - 1)
        values = [d[feature] for d in data]
        
        if max(values) == min(values):
            return {"type": "leaf", "size": len(data)}
        
        split = random.uniform(min(values), max(values))
        
        left = [d for d in data if d[feature] < split]
        right = [d for d in data if d[feature] >= split]
        
        return {
            "type": "split",
            "feature": feature,
            "split": split,
            "left": self._build_tree(left, depth + 1, max_depth),
            "right": self._build_tree(right, depth + 1, max_depth)
        }
    
    def _path_length(self, point: List[float], tree: dict, depth: int = 0) -> int:
        """Calcule la longueur du chemin pour un point"""
        if tree["type"] == "leaf":
            return depth + self._c(tree["size"])
        
        if point[tree["feature"]] < tree["split"]:
            return self._path_length(point, tree["left"], depth + 1)
        else:
            return self._path_length(point, tree["right"], depth + 1)
    
    def _c(self, n: int) -> float:
        """Facteur de normalisation"""
        if n <= 1:
            return 0
        return 2 * (math.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n
    
    def anomaly_score(self, point: List[float]) -> float:
        """Calcule le score d'anomalie"""
        if not self.fitted or not self.trees:
            return 0.0
        
        avg_path = sum(self._path_length(point, tree) for tree in self.trees) / len(self.trees)
        c = self._c(self.sample_size)
        
        if c == 0:
            return 0.0
        
        return 2 ** (-avg_path / c)


class MarkovChain:
    """Chaine de Markov pour sequences d'actions"""
    
    def __init__(self):
        self.transitions = defaultdict(lambda: defaultdict(int))
        self.totals = defaultdict(int)
    
    def update(self, from_state: str, to_state: str):
        """Met a jour les transitions"""
        self.transitions[from_state][to_state] += 1
        self.totals[from_state] += 1
    
    def probability(self, from_state: str, to_state: str) -> float:
        """Probabilite de transition"""
        if self.totals[from_state] == 0:
            return 0.0
        
        return self.transitions[from_state][to_state] / self.totals[from_state]
    
    def sequence_probability(self, sequence: List[str]) -> float:
        """Probabilite d'une sequence"""
        if len(sequence) < 2:
            return 1.0
        
        prob = 1.0
        for i in range(len(sequence) - 1):
            p = self.probability(sequence[i], sequence[i + 1])
            prob *= p if p > 0 else 0.001  # Smoothing
        
        return prob
    
    def is_anomalous_sequence(self, sequence: List[str], threshold: float = 0.01) -> bool:
        """Detecte si une sequence est anormale"""
        return self.sequence_probability(sequence) < threshold


# ============================================================================
# ANOMALY DETECTOR
# ============================================================================

class AnomalyDetector:
    """Detecteur d'anomalies multi-dimensionnel"""
    
    def __init__(self):
        # Modeles par utilisateur
        self.user_models: Dict[str, Dict[str, Any]] = {}
        
        # Modeles globaux
        self.global_isolation_forest = IsolationForest()
        self.action_markov = MarkovChain()
        
        # Historique global
        self.global_events: deque = deque(maxlen=10000)
    
    def _get_user_model(self, user_id: str) -> Dict[str, Any]:
        """Obtient ou cree un modele utilisateur"""
        if user_id not in self.user_models:
            self.user_models[user_id] = {
                "time_model": GaussianModel(),
                "frequency_model": GaussianModel(),
                "action_chain": MarkovChain(),
                "known_ips": set(),
                "known_devices": set(),
                "last_actions": deque(maxlen=10)
            }
        
        return self.user_models[user_id]
    
    def analyze_event(self, event: SecurityEvent) -> List[AnomalyType]:
        """Analyse un evenement et detecte les anomalies"""
        anomalies = []
        model = self._get_user_model(event.user_id)
        
        # 1. Analyse temporelle
        hour = datetime.fromisoformat(event.timestamp).hour
        model["time_model"].update(hour)
        
        if model["time_model"].is_anomaly(hour, threshold=2.5):
            anomalies.append(AnomalyType.UNUSUAL_ACCESS_TIME)
        
        # 2. Analyse de localisation
        if event.ip_address:
            if len(model["known_ips"]) > 5 and event.ip_address not in model["known_ips"]:
                anomalies.append(AnomalyType.UNUSUAL_LOCATION)
            model["known_ips"].add(event.ip_address)
        
        # 3. Analyse de device
        if event.device_id:
            if len(model["known_devices"]) > 3 and event.device_id not in model["known_devices"]:
                anomalies.append(AnomalyType.UNUSUAL_DEVICE)
            model["known_devices"].add(event.device_id)
        
        # 4. Analyse de frequence
        now = time.time()
        recent_count = sum(1 for e in self.global_events 
                         if e.user_id == event.user_id and 
                         (now - time.mktime(datetime.fromisoformat(e.timestamp).timetuple())) < 60)
        
        model["frequency_model"].update(recent_count)
        
        if recent_count > 10 and model["frequency_model"].is_anomaly(recent_count, threshold=3.0):
            anomalies.append(AnomalyType.HIGH_FREQUENCY)
        
        # 5. Analyse de sequence d'actions
        last_actions = list(model["last_actions"])
        if last_actions:
            model["action_chain"].update(last_actions[-1], event.action.value)
            
            sequence = last_actions[-5:] + [event.action.value]
            if len(sequence) >= 3 and model["action_chain"].is_anomalous_sequence(sequence):
                anomalies.append(AnomalyType.UNUSUAL_OPERATION)
        
        model["last_actions"].append(event.action.value)
        
        # 6. Detection de patterns specifiques
        anomalies.extend(self._detect_attack_patterns(event, model))
        
        # Store event
        self.global_events.append(event)
        
        return anomalies
    
    def _detect_attack_patterns(self, event: SecurityEvent, model: Dict) -> List[AnomalyType]:
        """Detecte des patterns d'attaque specifiques"""
        anomalies = []
        
        # Brute force detection
        if event.action == ActionType.LOGIN:
            recent_logins = sum(1 for e in self.global_events 
                               if e.user_id == event.user_id and 
                               e.action == ActionType.LOGIN and
                               e.details.get("success") == False)
            
            if recent_logins > 5:
                anomalies.append(AnomalyType.BRUTE_FORCE)
        
        # Data exfiltration detection
        if event.action == ActionType.KEY_EXPORT:
            recent_exports = sum(1 for e in self.global_events 
                                if e.user_id == event.user_id and 
                                e.action == ActionType.KEY_EXPORT)
            
            if recent_exports > 3:
                anomalies.append(AnomalyType.DATA_EXFILTRATION)
        
        # Privilege escalation
        if event.action == ActionType.PERMISSION_CHANGE:
            if event.details.get("elevated", False):
                anomalies.append(AnomalyType.PRIVILEGE_ESCALATION)
        
        return anomalies


# ============================================================================
# BEHAVIORAL ANALYZER
# ============================================================================

class BehavioralAnalyzer:
    """Analyseur comportemental avance"""
    
    def __init__(self, data_dir: str = "./behavioral_data"):
        self.data_dir = data_dir
        self.profiles_dir = f"{data_dir}/profiles"
        
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        self._profiles: Dict[str, UserProfile] = {}
    
    def get_profile(self, user_id: str) -> UserProfile:
        """Obtient ou cree un profil utilisateur"""
        if user_id in self._profiles:
            return self._profiles[user_id]
        
        path = f"{self.profiles_dir}/{user_id}.json"
        
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                profile = UserProfile(**data)
                self._profiles[user_id] = profile
                return profile
        
        profile = UserProfile(
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        
        self._save_profile(profile)
        return profile
    
    def _save_profile(self, profile: UserProfile):
        """Sauvegarde un profil"""
        profile.last_updated = datetime.now().isoformat()
        self._profiles[profile.user_id] = profile
        
        with open(f"{self.profiles_dir}/{profile.user_id}.json", 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
    
    def update_profile(self, event: SecurityEvent):
        """Met a jour le profil avec un nouvel evenement"""
        profile = self.get_profile(event.user_id)
        
        # Update temporal patterns
        dt = datetime.fromisoformat(event.timestamp)
        
        if dt.hour not in profile.typical_hours:
            profile.typical_hours.append(dt.hour)
            profile.typical_hours = profile.typical_hours[-24:]
        
        if dt.weekday() not in profile.typical_days:
            profile.typical_days.append(dt.weekday())
        
        # Update location patterns
        if event.ip_address and event.ip_address not in profile.known_ips:
            profile.known_ips.append(event.ip_address)
            profile.known_ips = profile.known_ips[-50:]
        
        if event.device_id and event.device_id not in profile.known_devices:
            profile.known_devices.append(event.device_id)
            profile.known_devices = profile.known_devices[-20:]
        
        # Update action frequencies
        action_key = event.action.value
        current = profile.action_frequencies.get(action_key, 0)
        profile.action_frequencies[action_key] = current + 1
        
        # Update stats
        profile.total_events += 1
        profile.total_anomalies += len(event.anomalies)
        
        profile.risk_score_history.append(event.risk_score)
        profile.risk_score_history = profile.risk_score_history[-100:]
        
        self._save_profile(profile)
    
    def calculate_behavior_deviation(self, event: SecurityEvent) -> float:
        """Calcule la deviation par rapport au comportement normal"""
        profile = self.get_profile(event.user_id)
        
        deviations = []
        
        # Temporal deviation
        dt = datetime.fromisoformat(event.timestamp)
        
        if profile.typical_hours:
            hour_deviation = min(
                abs(dt.hour - h) for h in profile.typical_hours
            ) / 12.0
            deviations.append(hour_deviation)
        
        # Location deviation
        if profile.known_ips and event.ip_address:
            ip_known = 0.0 if event.ip_address in profile.known_ips else 1.0
            deviations.append(ip_known)
        
        # Device deviation
        if profile.known_devices and event.device_id:
            device_known = 0.0 if event.device_id in profile.known_devices else 1.0
            deviations.append(device_known)
        
        # Action frequency deviation
        if profile.action_frequencies:
            total_actions = sum(profile.action_frequencies.values())
            action_key = event.action.value
            expected_freq = profile.action_frequencies.get(action_key, 0) / max(total_actions, 1)
            action_deviation = 1.0 - expected_freq
            deviations.append(action_deviation)
        
        if not deviations:
            return 0.0
        
        return sum(deviations) / len(deviations)


# ============================================================================
# THREAT PREDICTOR
# ============================================================================

class ThreatPredictor:
    """Predicteur de menaces base sur ML"""
    
    def __init__(self):
        self.threat_indicators: Dict[str, ThreatIndicator] = {}
        self.attack_sequences: List[List[str]] = []
        
        # Known attack patterns
        self.known_patterns = [
            ["LOGIN", "KEY_ACCESS", "KEY_EXPORT"],  # Potential theft
            ["LOGIN", "SETTING_CHANGE", "PERMISSION_CHANGE"],  # Privilege escalation
            ["LOGIN", "LOGIN", "LOGIN", "LOGIN", "LOGIN"],  # Brute force
            ["KEY_ACCESS", "KEY_ACCESS", "KEY_ACCESS", "KEY_EXPORT"],  # Exfiltration
        ]
    
    def add_indicator(self, indicator: ThreatIndicator):
        """Ajoute un indicateur de menace"""
        self.threat_indicators[indicator.indicator_id] = indicator
    
    def check_indicators(self, event: SecurityEvent) -> List[ThreatIndicator]:
        """Verifie les indicateurs de menace"""
        matches = []
        
        for indicator in self.threat_indicators.values():
            if indicator.indicator_type == "ip" and indicator.value == event.ip_address:
                matches.append(indicator)
            elif indicator.indicator_type == "device" and indicator.value == event.device_id:
                matches.append(indicator)
            elif indicator.indicator_type == "user" and indicator.value == event.user_id:
                matches.append(indicator)
        
        return matches
    
    def predict_attack(self, recent_actions: List[str]) -> Tuple[float, str]:
        """Predit la probabilite d'attaque"""
        max_match = 0.0
        predicted_attack = ""
        
        for pattern in self.known_patterns:
            if len(recent_actions) < 2:
                continue
            
            # Calculate similarity
            match_count = 0
            for i, action in enumerate(recent_actions[-len(pattern):]):
                if i < len(pattern) and action.upper() == pattern[i]:
                    match_count += 1
            
            similarity = match_count / len(pattern)
            
            if similarity > max_match:
                max_match = similarity
                
                if pattern == self.known_patterns[0]:
                    predicted_attack = "credential_theft"
                elif pattern == self.known_patterns[1]:
                    predicted_attack = "privilege_escalation"
                elif pattern == self.known_patterns[2]:
                    predicted_attack = "brute_force"
                elif pattern == self.known_patterns[3]:
                    predicted_attack = "data_exfiltration"
        
        return max_match, predicted_attack
    
    def get_risk_forecast(self, user_id: str, events: List[SecurityEvent]) -> Dict[str, Any]:
        """Prevision de risque pour les prochaines heures"""
        user_events = [e for e in events if e.user_id == user_id]
        
        if not user_events:
            return {"risk_level": "unknown", "confidence": 0.0}
        
        # Calculate trend
        recent_scores = [e.risk_score for e in user_events[-10:]]
        
        if len(recent_scores) < 2:
            return {
                "risk_level": "low",
                "confidence": 0.3,
                "trend": "stable"
            }
        
        trend = (recent_scores[-1] - recent_scores[0]) / len(recent_scores)
        avg_score = sum(recent_scores) / len(recent_scores)
        
        # Predict
        predicted_score = avg_score + trend * 5  # 5 events ahead
        
        risk_level = "low"
        if predicted_score > 0.7:
            risk_level = "critical"
        elif predicted_score > 0.5:
            risk_level = "high"
        elif predicted_score > 0.3:
            risk_level = "medium"
        
        return {
            "risk_level": risk_level,
            "predicted_score": min(max(predicted_score, 0), 1),
            "confidence": min(len(recent_scores) / 10, 1.0),
            "trend": "increasing" if trend > 0.05 else "decreasing" if trend < -0.05 else "stable"
        }


# ============================================================================
# RISK SCORING ENGINE
# ============================================================================

class RiskScoringEngine:
    """Moteur de scoring de risque"""
    
    def __init__(self):
        # Weights for different factors
        self.weights = {
            "anomaly_count": 0.3,
            "anomaly_severity": 0.25,
            "behavior_deviation": 0.2,
            "threat_indicators": 0.15,
            "historical_risk": 0.1
        }
        
        # Anomaly severity scores
        self.anomaly_severity = {
            AnomalyType.UNUSUAL_ACCESS_TIME: 0.2,
            AnomalyType.UNUSUAL_LOCATION: 0.4,
            AnomalyType.UNUSUAL_DEVICE: 0.3,
            AnomalyType.HIGH_FREQUENCY: 0.5,
            AnomalyType.UNUSUAL_OPERATION: 0.4,
            AnomalyType.DATA_EXFILTRATION: 0.9,
            AnomalyType.BRUTE_FORCE: 0.8,
            AnomalyType.PRIVILEGE_ESCALATION: 0.95,
            AnomalyType.LATERAL_MOVEMENT: 0.85
        }
    
    def calculate_risk_score(self, event: SecurityEvent, 
                           behavior_deviation: float,
                           threat_indicators: List[ThreatIndicator],
                           historical_avg: float) -> float:
        """Calcule le score de risque global"""
        scores = {}
        
        # Anomaly count factor
        scores["anomaly_count"] = min(len(event.anomalies) / 5, 1.0)
        
        # Anomaly severity factor
        if event.anomalies:
            severity = max(self.anomaly_severity.get(a, 0.5) for a in event.anomalies)
            scores["anomaly_severity"] = severity
        else:
            scores["anomaly_severity"] = 0.0
        
        # Behavior deviation
        scores["behavior_deviation"] = behavior_deviation
        
        # Threat indicators
        if threat_indicators:
            max_confidence = max(i.confidence for i in threat_indicators)
            scores["threat_indicators"] = max_confidence
        else:
            scores["threat_indicators"] = 0.0
        
        # Historical risk
        scores["historical_risk"] = historical_avg
        
        # Weighted sum
        total = sum(scores[k] * self.weights[k] for k in self.weights)
        
        return min(max(total, 0), 1)
    
    def determine_threat_level(self, risk_score: float) -> ThreatLevel:
        """Determine le niveau de menace"""
        if risk_score >= 0.8:
            return ThreatLevel.CRITICAL
        elif risk_score >= 0.6:
            return ThreatLevel.HIGH
        elif risk_score >= 0.3:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW


# ============================================================================
# ALERT MANAGER
# ============================================================================

class AlertManager:
    """Gestionnaire d'alertes intelligentes"""
    
    def __init__(self, data_dir: str = "./alerts_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self._alerts: Dict[str, Alert] = {}
        
        # Alert thresholds
        self.alert_thresholds = {
            ThreatLevel.LOW: 0.3,
            ThreatLevel.MEDIUM: 0.5,
            ThreatLevel.HIGH: 0.7,
            ThreatLevel.CRITICAL: 0.85
        }
    
    def should_alert(self, event: SecurityEvent) -> bool:
        """Determine si une alerte doit etre declenchee"""
        threshold = self.alert_thresholds.get(event.threat_level, 0.5)
        return event.risk_score >= threshold
    
    def create_alert(self, event: SecurityEvent, description: str = "") -> Alert:
        """Cree une nouvelle alerte"""
        import secrets
        
        alert_id = secrets.token_hex(16)
        
        # Generate recommended actions
        actions = self._generate_recommendations(event)
        
        alert = Alert(
            alert_id=alert_id,
            timestamp=datetime.now().isoformat(),
            threat_level=event.threat_level,
            anomaly_type=event.anomalies[0] if event.anomalies else AnomalyType.UNUSUAL_OPERATION,
            user_id=event.user_id,
            event_ids=[event.event_id],
            description=description or f"Security alert: {event.threat_level.value} risk detected",
            recommended_actions=actions
        )
        
        self._save_alert(alert)
        return alert
    
    def _generate_recommendations(self, event: SecurityEvent) -> List[str]:
        """Genere des recommandations d'action"""
        recommendations = []
        
        for anomaly in event.anomalies:
            if anomaly == AnomalyType.BRUTE_FORCE:
                recommendations.extend([
                    "Block IP address temporarily",
                    "Enable additional authentication factor",
                    "Review account security settings"
                ])
            elif anomaly == AnomalyType.DATA_EXFILTRATION:
                recommendations.extend([
                    "Revoke active sessions",
                    "Audit recent data access",
                    "Contact security team immediately"
                ])
            elif anomaly == AnomalyType.PRIVILEGE_ESCALATION:
                recommendations.extend([
                    "Review permission changes",
                    "Verify with account owner",
                    "Rollback unauthorized changes"
                ])
            elif anomaly == AnomalyType.UNUSUAL_LOCATION:
                recommendations.extend([
                    "Verify user location",
                    "Enable location-based restrictions"
                ])
        
        if event.threat_level == ThreatLevel.CRITICAL:
            recommendations.insert(0, "URGENT: Investigate immediately")
        
        return list(set(recommendations))[:5]
    
    def acknowledge_alert(self, alert_id: str, user: str):
        """Acquitte une alerte"""
        alert = self._alerts.get(alert_id)
        
        if alert:
            alert.is_acknowledged = True
            alert.acknowledged_by = user
            alert.acknowledged_at = datetime.now().isoformat()
            self._save_alert(alert)
    
    def resolve_alert(self, alert_id: str, notes: str):
        """Resout une alerte"""
        alert = self._alerts.get(alert_id)
        
        if alert:
            alert.is_resolved = True
            alert.resolution_notes = notes
            self._save_alert(alert)
    
    def _save_alert(self, alert: Alert):
        """Sauvegarde une alerte"""
        self._alerts[alert.alert_id] = alert
        
        with open(f"{self.data_dir}/{alert.alert_id}.json", 'w') as f:
            json.dump(alert.to_dict(), f, indent=2)
    
    def get_active_alerts(self) -> List[Alert]:
        """Recupere les alertes actives"""
        return [a for a in self._alerts.values() if not a.is_resolved]


# ============================================================================
# AI SECURITY SYSTEM FACADE
# ============================================================================

class AISecuritySystem:
    """Facade pour le systeme de securite IA complet"""
    
    def __init__(self, data_dir: str = "./ai_security_data"):
        self.data_dir = data_dir
        
        self.detector = AnomalyDetector()
        self.analyzer = BehavioralAnalyzer(f"{data_dir}/behavioral")
        self.predictor = ThreatPredictor()
        self.scorer = RiskScoringEngine()
        self.alert_manager = AlertManager(f"{data_dir}/alerts")
        
        # Event history
        self.events: List[SecurityEvent] = []
    
    def process_event(self, event: SecurityEvent) -> SecurityEvent:
        """Traite un evenement de securite"""
        # 1. Detect anomalies
        anomalies = self.detector.analyze_event(event)
        event.anomalies = anomalies
        
        # 2. Calculate behavior deviation
        deviation = self.analyzer.calculate_behavior_deviation(event)
        
        # 3. Check threat indicators
        indicators = self.predictor.check_indicators(event)
        
        # 4. Get historical average
        user_events = [e for e in self.events if e.user_id == event.user_id]
        historical_avg = (sum(e.risk_score for e in user_events[-20:]) / 
                        max(len(user_events[-20:]), 1))
        
        # 5. Calculate risk score
        event.risk_score = self.scorer.calculate_risk_score(
            event, deviation, indicators, historical_avg
        )
        
        # 6. Determine threat level
        event.threat_level = self.scorer.determine_threat_level(event.risk_score)
        
        # 7. Update profile
        self.analyzer.update_profile(event)
        
        # 8. Create alert if needed
        if self.alert_manager.should_alert(event):
            self.alert_manager.create_alert(event)
        
        # Store event
        self.events.append(event)
        
        return event
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Donnees pour tableau de bord"""
        recent = self.events[-100:]
        
        threat_distribution = {
            ThreatLevel.LOW.value: 0,
            ThreatLevel.MEDIUM.value: 0,
            ThreatLevel.HIGH.value: 0,
            ThreatLevel.CRITICAL.value: 0
        }
        
        for event in recent:
            threat_distribution[event.threat_level.value] += 1
        
        anomaly_distribution = defaultdict(int)
        for event in recent:
            for anomaly in event.anomalies:
                anomaly_distribution[anomaly.value] += 1
        
        return {
            "total_events": len(self.events),
            "recent_events": len(recent),
            "active_alerts": len(self.alert_manager.get_active_alerts()),
            "threat_distribution": threat_distribution,
            "anomaly_distribution": dict(anomaly_distribution),
            "avg_risk_score": sum(e.risk_score for e in recent) / max(len(recent), 1),
            "users_monitored": len(self.analyzer._profiles)
        }
    
    def get_user_risk_report(self, user_id: str) -> Dict[str, Any]:
        """Rapport de risque utilisateur"""
        profile = self.analyzer.get_profile(user_id)
        user_events = [e for e in self.events if e.user_id == user_id]
        
        forecast = self.predictor.get_risk_forecast(user_id, self.events)
        
        return {
            "user_id": user_id,
            "profile": profile.to_dict(),
            "total_events": len(user_events),
            "total_anomalies": profile.total_anomalies,
            "current_risk": user_events[-1].risk_score if user_events else 0,
            "forecast": forecast,
            "recommendations": self._generate_user_recommendations(profile, user_events)
        }
    
    def _generate_user_recommendations(self, profile: UserProfile, 
                                       events: List[SecurityEvent]) -> List[str]:
        """Genere des recommandations pour l'utilisateur"""
        recommendations = []
        
        if profile.total_anomalies > 10:
            recommendations.append("Review account security settings")
        
        if len(profile.known_ips) > 20:
            recommendations.append("Consider enabling IP whitelisting")
        
        recent_scores = profile.risk_score_history[-10:]
        if recent_scores and sum(recent_scores) / len(recent_scores) > 0.5:
            recommendations.append("Enable additional authentication")
        
        return recommendations


# ============================================================================
# FACTORY
# ============================================================================

def create_ai_security_system(data_dir: str = "./ai_security_data") -> AISecuritySystem:
    """Cree un systeme de securite IA complet"""
    return AISecuritySystem(data_dir)
