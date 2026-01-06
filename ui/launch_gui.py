#!/usr/bin/env python3
"""
Lanceur d'Interface Graphique - Poly-Spinor Nexus 7D
Connexion automatique avec votre cle vault
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("="*60)
    print("  POLY-SPINOR NEXUS 7D - INTERFACE GRAPHIQUE")
    print("="*60)
    
    # Fichiers de cle
    psnx_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.psnx'
    blend_path = 'vault_storage/keys/vault_key_monvaultsecurise_0d3e2fa2.blend_data'
    
    # Verifier les fichiers
    if not os.path.exists(psnx_path):
        print(f"\n[ERREUR] Fichier PSNX non trouve: {psnx_path}")
        print("Generez d'abord une cle avec: python scripts/generate_key.py")
        return
    
    if not os.path.exists(blend_path):
        print(f"\n[ERREUR] Fichier Blend non trouve: {blend_path}")
        return
    
    print(f"\n[1] Chargement de la cle...")
    print(f"    PSNX: {psnx_path}")
    print(f"    Blend: {blend_path}")
    
    # Charger la cle
    from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
    
    generator = CompletePolySpinorKeyGenerator()
    file_gen = CompleteKeyFileGenerator(generator)
    key_data, vault_key = file_gen.extract_key_from_file(psnx_path)
    
    print(f"\n[2] Cle chargee!")
    print(f"    Vault: {key_data.user_name}")
    print(f"    Key ID: {key_data.key_id}")
    print(f"    Entropie: {key_data.total_entropy_bits:,} bits")
    
    print(f"\n[3] Lancement de l'interface graphique...")
    print("    (Fermez la fenetre pour quitter)")
    
    # Lancer l'interface
    try:
        from ui.vault_monitor import VaultMonitorGUI
        gui = VaultMonitorGUI(vault_key, key_data.user_name)
        gui.run()
    except ImportError as e:
        print(f"\n[ERREUR] Module UI non disponible: {e}")
        print("\nTentative avec l'interface alternative...")
        
        try:
            from ui.vault_gui_complete import VaultGUIComplete
            gui = VaultGUIComplete(vault_key, key_data.user_name)
            gui.run()
        except ImportError as e2:
            print(f"[ERREUR] Interface alternative non disponible: {e2}")
            print("\nVerifiez que tkinter est installe:")
            print("  pip install tk")
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
