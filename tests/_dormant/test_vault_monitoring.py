"""Test du système de monitoring Vault NFT"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from poly_spinor_nexus_7d.protocols.vault_monitoring import (
    VaultMonitoringSystem,
    EventType,
    AlertSeverity,
    AlertRule,
    create_vault_monitoring
)


def test_event_emission():
    """Test d'émission d'événements"""
    print("\n--- Test Émission d'Événements ---")
    
    monitor = create_vault_monitoring()
    
    # Émettre un événement d'accès
    event = monitor.emit_event(
        event_type=EventType.VAULT_ACCESS,
        source="test_suite",
        details={'match_score': 0.995, 'access_level': 'admin'},
        user_id="user_123",
        resource_id="vault_abc"
    )
    
    print(f"Événement créé: {event.event_id}")
    print(f"Type: {event.event_type.value}")
    print(f"Timestamp: {event.timestamp}")
    
    # Vérifier que l'événement est enregistré
    events = monitor.get_events(event_type=EventType.VAULT_ACCESS)
    assert len(events) == 1, "Événement non enregistré!"
    print(f"[OK] {len(events)} événement(s) enregistré(s)")
    
    monitor.shutdown()
    print("[OK] Émission d'événements fonctionne")
    return True


def test_alert_generation():
    """Test de génération d'alertes"""
    print("\n--- Test Génération d'Alertes ---")
    
    monitor = create_vault_monitoring()
    
    # Émettre un événement qui devrait déclencher une alerte
    event = monitor.emit_event(
        event_type=EventType.VAULT_ACCESS_DENIED,
        source="test_suite",
        details={'match_score': 0.45, 'reason': 'fingerprint_mismatch'},
        user_id="attacker_456",
        resource_id="vault_xyz",
        severity=AlertSeverity.WARNING
    )
    
    print(f"Événement access_denied émis: {event.event_id}")
    
    # Vérifier qu'une alerte a été générée
    alerts = monitor.get_active_alerts()
    print(f"Alertes actives: {len(alerts)}")
    
    if alerts:
        alert = alerts[0]
        print(f"  - ID: {alert.alert_id}")
        print(f"  - Sévérité: {alert.severity.value}")
        print(f"  - Titre: {alert.title}")
    
    assert len(alerts) >= 1, "Alerte non générée!"
    print("[OK] Alertes générées correctement")
    
    monitor.shutdown()
    return True


def test_critical_alert():
    """Test d'alerte critique"""
    print("\n--- Test Alerte Critique ---")
    
    monitor = create_vault_monitoring()
    
    # Émettre un événement de breach
    event = monitor.emit_event(
        event_type=EventType.SECURITY_BREACH_ATTEMPT,
        source="intrusion_detection",
        details={'ip': '192.168.1.100', 'method': 'brute_force'},
        user_id="unknown",
        resource_id="vault_main",
        severity=AlertSeverity.CRITICAL
    )
    
    print(f"Événement breach émis")
    
    # Vérifier l'alerte critique
    critical_alerts = monitor.get_active_alerts(severity=AlertSeverity.CRITICAL)
    print(f"Alertes critiques: {len(critical_alerts)}")
    
    assert len(critical_alerts) >= 1, "Alerte critique non générée!"
    print("[OK] Alertes critiques fonctionnent")
    
    monitor.shutdown()
    return True


def test_alert_acknowledgement():
    """Test d'acquittement d'alertes"""
    print("\n--- Test Acquittement d'Alertes ---")
    
    monitor = create_vault_monitoring()
    
    # Générer une alerte
    monitor.emit_event(
        event_type=EventType.VAULT_ACCESS_DENIED,
        source="test",
        details={'match_score': 0.3},
        user_id="test_user"
    )
    
    alerts = monitor.get_active_alerts()
    assert len(alerts) > 0, "Pas d'alerte à acquitter!"
    
    alert_id = alerts[0].alert_id
    print(f"Alerte à acquitter: {alert_id}")
    
    # Acquitter
    result = monitor.acknowledge_alert(alert_id, "admin_user")
    assert result, "Acquittement échoué!"
    print("[OK] Alerte acquittée")
    
    # Vérifier
    alert = next(a for a in monitor.alerts if a.alert_id == alert_id)
    assert alert.acknowledged, "Flag acknowledged non mis!"
    assert alert.acknowledged_by == "admin_user", "acknowledged_by incorrect!"
    print(f"[OK] Acquittée par: {alert.acknowledged_by}")
    
    # Résoudre
    result = monitor.resolve_alert(alert_id)
    assert result, "Résolution échouée!"
    
    active = monitor.get_active_alerts()
    resolved_alert = next(a for a in monitor.alerts if a.alert_id == alert_id)
    assert resolved_alert.resolved, "Alerte non résolue!"
    print("[OK] Alerte résolue")
    
    monitor.shutdown()
    return True


def test_metrics_collection():
    """Test de collecte de métriques"""
    print("\n--- Test Collecte de Métriques ---")
    
    monitor = create_vault_monitoring()
    
    # Émettre plusieurs événements
    for i in range(5):
        monitor.emit_event(
            event_type=EventType.VAULT_ACCESS,
            source="test",
            details={'match_score': 0.99},
            user_id=f"user_{i}"
        )
    
    for i in range(3):
        monitor.emit_event(
            event_type=EventType.VAULT_ACCESS_DENIED,
            source="test",
            details={'match_score': 0.4},
            user_id=f"bad_user_{i}"
        )
    
    # Récupérer les métriques Prometheus
    prometheus_output = monitor.metrics.get_metrics_prometheus()
    print("Métriques Prometheus:")
    for line in prometheus_output.split('\n')[:10]:
        print(f"  {line}")
    
    assert 'vault_events_total' in prometheus_output, "Métrique events_total manquante!"
    assert 'vault_access_total' in prometheus_output, "Métrique access_total manquante!"
    print("[OK] Métriques collectées")
    
    monitor.shutdown()
    return True


def test_nft_registry():
    """Test du registre NFT"""
    print("\n--- Test Registre NFT ---")
    
    monitor = create_vault_monitoring()
    
    # Enregistrer un NFT
    nft = monitor.nft_registry.register_nft(
        nft_id="nft_001",
        document_hash="abc123def456",
        owner_id="alice",
        vault_id="vault_main",
        metadata={'title': 'Document Important'}
    )
    
    print(f"NFT créé: {nft.nft_id}")
    print(f"Propriétaire: {nft.owner_id}")
    print(f"Status: {nft.status}")
    
    # Transférer le NFT
    nft = monitor.nft_registry.transfer_nft(
        nft_id="nft_001",
        new_owner_id="bob",
        transfer_metadata={'reason': 'sale'}
    )
    
    print(f"Nouveau propriétaire: {nft.owner_id}")
    print(f"Historique: {len(nft.transfer_history)} transfert(s)")
    assert nft.owner_id == "bob", "Transfert échoué!"
    print("[OK] Transfert NFT réussi")
    
    # Verrouiller
    nft = monitor.nft_registry.lock_nft("nft_001")
    assert nft.status == "locked", "Verrouillage échoué!"
    print("[OK] NFT verrouillé")
    
    # Déverrouiller
    nft = monitor.nft_registry.unlock_nft("nft_001")
    assert nft.status == "active", "Déverrouillage échoué!"
    print("[OK] NFT déverrouillé")
    
    # Rechercher par propriétaire
    bob_nfts = monitor.nft_registry.get_nfts_by_owner("bob")
    assert len(bob_nfts) == 1, "Recherche par owner échouée!"
    print(f"[OK] NFTs de bob: {len(bob_nfts)}")
    
    monitor.shutdown()
    return True


def test_health_status():
    """Test du statut de santé"""
    print("\n--- Test Statut de Santé ---")
    
    monitor = create_vault_monitoring()
    
    # État initial (devrait être healthy)
    health = monitor.get_health_status()
    print(f"Status: {health['status']}")
    print(f"Score: {health['health_score']}")
    print(f"Alertes actives: {health['active_alerts']}")
    
    assert health['status'] == 'healthy', "Devrait être healthy au départ!"
    assert health['health_score'] == 100, "Score devrait être 100!"
    print("[OK] Système healthy")
    
    # Générer des alertes critiques
    for _ in range(2):
        monitor.emit_event(
            event_type=EventType.SECURITY_BREACH_ATTEMPT,
            source="test",
            details={},
            severity=AlertSeverity.CRITICAL
        )
    
    health = monitor.get_health_status()
    print(f"\nAprès alertes critiques:")
    print(f"Status: {health['status']}")
    print(f"Score: {health['health_score']}")
    print(f"Alertes critiques: {health['critical_alerts']}")
    
    assert health['health_score'] < 100, "Score devrait avoir diminué!"
    print("[OK] Dégradation détectée")
    
    monitor.shutdown()
    return True


def test_dashboard_data():
    """Test des données dashboard"""
    print("\n--- Test Données Dashboard ---")
    
    monitor = create_vault_monitoring()
    
    # Générer de l'activité
    users = ['alice', 'bob', 'charlie']
    for user in users:
        for _ in range(3):
            monitor.emit_event(
                event_type=EventType.VAULT_ACCESS,
                source="app",
                details={'match_score': 0.99},
                user_id=user
            )
    
    # Récupérer les données dashboard
    dashboard = monitor.get_dashboard_data()
    
    print("Données Dashboard:")
    print(f"  Health status: {dashboard['health']['status']}")
    print(f"  Event counts: {dashboard['event_counts_24h']}")
    print(f"  Top users: {dashboard['top_active_users'][:3]}")
    print(f"  Recent events: {len(dashboard['recent_events'])}")
    
    assert 'vault_access' in dashboard['event_counts_24h'], "Compteur manquant!"
    assert len(dashboard['top_active_users']) > 0, "Top users vide!"
    print("[OK] Données dashboard complètes")
    
    monitor.shutdown()
    return True


def test_webhook_registration():
    """Test d'enregistrement de webhooks"""
    print("\n--- Test Webhooks ---")
    
    monitor = create_vault_monitoring()
    
    # Enregistrer un webhook
    monitor.webhooks.register_webhook(
        webhook_id="slack_alerts",
        url="https://hooks.slack.com/example",
        events=[EventType.SECURITY_BREACH_ATTEMPT, EventType.SEAL_COMPROMISED],
        min_severity=AlertSeverity.ERROR
    )
    
    monitor.webhooks.register_webhook(
        webhook_id="all_events",
        url="https://monitoring.example.com/webhook",
        min_severity=AlertSeverity.INFO
    )
    
    print(f"Webhooks enregistrés: {len(monitor.webhooks.webhooks)}")
    
    # Émettre un événement (devrait notifier)
    monitor.emit_event(
        event_type=EventType.VAULT_ACCESS,
        source="test",
        details={},
        severity=AlertSeverity.INFO
    )
    
    # Laisser le temps au worker
    time.sleep(0.5)
    
    print("[OK] Webhooks configurés")
    
    monitor.shutdown()
    return True


def main():
    print("=== TEST VAULT MONITORING SYSTEM ===")
    
    tests = [
        ("Émission d'événements", test_event_emission),
        ("Génération d'alertes", test_alert_generation),
        ("Alertes critiques", test_critical_alert),
        ("Acquittement alertes", test_alert_acknowledgement),
        ("Collecte métriques", test_metrics_collection),
        ("Registre NFT", test_nft_registry),
        ("Statut de santé", test_health_status),
        ("Données dashboard", test_dashboard_data),
        ("Webhooks", test_webhook_registration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n=== SUMMARY ===")
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n=== MONITORING SYSTEM READY ===")
    
    return all_passed


if __name__ == "__main__":
    main()
