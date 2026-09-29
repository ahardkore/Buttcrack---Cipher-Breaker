#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 153
#define NUM_VARS 22

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

void compute_pt(const int *vars, int *pt_std) {
    for (int t = 0; t < N; t++) {
        int k = (vars[t % 4] + vars[4 + (t % 5)] + vars[9 + (t % 6)] + vars[15 + (t % 7)]) % 26;
        int p_kr = (ct_kr[t] - k + 26) % 26;
        pt_std[t] = k2std[p_kr];
    }
}

static inline int vi15(int v) { return v == 15; }

// 2-Opt Polish
float climb_clocks(int *vars) {
    int pt_std[N];
    compute_pt(vars, pt_std);
    float cur_sc = score_pt(pt_std);

    int improved = 1;
    int passes = 0;

    while (improved && passes < 30) {
        improved = 0;
        passes++;

        // 1-Opt
        for (int vi = 0; vi < NUM_VARS; vi++) {
            if (vi == 0 || vi == 4 || vi == 9 || vi == 15) continue; // fix gauges

            int old_v = vars[vi];
            int best_v = old_v;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_v) continue;
                vars[vi] = v;
                compute_pt(vars, pt_std);
                float sc = score_pt(pt_std);
                if (sc > best_s) {
                    best_s = sc;
                    best_v = v;
                }
            }

            vars[vi] = best_v;
            if (best_v != old_v) {
                cur_sc = best_s;
                improved = 1;
            }
        }

        // 2-Opt Coupled
        for (int v1 = 0; v1 < NUM_VARS - 1; v1++) {
            if (v1 == 0 || v1 == 4 || v1 == 9 || vi15(v1)) continue;
            for (int v2 = v1 + 1; v2 < NUM_VARS; v2++) {
                if (v2 == 0 || v2 == 4 || v2 == 9 || vi15(v2)) continue;

                int old1 = vars[v1];
                int old2 = vars[v2];
                int best_d = 0;
                float best_s = cur_sc;

                for (int d = 1; d < 26; d++) {
                    vars[v1] = (old1 + d) % 26;
                    vars[v2] = (old2 - d + 26) % 26;
                    compute_pt(vars, pt_std);
                    float sc = score_pt(pt_std);
                    if (sc > best_s) {
                        best_s = sc;
                        best_d = d;
                    }
                }

                if (best_d != 0) {
                    vars[v1] = (old1 + best_d) % 26;
                    vars[v2] = (old2 - best_d + 26) % 26;
                    cur_sc = best_s;
                    improved = 1;
                } else {
                    vars[v1] = old1;
                    vars[v2] = old2;
                }
            }
        }
    }
    return cur_sc;
}



int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    // Base solution from Star-Decomposition:
    // q4: [0, 15, 0, 6]
    // q5: [0, 4, 19, 12, 0]
    // q6: [0, 20, 22, 7, 25, 4]
    // q7: [0, 11, 25, 16, 4, 5, 11]

    int seed_vars[NUM_VARS] = {
        0, 15, 0, 6,             // q4 (0..3)
        0, 4, 19, 12, 0,         // q5 (4..8)
        0, 20, 22, 7, 25, 4,     // q6 (9..14)
        0, 11, 25, 16, 4, 5, 11  // q7 (15..21)
    };

    printf("Starting 2-Opt Polish initialized from Star-Decomposition Solution...\n");

    int pt[N];
    compute_pt(seed_vars, pt);
    float init_sc = score_pt(pt);
    printf("Initial quadgram score: %.4f\n", init_sc);

    float final_sc = climb_clocks(seed_vars);
    printf("Final quadgram score after 2-opt polish: %.4f\n\n", final_sc);

    compute_pt(seed_vars, pt);
    char pt_str[N + 1];
    for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt[t];
    pt_str[N] = '\0';

    printf("Polished Plaintext:\n%s\n\n", pt_str);
    printf("Polished Clocks:\n");
    printf("q4: [%d, %d, %d, %d]\n", seed_vars[0], seed_vars[1], seed_vars[2], seed_vars[3]);
    printf("q5: [%d, %d, %d, %d, %d]\n", seed_vars[4], seed_vars[5], seed_vars[6], seed_vars[7], seed_vars[8]);
    printf("q6: [%d, %d, %d, %d, %d, %d]\n", seed_vars[9], seed_vars[10], seed_vars[11], seed_vars[12], seed_vars[13], seed_vars[14]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", seed_vars[15], seed_vars[16], seed_vars[17], seed_vars[18], seed_vars[19], seed_vars[20], seed_vars[21]);

    return 0;
}
