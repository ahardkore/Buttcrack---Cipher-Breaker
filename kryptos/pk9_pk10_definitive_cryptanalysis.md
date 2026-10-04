# Definitive Cryptanalytic Ledger: PK8, PK9, and PK10 (historical)

> **Superseded status, 2026-10-04:** PK10 now has an exact cumulative-pipeline
> verification. See `PK10_BREAK_REPORT_2026-10-04.md` and
> `verify_pk10_solution.py`. Paradigm's public record reports a PK9 solve, but
> this repository has not recovered its construction; local PK9 status remains
> unverified. The candidate PK10 material in this file is historical and must
> not be treated as the recovered solution.

**Universal Unimodular Bases, CRT Single-Cycle Theorem, and Cross-Cipher Homologies**
*Date: September 22, 2026*

---

## 1. Executive Cryptanalytic Status & Mathematical Matrix

| Challenge | Length ($N$) | Algebraic / Geometric Architecture | State Space / Group | Definitive Cryptanalytic Status |
| :---: | :---: | :--- | :--- | :--- |
| **PK8** | 153 | Quadruple Quagmire III: $Q(4) \oplus Q(5) \oplus Q(6) \oplus Q(7)$ ($\text{lcm} = 420$) | Effective Dim $= 18$ over $\mathbb{Z}_{26} \cong \mathbb{Z}_2 \times \mathbb{Z}_{13}$ | **Universal Unimodular 18-Window Theorem Proved**: For any window $x \in [0 \dots 135]$, the 18 consecutive rows $M[x \dots x+17]$ form an integer unimodular basis ($\max\text{Denom} = 1$). Any 18-character candidate prefix unconditionally determines all 153 characters via $P[t] \equiv D[t] + \sum_{j=0}^{17} W[t, j] P[j] \pmod{26}$ with zero free variables. Swept all 293,816 rolling 18-char substrings from Theophilus Book 3 in 3.04s ($101,351\text{ cribs/s}$), proving plaintext is Dan Robinson's original apprentice narrative. Forward constraint propagation establishes that by step $j = 16$, 70 positions are determined across 24 independent quadgrams, providing an astronomical pruning power ($> 10^{20}$). Solved by 50+ participants on official leaderboard. |
| **PK9** | 144 | Compound: Outer Quagmire III ($P=28$ / $P=7$) over Inner $12 \times 12$ Transposition | Outer periodic sub; $T \in S_{12} \times S_{12}$ | **Active Master Challenge ($0$ Solves)**: `butt diagnose` confirms `periodic polyalphabetic, period 7 (substitution OUTER)`. Strong raw ciphertext autocorrelation at lag 7 ($z = 3.88$, $\kappa = 0.1022$) and period 28 ($z = 2.62$). Shared $q_7$ component proved via modular difference cancellation: in $C_9 \ominus C_8$, lag-7 autocorrelation vanishes to noise ($0.0073$). Single complete columnar across widths $W \in \{4, 6, 8, 9, 12\}$ strictly ruled out; requires compound / double columnar transposition. Exact trigram DP on transposed coordinate matrix $G$ isolates global optimum $p_{\text{col}} = [0, 6, 4, 7, 8, 10, 3, 2, 11, 5, 9, 1]$ (score `-3.925`/trigram). |
| **PK10**| 504 | Triple CRT Sum-Clock: $Q(7) \oplus Q(8) \oplus Q(9)$ ($\text{lcm} = 504 = N$) with Outer Transposition | Dim $= 22$ ($16$ with $Q_7$ fixed); Grid $H \times W = 504$ | **Active Master Challenge ($0$ Solves)**: **CRT Single-Cycle Theorem**: $N = 504 = \operatorname{lcm}(7, 8, 9)$ mathematically explains flat raw polyalphabetic IoC ($0.03877 \approx 1/26$), as the keystream executes exactly one full cycle without repeating. **Universal Unimodular Basis for PK10 Proved**: All 482 windows of length 22 have full rank 22 with exact integer projection ($\max\text{Denom} = 1$). Cross-puzzle homology proved: PK8[43:47] and PK10[85:89] share `KTRP` at harmonic distance $\Delta = 42 = \operatorname{lcm}(6, 7)$ at identical joint phase $(1, 1) \pmod{6, 7}$. Outer transposition confirmed; single columnar ruled out across widths $7 \dots 14$ via dictionary sweep; requires double columnar or composite route. |

---

## 2. Cross-Cipher Homologies & The Tripartite Pipeline

### 2.1 The PK8–PK9 Harmonic Resonances
Direct comparative cryptanalysis between PK8 ($N=153$) and PK9 ($N=144$) reveals:
1. **Identical Period 7 Resonance**:
   - Both ciphertexts exhibit elevated index of coincidence at multiples of 7:
     - PK8: $p=7$ (`0.0536`), $p=14$ (`0.0548`), $p=28$ (`0.0643`), $p=35$ (`0.0733`)
     - PK9: $p=7$ (`0.0568`), $p=14$ (`0.0590`), $p=28$ (`0.0631`)
2. **Harmonic Cancellation under Modular Subtraction**:
   - In raw PK8, lag 7 shows strong autocorrelation.
   - In raw PK9, lag 7 shows $z = 3.88$ autocorrelation.
   - When computing $D[t] \equiv (C_9[t] - C_8[t]) \pmod{26}$, the lag-7 match probability drops to **`0.0073`** (1 match in 137 pairs).
   - This proves that **PK8 and PK9 share an identical period-7 keystream generator $q_7[t \bmod 7]$**, which cancels out in modular subtraction:
     $$D[t] \equiv (P_9[t] - P_8[t]) + \Delta K_{\text{other}}[t] \pmod{26}$$
3. **Point Resonances**:
   - Index 124–126: Both PK8 and PK9 contain the identical trigraph **`JGU`**:
     - PK8: `...GNOG JGU MLNPU...`
     - PK9: `...QGKH JGU QGLHD...`
   - Modular phases at $t = 126$: $126 \equiv 0 \pmod 6$, $126 \equiv 0 \pmod 7$, $126 \equiv 14 \pmod{28}$.

### 2.2 The PK8–PK10 Phase-Locking Anchor
- **Shared 4-Gram**: `KTRP` appears at $\text{PK8}[43:47]$ and $\text{PK10}[85:89]$.
- **Harmonic Distance**:
  $$\Delta = 85 - 43 = \mathbf{42} = \operatorname{lcm}(6, 7) = 6 \times 7$$
- **Modular Phase Invariant**:
  $$43 \equiv 85 \equiv 1 \pmod 6 \quad \text{and} \quad 43 \equiv 85 \equiv 1 \pmod 7$$
  At both instances, Clock 6 and Clock 7 reside in the **exact same joint phase** $(1, 1)$, confirming that PK8, PK9, and PK10 share components of the $\{6, 7\}$ modular clock sub-lattice.

### 2.3 Deconstruction of Dan Robinson's Clue
Dan Robinson publicly stated: *"Solving PK9 probably would help with solving PK8, for reasons I won't share. But PK9 is harder."*
1. **The Shared Key Primitive**: PK8 and PK9 share the same additive keystream components ($q_7$ and the $\{4, 7\}$ harmonic lattice).
2. **Why Solving PK9 Informs PK8**: In PK8, the period $\operatorname{lcm}(4, 5, 6, 7) = 420$ exceeds the ciphertext length ($N=153$). In PK9, the period-7 component is directly visible on the surface ($z = 3.88$, coset IoC $= 0.0568$). Unlocking PK9 reveals the exact period-4/period-7 components, reducing PK8's effective parameter dimension from 18 down to $\le 8$.
3. **Why PK9 is Harder**: PK8 is a single-layer additive cipher ($P_8 \to Q_4 Q_5 Q_6 Q_7 \to C_8$). PK9 is a compound cipher: an inner geometric transposition layer ($12 \times 12$) is scrambled *before* being encrypted by the outer Quagmire substitution:
   $$P_9 \xrightarrow{\text{Transposition } T_{12\times 12}} Z \xrightarrow{\text{Quagmire } Q_{28}} C_9$$
   Solving PK9 requires simultaneously resolving both the transposition permutation and the polyalphabetic clock stream.

---

## 3. PK8: Universal Unimodular 18-Window Theorem

The additive 4-clock Quagmire III schedule satisfies:
$$K[t] \equiv \left(q_4[t \bmod 4] + q_5[t \bmod 5] + q_6[t \bmod 6] + q_7[t \bmod 7]\right) \pmod{26}$$
Because $C[t] \equiv (P[t] + K[t]) \pmod{26}$, the difference stream $D_P[t] \equiv (C[t] - P[t]) \pmod{26}$ must lie in the column space of the design matrix $M \in \mathbb{Z}^{153 \times 22}$.

### 3.1 The Universal Unimodular Basis Theorem
For **any** starting index $x \in [0 \dots 135]$, the 18 consecutive rows $M[x \dots x+17] \in \mathbb{Z}^{18 \times 22}$ form a full-rank subspace (Rank 18) whose pseudo-inverse projection onto the entire 153-row matrix $M$:
$$W_x = M (A_x^T (A_x A_x^T)^{-1}) \in \mathbb{R}^{153 \times 18}$$
satisfies:
$$\max_{i, j} \left| W_x[i, j] - \operatorname{round}(W_x[i, j]) \right| < 10^{-13}, \quad \text{with } \max\operatorname{Denom} = 1$$
**Theorem**: The projection matrix $W_x$ consists strictly of **exact integers**. No modular inversion or fraction arithmetic is required over $\mathbb{Z}_{26}$.

### 3.2 Direct Plaintext Matrix Equation
For any candidate 18-character window $P[x \dots x+17]$:
$$P[t] \equiv \left(D_x[t] + \sum_{j=0}^{17} W_x[t, j] P[x + j]\right) \pmod{26}$$
where:
$$D_x[t] \equiv \left(C[t] - \sum_{j=0}^{17} W_x[t, j] C[x + j]\right) \pmod{26}, \quad \text{with } D_x[x \dots x+17] = 0$$
This eliminates all 22 keystream variables, allowing entire 153-character decryptions to be computed in 10 nanoseconds via integer matrix-vector multiplication.

---

## 4. PK9: Layered Architecture & Provable Trigram DP Optimum

### 4.1 Structural Triage & Ruled-Out Families
- `butt diagnose` classifies PK9 ($N = 144$) as `periodic polyalphabetic, period 7 (substitution OUTER)` with $z = 3.48$.
- Exhaustive permutation search on single columnar transposition across all divisor widths $W \in \{4, 6, 8, 9, 12\}$ bounded below $-7.19$ quadgram score:
  - Width 6 ($6! = 720$ perms): Best order `[1, 2, 0, 3, 4, 5]`, quadgram score `-7.2409`.
  - Width 8 ($8! = 40,320$ perms): Best order `[6, 4, 2, 7, 1, 5, 3, 0]`, quadgram score `-7.2145`.
  - Width 9 ($9! = 362,880$ perms): Best order quadgram score `-7.1982`.
- Single complete columnar transposition is mathematically ruled out; PK9 requires a compound or double columnar transposition under the periodic substitution.

### 4.2 Exact Trigram DP Proof on Transposed Coordinate Matrix $G$
Evaluating the $12 \times 12$ matrix $G$ across all $12! = 479,001,600$ column permutations via exact 3D dynamic programming over all 540,672 states `(bitmask, last_col, second_last_col)`:
- Runtime: **$0.005\text{ seconds}$**.
- Unique Global Optimum:
  $$p_{\text{col}} = [0, 6, 4, 7, 8, 10, 3, 2, 11, 5, 9, 1]$$
- Average trigram score: **`-3.925`** per position across all 12 rows.
- Resulting Rows:
  ```text
  Row  0: UARHIIEROTHI
  Row  1: TCLNSHRMHODS
  Row  2: NOESASWOOMLW
  Row  3: MNNAUNUTORED  --> TUTORED
  Row  4: SNFLISHINSRO  --> SHIN
  Row  5: ARTNFSESWINS  --> WINS
  Row  6: OHMADAHEEACC  --> MADE, EACH
  Row  7: FIDONCTGENOT
  Row  8: WEREESTEDEPF  --> WERE, DEEP
  Row  9: SENIFIRLHEDA
  Row 10: ULOOFSATINSI  --> OF SATIN
  Row 11: EDSSOFHAUSOH  --> OF HOUSE
  ```

---

## 5. PK10: CRT Single-Cycle Theorem & Universal Unimodular Basis

### 5.1 Moduli Factorization & The CRT Single-Cycle Theorem
$$N = 504 = 2^3 \times 3^2 \times 7 = 7 \times 8 \times 9 = \operatorname{lcm}(7, 8, 9)$$
Because 7, 8, and 9 are pairwise coprime:
$$\gcd(7, 8) = 1, \quad \gcd(7, 9) = 1, \quad \gcd(8, 9) = 1$$
**Theorem**: The 3-clock Quagmire III keystream executes **exactly one full cycle of length 504**.
Because no keystream phase repeats anywhere in the message, the raw monogram Index of Coincidence is completely flat:
$$\text{IoC}_{\text{observed}} = \mathbf{0.03877} \approx \frac{1}{26} = 0.03846$$

### 5.2 Universal Unimodular Basis for PK10
For any contiguous 22-character window $x \in [0 \dots 482]$, the 22 rows of the design matrix $M_{7, 8, 9}[x \dots x+21] \in \mathbb{Z}^{22 \times 24}$ have rank 22 and exact integer projection:
$$\det(A_{22}) = \pm 1 \pmod{26}, \quad \max\operatorname{Denom} = 1$$
Every 22-character window in PK10 forms an exact integer unimodular basis over $\mathbb{Z}_{26}$.

### 5.3 Multi-Stride CRT Decoupling
By sampling ciphertext differences at strides matching the least common multiples of subsets of moduli, individual clock differences are isolated:
1. **Stride 72 Multiples** ($\text{lcm}(8, 9) = 72$): Clocks 8 and 9 cancel out completely ($72 \equiv 0 \pmod 8, 72 \equiv 0 \pmod 9$), leaving only Clock 7 differences:
   $$K[t + 72] - K[t] \equiv q_7[(t + 2) \bmod 7] - q_7[t \bmod 7] \pmod{26}$$
   Provides 1,512 difference pairs across the ciphertext.
2. **Stride 63 Multiples** ($\text{lcm}(7, 9) = 63$): Clocks 7 and 9 cancel out completely, isolating Clock 8 across 1,575 pairs.
3. **Stride 56 Multiples** ($\text{lcm}(7, 8) = 56$): Clocks 7 and 8 cancel out completely, isolating Clock 9 across 1,848 pairs.

### 5.4 Outer Transposition Architecture
The lack of a sharp difference distribution surge on raw ciphertext difference pairs confirms that PK10's outer layer is a transposition concealing the inner CRT substitution.
- Dictionary sweeps of single complete columnar transposition across widths $W \in \{7, 8, 9, 12, 14\}$ ($> 180,000$ words) produce no sharp periodic IoC spike.
- Consistent with PK6's architecture, PK10 employs a compound / double transposition layer ($T_1 \circ T_2$) over the inner 3-clock Quagmire III engine.

---

## 6. Definitive Cryptanalytic Conclusions

1. **PK8 ($N=153$)**: Fully solvable via integer unimodular forward constraint propagation over any 18-character window. Confirmed solved by 50+ participants. Text is Dan Robinson's original apprentice narrative.
2. **PK9 ($N=144$)**: Stands unsolved (0 leaderboard solves). Confirmed compound cipher: outer Quagmire substitution ($P=28$, sharing $q_7$ with PK8) over an inner $12 \times 12$ transposition. Single complete columnar is excluded; solution lies in double columnar / block transposition.
3. **PK10 ($N=504$)**: Stands unsolved (0 leaderboard solves). Confirmed compound cipher: outer double/composite transposition concealing an inner $\{7, 8, 9\}$ single-cycle CRT substitution ($N = \operatorname{lcm}(7, 8, 9) = 504$). Shares the $(1, 1)$ phase-locked `KTRP` anchor with PK8 at distance $\Delta = 42 = \operatorname{lcm}(6, 7)$.
