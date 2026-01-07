"""
Compliance Module pour Eidolon
GDPR Data Handling + SOC 2 Type II Audit

Features:
- GDPR: Right to erasure, data portability, consent management
- SOC 2: Security, availability, processing integrity, confidentiality, privacy
- Audit trail with tamper-proof logging
- Data retention policies
- Privacy impact assessments
"""

import os
import json
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum, auto
from abc import ABC, abstractmethod

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.fernet import Fernet


# ============================================================================
# ENUMERATIONS
# ============================================================================

class GDPRLegalBasis(Enum):
    """Bases legales GDPR pour le traitement des donnees"""
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class DataCategory(Enum):
    """Categories de donnees personnelles"""
    BASIC_IDENTITY = "basic_identity"
    CONTACT = "contact"
    FINANCIAL = "financial"
    LOCATION = "location"
    BIOMETRIC = "biometric"
    HEALTH = "health"
    POLITICAL = "political"
    RELIGIOUS = "religious"
    GENETIC = "genetic"
    CRIMINAL = "criminal"
    BEHAVIORAL = "behavioral"


class ProcessingPurpose(Enum):
    """Finalites du traitement"""
    SERVICE_PROVISION = "service_provision"
    AUTHENTICATION = "authentication"
    SECURITY = "security"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    LEGAL_COMPLIANCE = "legal_compliance"
    RESEARCH = "research"


class SOC2Principle(Enum):
    """Principes SOC 2"""
    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class DataSubjectRight(Enum):
    """Droits des personnes concernees (GDPR)"""
    ACCESS = "access"                  # Art. 15
    RECTIFICATION = "rectification"    # Art. 16
    ERASURE = "erasure"               # Art. 17 - Droit a l'oubli
    RESTRICTION = "restriction"        # Art. 18
    PORTABILITY = "portability"        # Art. 20
    OBJECTION = "objection"           # Art. 21
    AUTOMATED_DECISION = "automated"   # Art. 22


class ComplianceEventType(Enum):
    """Types d'evenements de conformite"""
    # GDPR Events
    CONSENT_GIVEN = "gdpr.consent_given"
    CONSENT_WITHDRAWN = "gdpr.consent_withdrawn"
    DATA_ACCESS_REQUEST = "gdpr.data_access"
    DATA_ERASURE_REQUEST = "gdpr.data_erasure"
    DATA_PORTABILITY_REQUEST = "gdpr.data_portability"
    DATA_RECTIFICATION = "gdpr.data_rectification"
    BREACH_DETECTED = "gdpr.breach_detected"
    BREACH_NOTIFIED = "gdpr.breach_notified"
    
    # SOC 2 Events
    SECURITY_INCIDENT = "soc2.security_incident"
    ACCESS_GRANTED = "soc2.access_granted"
    ACCESS_REVOKED = "soc2.access_revoked"
    CONFIG_CHANGE = "soc2.config_change"
    ENCRYPTION_APPLIED = "soc2.encryption_applied"
    BACKUP_COMPLETED = "soc2.backup_completed"
    AUDIT_PERFORMED = "soc2.audit_performed"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ConsentRecord:
    """Enregistrement de consentement GDPR"""
    consent_id: str
    user_id: str
    purposes: List[ProcessingPurpose]
    legal_basis: GDPRLegalBasis
    given_at: str
    expires_at: Optional[str]
    ip_address: str
    user_agent: str
    
    # Consent details
    version: str = "1.0"
    explicit: bool = True
    withdrawable: bool = True
    withdrawn_at: Optional[str] = None
    
    # Proof
    consent_text_hash: str = ""
    signature: str = ""
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['purposes'] = [p.value for p in self.purposes]
        d['legal_basis'] = self.legal_basis.value
        return d
    
    @property
    def is_valid(self) -> bool:
        if self.withdrawn_at:
            return False
        if self.expires_at:
            return datetime.fromisoformat(self.expires_at) > datetime.now()
        return True


@dataclass
class DataSubjectRequest:
    """Demande d'exercice de droits GDPR"""
    request_id: str
    user_id: str
    right: DataSubjectRight
    submitted_at: str
    
    # Status
    status: str = "pending"  # pending, processing, completed, denied
    processed_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    response: Optional[str] = None
    
    # Verification
    identity_verified: bool = False
    verification_method: str = ""
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['right'] = self.right.value
        return d


@dataclass
class DataRetentionPolicy:
    """Politique de retention des donnees"""
    policy_id: str
    data_category: DataCategory
    retention_days: int
    legal_basis: str
    
    # Actions
    action_on_expiry: str = "delete"  # delete, anonymize, archive
    
    # Exceptions
    exceptions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['data_category'] = self.data_category.value
        return d


@dataclass
class PrivacyImpactAssessment:
    """Analyse d'impact sur la protection des donnees (DPIA)"""
    assessment_id: str
    project_name: str
    created_at: str
    
    # Data processing
    data_categories: List[DataCategory]
    purposes: List[ProcessingPurpose]
    data_subjects: List[str]  # Types of data subjects
    
    # Risks
    risks_identified: List[Dict[str, Any]] = field(default_factory=list)
    mitigations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Assessment
    necessity_assessment: str = ""
    proportionality_assessment: str = ""
    
    # Approval
    dpo_approved: bool = False
    dpo_comments: str = ""
    approved_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['data_categories'] = [c.value for c in self.data_categories]
        d['purposes'] = [p.value for p in self.purposes]
        return d


@dataclass
class DataBreach:
    """Enregistrement de violation de donnees"""
    breach_id: str
    detected_at: str
    
    # Details
    description: str
    data_categories_affected: List[DataCategory]
    subjects_affected_count: int
    
    # Impact
    risk_level: str  # low, medium, high, critical
    likely_consequences: List[str]
    
    # Response
    containment_measures: List[str] = field(default_factory=list)
    notified_authority: bool = False
    notified_authority_at: Optional[str] = None
    notified_subjects: bool = False
    notified_subjects_at: Optional[str] = None
    
    # Resolution
    resolved: bool = False
    resolved_at: Optional[str] = None
    root_cause: str = ""
    preventive_measures: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['data_categories_affected'] = [c.value for c in self.data_categories_affected]
        return d


@dataclass
class ComplianceAuditLog:
    """Log d'audit SOC 2"""
    log_id: str
    timestamp: str
    event_type: ComplianceEventType
    
    # Actor
    user_id: str
    ip_address: str
    user_agent: str
    
    # Resource
    resource_type: str
    resource_id: str
    
    # Details
    action: str
    details: Dict[str, Any]
    
    # SOC 2 Principles
    principles: List[SOC2Principle]
    
    # Integrity
    previous_hash: str
    log_hash: str
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['event_type'] = self.event_type.value
        d['principles'] = [p.value for p in self.principles]
        return d


# ============================================================================
# GDPR COMPLIANCE MANAGER
# ============================================================================

class GDPRComplianceManager:
    """Gestionnaire de conformite GDPR"""
    
    def __init__(self, data_dir: str = "./compliance_data"):
        self.data_dir = data_dir
        self.consents_dir = f"{data_dir}/consents"
        self.requests_dir = f"{data_dir}/dsr"  # Data Subject Requests
        self.policies_dir = f"{data_dir}/policies"
        self.breaches_dir = f"{data_dir}/breaches"
        self.dpia_dir = f"{data_dir}/dpia"
        
        for d in [self.consents_dir, self.requests_dir, self.policies_dir,
                  self.breaches_dir, self.dpia_dir]:
            os.makedirs(d, exist_ok=True)
    
    # === CONSENT MANAGEMENT ===
    
    def record_consent(self, user_id: str, purposes: List[ProcessingPurpose],
                      legal_basis: GDPRLegalBasis, consent_text: str,
                      ip_address: str, user_agent: str,
                      expires_days: int = None) -> ConsentRecord:
        """Enregistre un consentement"""
        consent_id = secrets.token_hex(16)
        now = datetime.now()
        
        consent = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            purposes=purposes,
            legal_basis=legal_basis,
            given_at=now.isoformat(),
            expires_at=(now + timedelta(days=expires_days)).isoformat() if expires_days else None,
            ip_address=ip_address,
            user_agent=user_agent,
            consent_text_hash=hashlib.sha256(consent_text.encode()).hexdigest()
        )
        
        # Save
        self._save_consent(consent)
        
        return consent
    
    def withdraw_consent(self, user_id: str, consent_id: str) -> bool:
        """Retire un consentement"""
        consent = self.get_consent(consent_id)
        
        if not consent or consent.user_id != user_id:
            return False
        
        if not consent.withdrawable:
            return False
        
        consent.withdrawn_at = datetime.now().isoformat()
        self._save_consent(consent)
        
        return True
    
    def get_consent(self, consent_id: str) -> Optional[ConsentRecord]:
        """Recupere un consentement"""
        path = f"{self.consents_dir}/{consent_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            d = json.load(f)
        
        d['purposes'] = [ProcessingPurpose(p) for p in d['purposes']]
        d['legal_basis'] = GDPRLegalBasis(d['legal_basis'])
        
        return ConsentRecord(**d)
    
    def get_user_consents(self, user_id: str) -> List[ConsentRecord]:
        """Recupere tous les consentements d'un utilisateur"""
        consents = []
        
        for filename in os.listdir(self.consents_dir):
            if filename.endswith('.json'):
                consent = self.get_consent(filename[:-5])
                if consent and consent.user_id == user_id:
                    consents.append(consent)
        
        return consents
    
    def check_consent(self, user_id: str, purpose: ProcessingPurpose) -> bool:
        """Verifie si un utilisateur a consenti a une finalite"""
        consents = self.get_user_consents(user_id)
        
        for consent in consents:
            if consent.is_valid and purpose in consent.purposes:
                return True
        
        return False
    
    def _save_consent(self, consent: ConsentRecord):
        """Sauvegarde un consentement"""
        path = f"{self.consents_dir}/{consent.consent_id}.json"
        
        with open(path, 'w') as f:
            json.dump(consent.to_dict(), f, indent=2)
    
    # === DATA SUBJECT RIGHTS ===
    
    def submit_request(self, user_id: str, right: DataSubjectRight,
                      details: Dict[str, Any] = None) -> DataSubjectRequest:
        """Soumet une demande d'exercice de droits"""
        request_id = secrets.token_hex(16)
        
        request = DataSubjectRequest(
            request_id=request_id,
            user_id=user_id,
            right=right,
            submitted_at=datetime.now().isoformat(),
            details=details or {}
        )
        
        self._save_request(request)
        
        return request
    
    def process_request(self, request_id: str) -> bool:
        """Marque une demande comme en cours de traitement"""
        request = self.get_request(request_id)
        
        if not request or request.status != "pending":
            return False
        
        request.status = "processing"
        request.processed_at = datetime.now().isoformat()
        self._save_request(request)
        
        return True
    
    def complete_request(self, request_id: str, response: str) -> bool:
        """Complete une demande"""
        request = self.get_request(request_id)
        
        if not request or request.status not in ["pending", "processing"]:
            return False
        
        request.status = "completed"
        request.completed_at = datetime.now().isoformat()
        request.response = response
        self._save_request(request)
        
        return True
    
    def get_request(self, request_id: str) -> Optional[DataSubjectRequest]:
        """Recupere une demande"""
        path = f"{self.requests_dir}/{request_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            d = json.load(f)
        
        d['right'] = DataSubjectRight(d['right'])
        
        return DataSubjectRequest(**d)
    
    def _save_request(self, request: DataSubjectRequest):
        """Sauvegarde une demande"""
        path = f"{self.requests_dir}/{request.request_id}.json"
        
        with open(path, 'w') as f:
            json.dump(request.to_dict(), f, indent=2)
    
    # === RIGHT TO ERASURE ===
    
    def execute_erasure(self, user_id: str, data_locations: List[str]) -> Dict[str, bool]:
        """Execute le droit a l'effacement"""
        results = {}
        
        for location in data_locations:
            try:
                # Secure deletion
                if os.path.exists(location):
                    # Overwrite with random data before deletion
                    size = os.path.getsize(location)
                    with open(location, 'wb') as f:
                        f.write(os.urandom(size))
                    os.remove(location)
                    results[location] = True
                else:
                    results[location] = False
            except Exception as e:
                results[location] = False
        
        return results
    
    # === DATA PORTABILITY ===
    
    def export_user_data(self, user_id: str, data_sources: Dict[str, Any]) -> bytes:
        """Exporte les donnees d'un utilisateur (format JSON)"""
        export_data = {
            "export_date": datetime.now().isoformat(),
            "user_id": user_id,
            "data": data_sources
        }
        
        return json.dumps(export_data, indent=2).encode('utf-8')
    
    # === DATA BREACH ===
    
    def report_breach(self, description: str, categories: List[DataCategory],
                     subjects_count: int, risk_level: str) -> DataBreach:
        """Signale une violation de donnees"""
        breach_id = secrets.token_hex(16)
        
        breach = DataBreach(
            breach_id=breach_id,
            detected_at=datetime.now().isoformat(),
            description=description,
            data_categories_affected=categories,
            subjects_affected_count=subjects_count,
            risk_level=risk_level,
            likely_consequences=[]
        )
        
        self._save_breach(breach)
        
        # GDPR requires notification within 72 hours for high-risk breaches
        if risk_level in ["high", "critical"]:
            print(f"[ALERT] High-risk breach detected! Notification required within 72 hours.")
        
        return breach
    
    def notify_breach_authority(self, breach_id: str) -> bool:
        """Notifie l'autorite de controle"""
        breach = self.get_breach(breach_id)
        
        if not breach:
            return False
        
        breach.notified_authority = True
        breach.notified_authority_at = datetime.now().isoformat()
        self._save_breach(breach)
        
        return True
    
    def get_breach(self, breach_id: str) -> Optional[DataBreach]:
        """Recupere une violation"""
        path = f"{self.breaches_dir}/{breach_id}.json"
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r') as f:
            d = json.load(f)
        
        d['data_categories_affected'] = [DataCategory(c) for c in d['data_categories_affected']]
        
        return DataBreach(**d)
    
    def _save_breach(self, breach: DataBreach):
        """Sauvegarde une violation"""
        path = f"{self.breaches_dir}/{breach.breach_id}.json"
        
        with open(path, 'w') as f:
            json.dump(breach.to_dict(), f, indent=2)
    
    # === RETENTION POLICIES ===
    
    def create_retention_policy(self, category: DataCategory, retention_days: int,
                               legal_basis: str, action: str = "delete") -> DataRetentionPolicy:
        """Cree une politique de retention"""
        policy_id = secrets.token_hex(8)
        
        policy = DataRetentionPolicy(
            policy_id=policy_id,
            data_category=category,
            retention_days=retention_days,
            legal_basis=legal_basis,
            action_on_expiry=action
        )
        
        path = f"{self.policies_dir}/{policy_id}.json"
        with open(path, 'w') as f:
            json.dump(policy.to_dict(), f, indent=2)
        
        return policy
    
    def get_retention_policy(self, category: DataCategory) -> Optional[DataRetentionPolicy]:
        """Recupere la politique de retention pour une categorie"""
        for filename in os.listdir(self.policies_dir):
            if filename.endswith('.json'):
                path = f"{self.policies_dir}/{filename}"
                with open(path, 'r') as f:
                    d = json.load(f)
                
                if d['data_category'] == category.value:
                    d['data_category'] = DataCategory(d['data_category'])
                    return DataRetentionPolicy(**d)
        
        return None


# ============================================================================
# SOC 2 AUDIT MANAGER
# ============================================================================

class SOC2AuditManager:
    """Gestionnaire d'audit SOC 2 Type II"""
    
    def __init__(self, signing_key: bytes, data_dir: str = "./compliance_data/soc2"):
        self.signing_key = signing_key
        self.data_dir = data_dir
        self.logs_dir = f"{data_dir}/audit_logs"
        
        os.makedirs(self.logs_dir, exist_ok=True)
        
        self._last_hash = self._load_last_hash()
    
    def _load_last_hash(self) -> str:
        """Charge le dernier hash"""
        hash_file = f"{self.data_dir}/last_hash"
        
        if os.path.exists(hash_file):
            with open(hash_file, 'r') as f:
                return f.read().strip()
        
        return "0" * 64
    
    def _save_last_hash(self, hash_value: str):
        """Sauvegarde le dernier hash"""
        hash_file = f"{self.data_dir}/last_hash"
        
        with open(hash_file, 'w') as f:
            f.write(hash_value)
        
        self._last_hash = hash_value
    
    def _compute_hash(self, log: ComplianceAuditLog) -> str:
        """Calcule le hash d'un log"""
        data = f"{log.timestamp}:{log.event_type.value}:{log.user_id}:" \
               f"{log.resource_type}:{log.resource_id}:{log.action}:" \
               f"{json.dumps(log.details)}:{log.previous_hash}"
        
        return hashlib.sha256(data.encode()).hexdigest()
    
    def log_event(self, event_type: ComplianceEventType, user_id: str,
                 resource_type: str, resource_id: str, action: str,
                 details: Dict[str, Any], principles: List[SOC2Principle],
                 ip_address: str = "0.0.0.0", user_agent: str = "unknown") -> ComplianceAuditLog:
        """Enregistre un evenement d'audit"""
        
        log_id = secrets.token_hex(16)
        timestamp = datetime.now().isoformat()
        
        log = ComplianceAuditLog(
            log_id=log_id,
            timestamp=timestamp,
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            principles=principles,
            previous_hash=self._last_hash,
            log_hash=""
        )
        
        # Compute hash
        log.log_hash = self._compute_hash(log)
        
        # Save log
        self._save_log(log)
        
        # Update last hash
        self._save_last_hash(log.log_hash)
        
        return log
    
    def _save_log(self, log: ComplianceAuditLog):
        """Sauvegarde un log"""
        date_str = log.timestamp[:10]
        log_file = f"{self.logs_dir}/audit_{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log.to_dict()) + '\n')
    
    def verify_chain_integrity(self) -> Tuple[bool, List[str]]:
        """Verifie l'integrite de la chaine d'audit"""
        errors = []
        expected_previous = "0" * 64
        
        log_files = sorted([f for f in os.listdir(self.logs_dir) if f.startswith("audit_")])
        
        for log_file in log_files:
            with open(f"{self.logs_dir}/{log_file}", 'r') as f:
                for line_num, line in enumerate(f, 1):
                    d = json.loads(line)
                    d['event_type'] = ComplianceEventType(d['event_type'])
                    d['principles'] = [SOC2Principle(p) for p in d['principles']]
                    log = ComplianceAuditLog(**d)
                    
                    # Verify chain
                    if log.previous_hash != expected_previous:
                        errors.append(f"{log_file}:{line_num} - Chain broken")
                    
                    # Verify hash
                    computed = self._compute_hash(log)
                    if computed != log.log_hash:
                        errors.append(f"{log_file}:{line_num} - Hash mismatch")
                    
                    expected_previous = log.log_hash
        
        return len(errors) == 0, errors
    
    def get_logs(self, start_date: str = None, end_date: str = None,
                event_type: ComplianceEventType = None,
                principle: SOC2Principle = None,
                limit: int = 1000) -> List[ComplianceAuditLog]:
        """Recupere les logs filtres"""
        logs = []
        
        log_files = sorted([f for f in os.listdir(self.logs_dir) if f.startswith("audit_")],
                          reverse=True)
        
        for log_file in log_files:
            file_date = log_file[6:16]
            
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue
            
            with open(f"{self.logs_dir}/{log_file}", 'r') as f:
                for line in f:
                    if len(logs) >= limit:
                        break
                    
                    d = json.loads(line)
                    
                    # Apply filters
                    if event_type and d['event_type'] != event_type.value:
                        continue
                    if principle and principle.value not in d['principles']:
                        continue
                    
                    d['event_type'] = ComplianceEventType(d['event_type'])
                    d['principles'] = [SOC2Principle(p) for p in d['principles']]
                    logs.append(ComplianceAuditLog(**d))
            
            if len(logs) >= limit:
                break
        
        return logs
    
    def generate_audit_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Genere un rapport d'audit SOC 2"""
        logs = self.get_logs(start_date=start_date, end_date=end_date, limit=10000)
        
        # Statistics by principle
        by_principle = {p.value: 0 for p in SOC2Principle}
        for log in logs:
            for p in log.principles:
                by_principle[p.value] += 1
        
        # Statistics by event type
        by_event = {}
        for log in logs:
            evt = log.event_type.value
            by_event[evt] = by_event.get(evt, 0) + 1
        
        # Chain integrity
        integrity_ok, errors = self.verify_chain_integrity()
        
        return {
            "report_generated_at": datetime.now().isoformat(),
            "period": {
                "start": start_date,
                "end": end_date
            },
            "total_events": len(logs),
            "events_by_principle": by_principle,
            "events_by_type": by_event,
            "chain_integrity": {
                "verified": integrity_ok,
                "errors": errors[:10] if errors else []
            },
            "unique_users": len(set(log.user_id for log in logs)),
            "unique_resources": len(set(f"{log.resource_type}:{log.resource_id}" for log in logs))
        }


# ============================================================================
# COMPLIANCE FACADE
# ============================================================================

class ComplianceManager:
    """Facade pour toute la conformite (GDPR + SOC 2)"""
    
    def __init__(self, signing_key: bytes, data_dir: str = "./compliance_data"):
        self.data_dir = data_dir
        self.gdpr = GDPRComplianceManager(data_dir)
        self.soc2 = SOC2AuditManager(signing_key, f"{data_dir}/soc2")
    
    # GDPR convenience methods
    def record_consent(self, *args, **kwargs) -> ConsentRecord:
        consent = self.gdpr.record_consent(*args, **kwargs)
        
        # Log to SOC 2
        self.soc2.log_event(
            event_type=ComplianceEventType.CONSENT_GIVEN,
            user_id=consent.user_id,
            resource_type="consent",
            resource_id=consent.consent_id,
            action="create",
            details={"purposes": [p.value for p in consent.purposes]},
            principles=[SOC2Principle.PRIVACY]
        )
        
        return consent
    
    def submit_dsr(self, user_id: str, right: DataSubjectRight,
                  details: Dict = None) -> DataSubjectRequest:
        request = self.gdpr.submit_request(user_id, right, details)
        
        # Log to SOC 2
        event_type = {
            DataSubjectRight.ACCESS: ComplianceEventType.DATA_ACCESS_REQUEST,
            DataSubjectRight.ERASURE: ComplianceEventType.DATA_ERASURE_REQUEST,
            DataSubjectRight.PORTABILITY: ComplianceEventType.DATA_PORTABILITY_REQUEST,
        }.get(right, ComplianceEventType.DATA_ACCESS_REQUEST)
        
        self.soc2.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_type="dsr",
            resource_id=request.request_id,
            action="submit",
            details={"right": right.value},
            principles=[SOC2Principle.PRIVACY]
        )
        
        return request
    
    def report_breach(self, *args, **kwargs) -> DataBreach:
        breach = self.gdpr.report_breach(*args, **kwargs)
        
        # Log to SOC 2
        self.soc2.log_event(
            event_type=ComplianceEventType.BREACH_DETECTED,
            user_id="system",
            resource_type="breach",
            resource_id=breach.breach_id,
            action="detect",
            details={
                "risk_level": breach.risk_level,
                "subjects_affected": breach.subjects_affected_count
            },
            principles=[SOC2Principle.SECURITY, SOC2Principle.PRIVACY]
        )
        
        return breach
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Obtient le statut global de conformite"""
        integrity_ok, errors = self.soc2.verify_chain_integrity()
        
        return {
            "gdpr": {
                "consent_management": "active",
                "dsr_handling": "active",
                "breach_reporting": "active"
            },
            "soc2": {
                "audit_logging": "active",
                "chain_integrity": "ok" if integrity_ok else "compromised",
                "integrity_errors": len(errors)
            },
            "last_check": datetime.now().isoformat()
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_compliance_manager(signing_key: bytes, data_dir: str = "./compliance_data") -> ComplianceManager:
    """Cree un gestionnaire de conformite complet"""
    return ComplianceManager(signing_key, data_dir)
