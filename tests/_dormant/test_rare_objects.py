#!/usr/bin/env python3
"""
Tests pour le système d'objets rares Eidolon
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Ajouter les chemins
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

try:
    import pytest
except ImportError:
    pytest = None


def test_rare_objects_models():
    """Test des modèles d'objets rares"""
    from core.rare_objects_models import (
        MainCategory, RarityClass, CertificationTier,
        ObjectCategory, ProvenanceEntry, ExhibitionEntry,
        CATEGORY_SPECIFICATIONS, get_rarity_description, get_category_icon,
        validate_category_data
    )
    
    # Test des énumérations
    assert MainCategory.HORLOGERIE.value == "horlogerie"
    assert RarityClass.UNIQUE.value == "unique"
    assert CertificationTier.EXPERT.value == 3
    
    # Test des descriptions de rareté
    desc = get_rarity_description(RarityClass.UNIQUE)
    assert "unique" in desc.lower()
    
    # Test des icônes
    icon = get_category_icon(MainCategory.JOAILLERIE)
    assert icon == "💎"
    
    # Test ObjectCategory
    category = ObjectCategory(
        main_category=MainCategory.HORLOGERIE,
        sub_category="montres_mecaniques",
        object_type="Montre de plongée",
        rarity_class=RarityClass.RARE
    )
    
    assert category.main_category == MainCategory.HORLOGERIE
    
    # Conversion dict
    cat_dict = category.to_dict()
    assert cat_dict['main_category'] == 'horlogerie'
    
    # Reconstruction
    cat_restored = ObjectCategory.from_dict(cat_dict)
    assert cat_restored.main_category == MainCategory.HORLOGERIE
    
    # Test spécifications
    specs = category.get_specifications()
    assert 'required_fields' in specs
    assert 'marque' in specs['required_fields']
    
    # Test ProvenanceEntry
    prov = ProvenanceEntry(
        owner_name="Musée du Louvre",
        owner_type="museum",
        acquisition_date="1920-01-01",
        acquisition_method="donation",
        location="Paris, France",
        verified=True
    )
    assert prov.to_dict()['owner_name'] == "Musée du Louvre"
    
    # Test validation
    valid, missing = validate_category_data(category, {
        'marque': 'Rolex',
        'modele': 'Submariner',
        'calibre': '3135',
        'fonctions': 'Date',
        'matiere_boitier': 'Acier',
        'diametre': 40
    })
    assert valid
    assert len(missing) == 0
    
    print("[PASS] test_rare_objects_models passed")


def test_universal_physical_fingerprint():
    """Test du système d'empreinte physique universelle"""
    from core.rare_objects_models import (
        MainCategory, RarityClass, ObjectCategory, DimensionalData
    )
    from core.universal_physical_fingerprint import (
        UniversalPhysicalFingerprint, UniversalFingerprintGenerator
    )
    
    generator = UniversalFingerprintGenerator()
    
    # Test création montre
    watch_fp = generator.create_from_watch(
        brand="Patek Philippe",
        model="Nautilus 5711",
        serial_number="PP5711-001234",
        caliber="324 S C",
        year="2020",
        case_material="Acier",
        diameter_mm=40.0
    )
    
    assert watch_fp.object_name == "Patek Philippe Nautilus 5711"
    assert watch_fp.holographic_fingerprint
    assert len(watch_fp.holographic_fingerprint) == 32
    assert watch_fp.category.main_category == MainCategory.HORLOGERIE
    
    # Test score de vérification
    score, checks = watch_fp.get_verification_score()
    assert score > 0
    assert 'has_name' in checks
    assert checks['has_name'] == True
    
    # Test création bijou
    jewelry_fp = generator.create_from_jewelry(
        name="Bague Solitaire",
        jeweler="Cartier",
        main_stone="Diamant",
        carat_weight=3.5,
        metal="Platine",
        certificate_number="GIA-12345678"
    )
    
    assert jewelry_fp.category.main_category == MainCategory.JOAILLERIE
    assert "Diamant" in jewelry_fp.capture_metadata.get('main_stone', '')
    
    # Test création œuvre d'art
    art_fp = generator.create_from_artwork(
        title="Les Nymphéas",
        artist="Claude Monet",
        technique="Huile sur toile",
        year="1906",
        dimensions=(200.0, 600.0)
    )
    
    assert art_fp.category.main_category == MainCategory.ART
    assert art_fp.category.rarity_class == RarityClass.UNIQUE
    assert art_fp.dimensional_data.height_mm == 200.0
    
    # Test création vin
    wine_fp = generator.create_from_wine(
        domain="Domaine de la Romanée-Conti",
        vintage="1945",
        appellation="Romanée-Conti Grand Cru",
        bottle_number="123"
    )
    
    assert wine_fp.category.main_category == MainCategory.VIN_SPIRITUEUX
    
    # Test serialization
    fp_dict = watch_fp.to_dict()
    assert 'holographic_fingerprint' in fp_dict
    
    fp_restored = UniversalPhysicalFingerprint.from_dict(fp_dict)
    assert fp_restored.holographic_fingerprint == watch_fp.holographic_fingerprint
    
    print("[PASS] test_universal_physical_fingerprint passed")


def test_rare_objects_registry():
    """Test du registre d'objets rares"""
    from core.rare_objects_models import MainCategory, RarityClass
    from core.universal_physical_fingerprint import UniversalFingerprintGenerator
    from core.rare_objects_registry import RareObjectsRegistry
    
    # Créer un registre temporaire
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = RareObjectsRegistry(storage_dir=tmpdir)
        generator = UniversalFingerprintGenerator()
        
        # Créer et enregistrer des objets
        watch = generator.create_from_watch(
            brand="Audemars Piguet",
            model="Royal Oak",
            serial_number="AP-RO-001",
            year="2021"
        )
        
        success, msg, record = registry.register_object(
            watch, tags=["iconic", "sports"]
        )
        assert success
        assert record.object_name == "Audemars Piguet Royal Oak"
        
        # Test double enregistrement
        success2, msg2, _ = registry.register_object(watch)
        assert not success2
        assert "already registered" in msg2.lower()
        
        # Enregistrer un deuxième objet
        jewelry = generator.create_from_jewelry(
            name="Collier Diamants",
            jeweler="Van Cleef",
            main_stone="Diamant",
            carat_weight=10.0
        )
        jewelry.category.rarity_class = RarityClass.ULTRA_RARE
        
        registry.register_object(jewelry, tags=["diamonds"])
        
        # Test recherche
        results = registry.search_objects(query="Royal")
        assert len(results) == 1
        assert results[0].object_name == "Audemars Piguet Royal Oak"
        
        # Test recherche par catégorie
        horlo = registry.search_objects(category="horlogerie")
        assert len(horlo) == 1
        
        joail = registry.search_objects(category="joaillerie")
        assert len(joail) == 1
        
        # Test get_object
        obj = registry.get_object(watch.object_id)
        assert obj is not None
        assert obj.object_name == watch.object_name
        
        # Test get_by_fingerprint
        obj2 = registry.get_by_fingerprint(watch.holographic_fingerprint)
        assert obj2 is not None
        
        # Test similar objects
        similar = registry.get_similar_objects(watch.object_id)
        # Pas d'objets similaires dans ce petit dataset
        
        # Test timeline
        timeline = registry.get_object_timeline(watch.object_id)
        assert len(timeline) > 0
        assert any(e['event_type'] == 'certification' for e in timeline)
        
        # Test statistiques
        stats = registry.get_statistics()
        assert stats.total_objects == 2
        assert stats.objects_by_category.get('horlogerie') == 1
        
        # Test rapport de rareté
        report = registry.generate_rarity_report(jewelry.object_id)
        assert report['rarity_class'] == 'ultra_rare'
        assert report['rarity_score'] == 95
        
        # Test collections
        coll = registry.create_collection(
            name="Ma Collection",
            description="Collection test",
            theme="Montres de luxe",
            owner_id="user_123",
            object_ids=[watch.object_id]
        )
        assert coll.collection_id
        
        retrieved_coll = registry.get_collection(coll.collection_id)
        assert retrieved_coll.name == "Ma Collection"
        
        # Test category summary
        summary = registry.get_category_summary()
        assert len(summary) > 0
        
    print("[PASS] test_rare_objects_registry passed")


def test_certification_system():
    """Test du système de certification"""
    from core.rare_objects_models import MainCategory, CertificationTier
    from core.universal_physical_fingerprint import UniversalFingerprintGenerator
    from core.rare_objects_certification import (
        CertificationService, CertificationStatus,
        get_capture_protocols, CERTIFICATION_PRICES
    )
    
    generator = UniversalFingerprintGenerator()
    
    # Test protocoles de capture
    protocols_basic = get_capture_protocols(MainCategory.HORLOGERIE, CertificationTier.BASIC)
    assert len(protocols_basic) >= 1
    assert any(p.protocol.value == "photo_standard" for p in protocols_basic)
    
    protocols_expert = get_capture_protocols(MainCategory.HORLOGERIE, CertificationTier.EXPERT)
    assert len(protocols_expert) > len(protocols_basic)
    
    # Test tarification
    assert CERTIFICATION_PRICES[CertificationTier.BASIC]['base_price'] == 99.0
    assert CERTIFICATION_PRICES[CertificationTier.EXPERT]['base_price'] == 1999.0
    
    # Créer un service temporaire
    with tempfile.TemporaryDirectory() as tmpdir:
        service = CertificationService(storage_dir=tmpdir)
        
        # Créer un objet
        watch = generator.create_from_watch(
            brand="Vacheron Constantin",
            model="Overseas",
            serial_number="VC-OV-001",
            year="2022"
        )
        
        # Créer une demande
        success, msg, request = service.create_certification_request(
            fingerprint=watch,
            tier=CertificationTier.ADVANCED,
            requester_id="user_456"
        )
        
        assert success
        assert request.status == CertificationStatus.PENDING
        assert request.price_paid == 499.0
        assert len(request.capture_requirements) > 0
        
        # Récupérer la demande
        req = service.get_request(request.request_id)
        assert req is not None
        assert req.object_id == watch.object_id
        
        # Assigner un expert
        service.assign_expert(request.request_id, "expert_001")
        req = service.get_request(request.request_id)
        assert req.assigned_expert == "expert_001"
        assert req.status == CertificationStatus.IN_PROGRESS
        
        # Enregistrer des captures
        service.record_capture_completed(request.request_id, "photo_standard")
        req = service.get_request(request.request_id)
        assert "photo_standard" in req.captures_completed
        
        # Mettre à jour le statut
        service.update_request_status(
            request.request_id, 
            CertificationStatus.AWAITING_REVIEW,
            notes="Captures complètes, prêt pour revue"
        )
        
        req = service.get_request(request.request_id)
        assert req.status == CertificationStatus.AWAITING_REVIEW
        assert len(req.expert_notes) > 0
        
        # Émettre le certificat
        success, msg, certificate = service.issue_certificate(
            request=req,
            fingerprint=watch,
            expert_remarks="Objet authentique, état excellent"
        )
        
        assert success
        assert certificate is not None
        assert certificate.is_valid()
        assert certificate.certification_tier == CertificationTier.ADVANCED
        
        # Vérifier le certificat
        verification = service.verify_certificate(certificate.certificate_id)
        assert verification['valid'] == True
        assert verification['tier'] == 2
        
        # Test révocation
        service.revoke_certificate(certificate.certificate_id, "Test révocation")
        verification2 = service.verify_certificate(certificate.certificate_id)
        assert verification2['valid'] == False
        
    print("[PASS] test_certification_system passed")


def test_marketplace():
    """Test du marketplace"""
    from core.rare_objects_models import MainCategory, CertificationTier
    from core.universal_physical_fingerprint import UniversalFingerprintGenerator
    from core.rare_objects_certification import Certificate
    from core.rare_objects_marketplace import (
        RareObjectsMarketplace, SaleType, Currency, 
        ListingStatus, TransactionStatus, PLATFORM_FEES
    )
    
    generator = UniversalFingerprintGenerator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        marketplace = RareObjectsMarketplace(storage_dir=tmpdir)
        
        # Créer un objet et un certificat
        watch = generator.create_from_watch(
            brand="Omega",
            model="Speedmaster Moonwatch",
            serial_number="OMEGA-SM-001",
            year="1969"
        )
        
        # Créer un certificat (simulé)
        certificate = Certificate(
            certificate_id="CERT-001",
            object_id=watch.object_id,
            fingerprint_hash=watch.holographic_fingerprint,
            certification_tier=CertificationTier.EXPERT,
            issued_at="2024-01-01T00:00:00",
            valid_until="2034-01-01T00:00:00",
            object_name=watch.object_name,
            object_category="horlogerie",
            creator_maker="Omega",
            verification_score=85.0,
            rarity_score=80
        )
        
        # Test calcul des frais
        fees = marketplace.get_fees_for_price(10000)
        assert fees['buyer_premium'] == 500.0  # 5%
        assert fees['seller_commission'] == 1000.0  # 10%
        
        # Créer un listing
        success, msg, listing = marketplace.create_listing(
            fingerprint=watch,
            certificate=certificate,
            seller_id="seller_001",
            seller_name="Montre Vintage Paris",
            sale_type=SaleType.FIXED_PRICE,
            price=25000.0,
            currency=Currency.EUR,
            description="Omega Speedmaster historique, premier modèle lunaire",
            location_country="France",
            location_city="Paris"
        )
        
        assert success
        assert listing.status == ListingStatus.DRAFT
        assert listing.price == 25000.0
        
        # Publier le listing
        success, msg = marketplace.publish_listing(listing.listing_id)
        assert success
        
        listing = marketplace.get_listing(listing.listing_id)
        assert listing.status == ListingStatus.ACTIVE
        
        # Rechercher
        results = marketplace.search_listings(query="Speedmaster")
        assert len(results) == 1
        
        results = marketplace.search_listings(category="horlogerie")
        assert len(results) == 1
        
        results = marketplace.search_listings(min_price=30000)
        assert len(results) == 0
        
        # Initier un achat
        success, msg, transaction = marketplace.initiate_purchase(
            listing_id=listing.listing_id,
            buyer_id="buyer_001"
        )
        
        assert success
        assert transaction.status == TransactionStatus.INITIATED
        assert transaction.amount == 25000.0
        assert 'buyer_premium' in transaction.fees
        
        # Vérifier que le listing est réservé
        listing = marketplace.get_listing(listing.listing_id)
        assert listing.status == ListingStatus.RESERVED
        
        # Simuler le flux de transaction
        marketplace.update_transaction_status(
            transaction.transaction_id, 
            TransactionStatus.PAYMENT_RECEIVED
        )
        
        marketplace.update_transaction_status(
            transaction.transaction_id,
            TransactionStatus.COMPLETED
        )
        
        # Vérifier listing vendu
        listing = marketplace.get_listing(listing.listing_id)
        assert listing.status == ListingStatus.SOLD
        
        # Vérifier historique des prix
        history = marketplace.get_price_history(watch.object_id)
        assert len(history) >= 2  # listing + sale
        
        # Test alertes
        alert = marketplace.create_search_alert(
            user_id="user_789",
            criteria={
                'category': 'horlogerie',
                'max_price': 50000
            }
        )
        assert alert.alert_id
        
        # Test stats marché
        stats = marketplace.get_market_stats()
        assert 'total_listings' in stats
        
    print("[PASS] test_marketplace passed")


def test_auction():
    """Test du système d'enchères"""
    from core.rare_objects_models import CertificationTier
    from core.universal_physical_fingerprint import UniversalFingerprintGenerator
    from core.rare_objects_certification import Certificate
    from core.rare_objects_marketplace import (
        RareObjectsMarketplace, SaleType, Currency, ListingStatus
    )
    
    generator = UniversalFingerprintGenerator()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        marketplace = RareObjectsMarketplace(storage_dir=tmpdir)
        
        # Créer un objet pour enchères
        art = generator.create_from_artwork(
            title="Nature Morte aux Fleurs",
            artist="Vincent van Gogh",
            technique="Huile sur toile",
            year="1888"
        )
        
        cert = Certificate(
            certificate_id="CERT-ART-001",
            object_id=art.object_id,
            fingerprint_hash=art.holographic_fingerprint,
            certification_tier=CertificationTier.EXPERT,
            issued_at="2024-01-01T00:00:00",
            valid_until="2034-01-01T00:00:00",
            object_name=art.object_name,
            object_category="art",
            creator_maker="Vincent van Gogh",
            verification_score=95.0,
            rarity_score=100
        )
        
        # Créer un listing aux enchères
        success, msg, listing = marketplace.create_listing(
            fingerprint=art,
            certificate=cert,
            seller_id="gallery_001",
            seller_name="Galerie Impressionniste",
            sale_type=SaleType.AUCTION,
            price=5000000.0,  # Prix de départ
            currency=Currency.EUR,
            reserve_price=8000000.0,
            location_country="France"
        )
        
        assert success
        assert listing.sale_type == SaleType.AUCTION
        
        marketplace.publish_listing(listing.listing_id)
        
        # Placer des enchères
        success1, msg1, bid1 = marketplace.place_bid(
            listing_id=listing.listing_id,
            bidder_id="bidder_001",
            amount=5500000.0
        )
        assert success1
        assert bid1.is_winning
        
        success2, msg2, bid2 = marketplace.place_bid(
            listing_id=listing.listing_id,
            bidder_id="bidder_002",
            amount=6000000.0
        )
        assert success2
        assert bid2.is_winning
        
        # Vérifier que l'enchère précédente n'est plus gagnante
        bids = marketplace._get_bids_for_listing(listing.listing_id)
        assert len(bids) == 2
        assert bids[0].amount == 6000000.0
        assert bids[0].is_winning
        
        # Enchère trop basse
        success3, msg3, _ = marketplace.place_bid(
            listing_id=listing.listing_id,
            bidder_id="bidder_003",
            amount=5000000.0
        )
        assert not success3
        assert "higher" in msg3.lower()
        
    print("[PASS] test_auction passed")


if __name__ == "__main__":
    test_rare_objects_models()
    test_universal_physical_fingerprint()
    test_rare_objects_registry()
    test_certification_system()
    test_marketplace()
    test_auction()
    
    print("\n" + "="*50)
    print("[PASS] All rare objects tests passed!")
    print("="*50)
