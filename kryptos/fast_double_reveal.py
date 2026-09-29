import sys
sys.path.insert(0, 'buttcrack/src')
from buttcrack.transsub import _undo_double, reveal_score
from buttcrack.ciphers.columnar import _read_order
import json

with open('pk_all_ciphertexts.json') as f:
    ct9 = json.load(f)['PK9']

def test_words(fn, length):
    words = []
    with open(fn) as f:
        words = list(set([line.strip().upper() for line in f if len(line.strip()) == length and line.strip().isalpha()]))
    
    # Precompute unique orders
    orders = {}
    for w in words:
        ord_tuple = tuple(_read_order(w))
        if ord_tuple not in orders:
            orders[ord_tuple] = w
            
    print(f"Testing {fn} (len {length}): {len(words)} words -> {len(orders)} unique orders")
    
    order_list = list(orders.items())
    best_rv = 0.0
    best_pair = None
    
    hits = []
    for ord1, w1 in order_list:
        o1 = list(ord1)
        for ord2, w2 in order_list:
            o2 = list(ord2)
            undone = _undo_double(ct9, o1, o2)
            rv, p = reveal_score(undone)
            if rv > 0.065:
                hits.append((rv, p, w1, w2))
            if rv > best_rv:
                best_rv = rv
                best_pair = (rv, p, w1, w2)
                
    print(f"Best reveal for len {length}: {best_pair}")
    print(f"Total hits with rv > 0.065: {len(hits)}")
    hits.sort(key=lambda t: t[0], reverse=True)
    for h in hits[:10]:
        print(f"  rv={h[0]:.5f} p={h[1]} | kw1={h[2]} kw2={h[3]}")

test_words('theophilus_w9.txt', 9)
test_words('theophilus_w8.txt', 8)
