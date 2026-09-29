#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int inv13[13] = {0, 1, 7, 9, 10, 8, 11, 2, 5, 3, 4, 6, 12}; // mod 13 inverse

// Periods (4, 5, 7):
// Total vars: 4 + 5 + 7 = 16 vars.
// Var layout:
// 0..3: x4[0..3]
// 4..8: x5[0..4]
// 9..15: x7[0..6]

typedef struct {
    uint16_t basis2[16];
    int val2[16];
    int has2[16];

    int basis13[16][16];
    int val13[16];
    int has13[16];
} System;

void sys_init(System *sys) {
    memset(sys, 0, sizeof(System));
}

int sys_add(System *sys, int pos, int rhs26) {
    int rhs2 = rhs26 & 1;
    int rhs13 = rhs26 % 13;

    // Build row vector
    uint16_t mask2 = (1 << (pos % 4)) | (1 << (4 + (pos % 5))) | (1 << (9 + (pos % 7)));
    int row13[16] = {0};
    row13[pos % 4] = 1;
    row13[4 + (pos % 5)] = 1;
    row13[9 + (pos % 7)] = 1;

    // Reduce mod 2
    for (int p = 0; p < 16; p++) {
        if (mask2 & (1 << p)) {
            if (sys->has2[p]) {
                mask2 ^= sys->basis2[p];
                rhs2 ^= sys->val2[p];
            } else {
                sys->basis2[p] = mask2;
                sys->val2[p] = rhs2;
                sys->has2[p] = 1;
                break;
            }
        }
    }
    if (mask2 == 0 && rhs2 != 0) return 0; // Contradiction mod 2

    // Reduce mod 13
    for (int p = 0; p < 16; p++) {
        int factor = row13[p];
        if (factor != 0) {
            if (sys->has13[p]) {
                for (int j = p; j < 16; j++) {
                    row13[j] = (row13[j] - factor * sys->basis13[p][j]) % 13;
                    if (row13[j] < 0) row13[j] += 13;
                }
                rhs13 = (rhs13 - factor * sys->val13[p]) % 13;
                if (rhs13 < 0) rhs13 += 13;
            } else {
                int inv = inv13[factor];
                for (int j = p; j < 16; j++) {
                    sys->basis13[p][j] = (row13[j] * inv) % 13;
                }
                sys->val13[p] = (rhs13 * inv) % 13;
                sys->has13[p] = 1;
                break;
            }
        }
    }
    int all_zero = 1;
    for (int j = 0; j < 16; j++) if (row13[j] != 0) { all_zero = 0; break; }
    if (all_zero && rhs13 != 0) return 0; // Contradiction mod 13

    return 1;
}

// Check if position i is determined
int sys_eval(System *sys, int pos, int *out_k) {
    // Check mod 2
    uint16_t mask2 = (1 << (pos % 4)) | (1 << (4 + (pos % 5))) | (1 << (9 + (pos % 7)));
    int v2 = 0;
    for (int p = 0; p < 16; p++) {
        if (mask2 & (1 << p)) {
            if (!sys->has2[p]) return 0; // Not determined mod 2
            mask2 ^= sys->basis2[p];
            v2 ^= sys->val2[p];
        }
    }

    // Check mod 13
    int row13[16] = {0};
    row13[pos % 4] = 1;
    row13[4 + (pos % 5)] = 1;
    row13[9 + (pos % 7)] = 1;
    int v13 = 0;
    for (int p = 0; p < 16; p++) {
        int factor = row13[p];
        if (factor != 0) {
            if (!sys->has13[p]) return 0; // Not determined mod 13
            for (int j = p; j < 16; j++) {
                row13[j] = (row13[j] - factor * sys->basis13[p][j]) % 13;
                if (row13[j] < 0) row13[j] += 13;
            }
            v13 = (v13 + factor * sys->val13[p]) % 13;
        }
    }

    // CRT: 13 * v2 + 14 * v13 mod 26:
    // Notice: if mod 2 is v2 (0 or 1), and mod 13 is v13 (0..12):
    // k = (13 * v2 + 14 * v13) % 26
    *out_k = (13 * v2 + 14 * v13) % 26;
    return 1;
}

int main() {
    System sys;
    sys_init(&sys);

    // Test with a 14-letter crib at pos 0
    const char *test_crib = "ABCDEFGHIJKLMN";
    int ok = 1;
    for (int i = 0; i < 14; i++) {
        // dummy rhs = i
        if (!sys_add(&sys, i, i)) {
            ok = 0; break;
        }
    }
    printf("Consistent: %d\n", ok);
    int det_count = 0;
    for (int i = 0; i < 144; i++) {
        int k;
        if (sys_eval(&sys, i, &k)) det_count++;
    }
    printf("Determined count across 144: %d\n", det_count);
    return 0;
}
