#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W1 18
#define H1 8
#define W2 8
#define H2 18

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
const char *PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];
}

static const int p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
static const int p2[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

static int pt_to_z[N];
static int z_to_pt[N];

void init_routing_maps() {
    int pt_to_mid[N];
    int idx = 0;
    for (int c_idx = 0; c_idx < W1; c_idx++) {
        int col = p1[c_idx];
        for (int r = 0; r < H1; r++) {
            pt_to_mid[r * W1 + col] = idx++;
        }
    }

    int mid_to_z[N];
    idx = 0;
    for (int c_idx = 0; c_idx < W2; c_idx++) {
        int col = p2[c_idx];
        for (int r = 0; r < H2; r++) {
            mid_to_z[r * W2 + col] = idx++;
        }
    }

    for (int i = 0; i < N; i++) {
        pt_to_z[i] = mid_to_z[pt_to_mid[i]];
        z_to_pt[pt_to_z[i]] = i;
    }
}

static inline void decrypt_pt(const int *shifts28, int *pt) {
    for (int i = 0; i < N; i++) {
        int z_idx = pt_to_z[i];
        int s = shifts28[z_idx % 28];
        int p_kr = (ct_kr[z_idx] - s + 26) % 26;
        pt[i] = k2std[p_kr];
    }
}

static inline float eval_pt(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();
    init_tables();
    init_routing_maps();

    int shifts[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};

    int pt[N];
    decrypt_pt(shifts, pt);
    float cur_sc = eval_pt(pt);

    printf("======================================================================\n");
    printf("Targeted Coordinate-Shift Alignment (TCSA) Engine on PK9\n");
    printf("Initial Baseline Score: %.4f\n", cur_sc);
    printf("======================================================================\n\n");

    double t0 = omp_get_wtime();

    // 1. Exhaustive single-shift coordinate passes
    printf("Phase 1: Exhaustive Single-Shift Coordinate Descent...\n");
    int improved = 1;
    int pass = 0;
    while (improved && pass < 50) {
        improved = 0;
        pass++;
        for (int k = 0; k < 28; k++) {
            int old_s = shifts[k];
            int best_s = old_s;
            float best_sc = cur_sc;

            for (int diff = 1; diff < 26; diff++) {
                shifts[k] = (old_s + diff) % 26;
                decrypt_pt(shifts, pt);
                float sc = eval_pt(pt);
                if (sc > best_sc + 1e-4f) {
                    best_sc = sc;
                    best_s = shifts[k];
                }
            }

            shifts[k] = best_s;
            if (best_s != old_s) {
                cur_sc = best_sc;
                improved = 1;
                printf("  [Pass %2d] Shift %2d changed %2d -> %2d | New Score: %.4f\n",
                       pass, k, old_s, best_s, cur_sc);
            }
        }
    }

    // 2. Exhaustive pairwise shift sweep (all 378 pairs x 676 combinations = 255,528 evaluations)
    printf("\nPhase 2: Exhaustive Pairwise Shift Sweep (all 378 pairs)...\n");
    int pair_improved = 1;
    int pair_pass = 0;
    while (pair_improved && pair_pass < 10) {
        pair_improved = 0;
        pair_pass++;
        for (int k1 = 0; k1 < 27; k1++) {
            for (int k2 = k1 + 1; k2 < 28; k2++) {
                int old_s1 = shifts[k1], old_s2 = shifts[k2];
                int best_s1 = old_s1, best_s2 = old_s2;
                float best_sc = cur_sc;

                for (int d1 = 0; d1 < 26; d1++) {
                    shifts[k1] = (old_s1 + d1) % 26;
                    for (int d2 = 0; d2 < 26; d2++) {
                        shifts[k2] = (old_s2 + d2) % 26;
                        decrypt_pt(shifts, pt);
                        float sc = eval_pt(pt);
                        if (sc > best_sc + 1e-4f) {
                            best_sc = sc;
                            best_s1 = shifts[k1];
                            best_s2 = shifts[k2];
                        }
                    }
                }

                shifts[k1] = best_s1;
                shifts[k2] = best_s2;
                if (best_s1 != old_s1 || best_s2 != old_s2) {
                    cur_sc = best_sc;
                    pair_improved = 1;
                    printf("  [Pair Pass %2d] Shifts (%2d, %2d) -> (%2d, %2d) | Score: %.4f\n",
                           pair_pass, k1, k2, best_s1, best_s2, cur_sc);
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\n======================================================================\n");
    printf("TCSA EXHAUSTION COMPLETE in %.3f s\n", elapsed);
    printf("Final Score: %.4f\n", cur_sc);
    printf("Final Shifts: [");
    for (int i = 0; i < 28; i++) printf("%d%s", shifts[i], i==27?"":", ");
    printf("]\n");
    printf("Key in KR:    ");
    for (int i = 0; i < 28; i++) printf("%c", KRYPTOS[shifts[i]]);
    printf("\n\n");

    decrypt_pt(shifts, pt);
    char pt_str[N + 1];
    for (int i = 0; i < N; i++) pt_str[i] = 'A' + pt[i];
    pt_str[N] = '\0';

    printf("Full Plaintext:\n%s\n\n", pt_str);

    printf("Plaintext in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[19];
        memcpy(buf, pt_str + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}
