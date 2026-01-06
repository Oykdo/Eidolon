"""Affiche les glyphes d'un artefact"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json
from pathlib import Path

def main():
    block_file = Path(__file__).parent.parent / 'genesis_data/blocks/block_00000001.json'
    with open(block_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    art = data.get('artifact', {})
    ga = art.get('glyph_array', {})

    print('=== VAULT #1 PRIMORDIAL ARTIFACT ===')
    print('Name:', art.get('name'))
    print('Rarity:', art.get('rarity', '').upper())
    stats = art.get('stats', {})
    print('Power:', f"{stats.get('effective_power', 0):,.0f}")
    print()
    print('GLYPH ARRAY:')
    print('  Total Gems:', ga.get('total_gems'))
    print('  Glyph Power:', f"{ga.get('total_power', 0):,.0f}")
    print('  Bell Correlation:', ga.get('bell_correlation', 0))
    print()
    print('7 GLYPHS avec 21 GEMMES:')
    
    glyph_symbols = {
        'glyph_void': 'ᛟ', 'glyph_quantum': 'ᚠ', 'glyph_temporal': 'ᛞ',
        'glyph_spatial': 'ᚱ', 'glyph_entropic': 'ᚺ', 'glyph_harmonic': 'ᚹ',
        'glyph_celestial': 'ᛊ'
    }
    
    for g in ga.get('glyphs', []):
        gtype = g.get('glyph_type', '')
        symbol = glyph_symbols.get(gtype, '?')
        gname = gtype.replace('glyph_', '').upper()
        pwr = g.get('total_power', 0)
        gems = g.get('gems', [])
        
        print(f'  {symbol} D{g.get("dimension")}: {gname:10} | PWR:{pwr:>6,.0f}')
        
        for gem in gems:
            gt = gem.get('gem_type', '').replace('_', ' ').title()
            gr = gem.get('rarity', '').upper()[:4]
            gp = gem.get('base_power', 0)
            res = gem.get('resonance', 0)
            pur = gem.get('purity', 0)
            special = gem.get('special_effect', '')
            
            special_str = f' [{special}]' if special else ''
            print(f'      [{gr}] {gt}: PWR {gp:.0f} | RES {res:.0f}% | PUR {pur:.0f}%{special_str}')

if __name__ == '__main__':
    main()
