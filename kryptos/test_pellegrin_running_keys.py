import json
from buttcrack.engine import resolve_scorer
from buttcrack.ciphers.columnar import _decode_units

with open('pk_all_ciphertexts.json') as f:
    cts = json.load(f)
pk9 = cts['PK9']
M = _decode_units(pk9, [3, 5, 1, 4, 2, 0], unit=3)
scorer = resolve_scorer('quadgrams', 'english')

ALPH_K = 'KRYPTOSABCDEFGHIJLMNQUVWXZ'
ALPH_S = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

sources = [
    "LAFLEURDELASCIENCEDEPOURTRAICTUREETPATRONSDEBRODERIEFACONARABICQUEETYTALIQUE",
    "ENLAGRANTRUESAINCTANTHOYNEDEVANTLESTOURNELLESAULOGISDEMONSEIGNEURLECONTEDECARPES",
    "PRIVILEGEDUROYFRANCOISPREMIERPOURSIXANSIMPRIMEPARJACQUESNYVERDETVENDUPARLAUTEUR",
    "CEPRESENTLIVREAESTEIMPRIMEAPARISPARJACQUESNYVERDDEMOURANTENLARUEDELAJUYFRIEALENSEIGNEDELAROSEDOR",
    "UNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODO",
    "UNAGOTANTOSOTTILEDELEGGEREQUALUNQUENODO",
    "UNAGOTANTOSOTTILEDALEGGEREOGNINODO",
    "FRANCISQUEPELLEGRINDEFLORENCEPEINTRELEFLORENTIN",
    "FRANCESCODIPELLEGRINOILFIORENTINOPITTOREESCULTORE",
    "FONTAINEBLEAUROSSLOROSSOFRANCOISPREMIER",
    "ALBERTOP IOCONTEDECARPIROSEDOR",
    "PATRONSDEBRODERIEFACONARABICQUEETYTALIQUEPARFRANCISQUEPELLEGRIN",
    "LAFLEURDELASCIENCEDEPOURTRAICTURE",
    "PATRONSDEBRODERIE",
    "FACONARABICQUEETYTALIQUE",
    "JACQUESNYVERD",
    "FRANCISQUEPELLEGRIN",
    "FRANCESCODIPELLEGRINO",
    "CONTEDECARPI",
    "LECONTE DECARPES",
    "RUESAINCTANTHOYNE",
    "DEVANTLESTOURNELLES",
    "AULOGISDEMONSEIGNEUR"
]

print(f"Loaded {len(sources)} candidate running key texts.")

targets = [("Stream M", M), ("Raw C", pk9)]
alphabets = [("KRYPTOS", ALPH_K), ("STANDARD", ALPH_S)]

def dec(c, k, alph, mode):
    ci = alph.index(c)
    ki = alph.index(k)
    if mode == 'vigenere': return alph[(ci - ki) % 26]
    elif mode == 'beaufort': return alph[(ki - ci) % 26]
    elif mode == 'variant': return alph[(ci + ki) % 26]

best_sc = -999.0
best_hit = ""

for t_name, text in targets:
    for a_name, alph in alphabets:
        for mode in ['vigenere', 'beaufort', 'variant']:
            for s in sources:
                clean_s = "".join(ch for ch in s.upper() if ch.isalpha())
                if len(clean_s) < 14: continue
                # Test repeating key
                L = len(clean_s)
                pt = "".join(dec(text[i], clean_s[i % L], alph, mode) for i in range(len(text)))
                sc = scorer.average(pt)
                if sc > best_sc:
                    best_sc = sc
                    best_hit = f"Repeating | {t_name} | {a_name} | {mode} | {clean_s[:20]}... sc={sc:.3f}"
                    print(f"New Best: {best_hit}\n  PT: {pt[:65]}...")
                if sc > -6.0:
                    print(f"!!! HIT !!! {best_hit}\nFULL PT: {pt}")

                # Test running key from offset 0
                max_len = min(len(text), len(clean_s))
                if max_len >= 30:
                    pt_run = "".join(dec(text[i], clean_s[i], alph, mode) for i in range(max_len))
                    sc_run = scorer.average(pt_run)
                    if sc_run > best_sc:
                        best_sc = sc_run
                        best_hit = f"Running | {t_name} | {a_name} | {mode} | {clean_s[:20]}... sc={sc_run:.3f}"
                        print(f"New Best: {best_hit}\n  PT: {pt_run[:65]}...")
                    if sc_run > -6.0:
                        print(f"!!! RUNNING HIT !!! {best_hit}\nFULL PT: {pt_run}")

print(f"\nFinal Best overall: {best_hit}")
