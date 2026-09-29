import numpy as np, sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.additive_crib import _alphabet

pk10 = 'UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ'
N = len(pk10)

alpha_kr = _alphabet('KRYPTOS')
k2i = {c: i for i, c in enumerate(alpha_kr)}
ct_kr = np.array([k2i[c] % 13 for c in pk10], dtype=int)

def slice_ioc(stream, p):
    total_num = 0
    total_den = 0
    for rem in range(p):
        sub = stream[rem::p]
        if len(sub) > 1:
            bc = np.bincount(sub, minlength=13)
            total_num += np.sum(bc * (bc - 1))
            total_den += len(sub) * (len(sub) - 1)
    return total_num / total_den if total_den > 0 else 0.0

def word_to_order(word):
    used = [False] * len(word)
    order = []
    for c in sorted(list(set(word))):
        for i, ch in enumerate(word):
            if ch == c:
                order.append(i)
    return order

thematic_phrases = [
    'PROVENANCE', 'KRYPTOS', 'PORTAL', 'PALIMPSEST', 'ABSCISSA', 'SHADOWFORCES',
    'ARCHIVEOFPELLEGRIN', 'THELOSTARCHIVE', 'THEWHITESMITH', 'NINEDAYS',
    'FIFTHNEEDLE', 'PELLEGRIN', 'THEOPHILUS', 'DEDIVERSISARTIBUS',
    'UNAGOTANTOSOTTILE', 'RESIDUEOFHISPRACTICE', 'ONEOFMYOWNMAKING',
    'CELESTIALCOORDINATES', 'SWISSALPS', 'TWELVEKNOTS', 'ANATOMIST',
    'SURGICALDEMONSTRATION', 'INVESTIGATIONLOG', 'DRAWPLATE', 'TEMPERING',
    'PURIFIEDSTEEL', 'GLOWINGCOALS', 'WHITEHEAT', 'NEEDLEANDTHREAD'
]

print(f"Testing {len(thematic_phrases)} thematic keywords on PK10...")

for phrase in thematic_phrases:
    w = len(phrase)
    if N % w != 0:
        continue
    H = N // w
    order = word_to_order(phrase)
    
    # Decrypt columnar
    grid = np.zeros((H, w), dtype=int)
    idx = 0
    for c in range(w):
        col = order[c]
        grid[:, col] = ct_kr[idx : idx + H]
        idx += H
    stream = grid.flatten()
    
    ioc7 = slice_ioc(stream, 7)
    ioc8 = slice_ioc(stream, 8)
    ioc9 = slice_ioc(stream, 9)
    trip = ioc7 + ioc8 + ioc9
    
    print(f"[{phrase:22s}] W={w:2d}, H={H:2d}: IoC7={ioc7:.4f}, IoC8={ioc8:.4f}, IoC9={ioc9:.4f} | Trip={trip:.4f}")
    if trip > 0.25:
        print(f"  >>> ELEVATED HIT on {phrase}! <<<")
