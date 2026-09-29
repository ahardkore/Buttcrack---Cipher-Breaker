#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153
#define L 16

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
    char q[16]; float cnt;
    double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";
static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

void init_tables() {
    for (int i=0; i<26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i=0; i<N; i++) {
        c_idx[i] = hpos[(unsigned char)PK8_CT[i]];
    }
}

// Precomputed linear solver for pos 0
// System of 16 equations in 18 variables (after fixing 4 gauge variables)
// Let's solve via GF(2) and GF(13) CRT
// Variables:
// q4: 4 vars (q4[0..3])
// q5: 4 vars (q5[1..4], q5[0]=0)
// q6: 4 vars (q6[1..4], q6[0]=0, q6[5]=0)
// q7: 6 vars (q7[1..6], q7[0]=0)
// Total vars: 4 + 4 + 4 + 6 = 18 vars!
// Equations: row i in 0..15:
// sum of chosen clock vars = diff[i]
// Since L = 16 and vars = 18, there are 2 null vectors over Z_26!

static int M_base[16][18];
static int piv_col[16];
static int free_cols[2];

void init_system() {
    // Variable layout:
    // 0..3: q4[0..3]
    // 4..7: q5[1..4]
    // 8..11: q6[1..4]
    // 12..17: q7[1..6]
    for (int i = 0; i < 16; i++) {
        memset(M_base[i], 0, sizeof(M_base[i]));
        // q4
        M_base[i][i % 4] = 1;
        // q5
        int r5 = i % 5;
        if (r5 > 0) M_base[i][4 + (r5 - 1)] = 1;
        // q6
        int r6 = i % 6;
        if (r6 >= 1 && r6 <= 4) M_base[i][8 + (r6 - 1)] = 1;
        // q7
        int r7 = i % 7;
        if (r7 > 0) M_base[i][12 + (r7 - 1)] = 1;
    }
}

