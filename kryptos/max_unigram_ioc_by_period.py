import numpy as np

KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
pk9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQGZGSMMJHJQNHSVHAWFLHXLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIFLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJK"
n = len(pk9)
c_vals = np.array([KRYPTOS.index(c) for c in pk9], dtype=int)

def ioc(arr):
    counts = np.bincount(arr, minlength=26)
    return np.sum(counts * (counts - 1)) / (len(arr) * (len(arr) - 1))

# For each period p, find the key that maximizes the unigram IoC of decrypted text
# Quagmire III: P[i] = (C[i] - K[i % p]) % 26
# Standard Vig: P[i] = (C_std[i] - K[i % p]) % 26

for p in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 24, 28]:
    # We can optimize each column of period p to align frequencies!
    # Under polyalphabetic substitution, each column j in 0..p-1 has a shift k_j.
    # When shifted by k_j, the combined distribution of all columns is sum_{j=0}^{p-1} count_j(x + k_j).
    # To maximize \sum_x ( \sum_j count_j(x + k_j) )^2, this is a multi-column alignment problem!
    # For small p (<= 6), we can do brute force.
    # For larger p, simulated annealing or greedy coordinate ascent.
    
    # Precompute column counts
    col_counts = [np.bincount(c_vals[j::p], minlength=26) for j in range(p)]
    
    # Random restarts coordinate ascent
    best_ioc = 0.0
    best_key = None
    
    for restart in range(500):
        key = np.random.randint(0, 26, size=p)
        key[0] = 0 # fix gauge
        
        improved = True
        while improved:
            improved = False
            for col in range(1, p):
                best_shift = key[col]
                # calculate current total counts without col
                total = np.zeros(26, dtype=int)
                for j in range(p):
                    if j != col:
                        total += np.roll(col_counts[j], -key[j])
                
                # find shift that maximizes sum of squares
                best_ss = 0
                for s in range(26):
                    c = total + np.roll(col_counts[col], -s)
                    ss = np.sum(c * (c - 1))
                    if ss > best_ss:
                        best_ss = ss
                        best_shift = s
                
                if best_shift != key[col]:
                    key[col] = best_shift
                    improved = True
        
        # calculate final ioc
        final_counts = np.zeros(26, dtype=int)
        for j in range(p):
            final_counts += np.roll(col_counts[j], -key[j])
        current_ioc = np.sum(final_counts * (final_counts - 1)) / (n * (n - 1))
        if current_ioc > best_ioc:
            best_ioc = current_ioc
            best_key = key.copy()
            
    print(f"Period {p:2d}: Max Unigram IoC = {best_ioc:.5f} | Key: {list(best_key)}")
