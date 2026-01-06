"""
Tests for Poly-Spinor Nexus 7D
"""

import sys
import os

# Ajouter le répertoire parent au path pour les imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
