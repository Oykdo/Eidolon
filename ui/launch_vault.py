#!/usr/bin/env python
"""
Lanceur de l'interface graphique Vault
Eidolon - Authentification Double Cle (.psnx + .blend_data)

Fonctionnalites:
- Authentification par fichier .psnx (donnees crypto) + .blend_data (structure 3D)
- Stockage securise de fichiers (AES-256-GCM)
- Wallet EVM integre (ERC20/NFT)
- 30,900 bits d'entropie
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from ui.vault_gui_complete import main
    main()
