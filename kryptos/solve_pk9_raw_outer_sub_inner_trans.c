#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

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
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];
    }
}

// Evaluate candidate:
// 1. Z[t] = QuagmireIII(ct_kr[t], (q4[t%4] + q7[t%7]) % 26)
// 2. pt by reading Z transposed with width W (12) and column permutation perm
static inline float eval_q4_q7_trans(const int *q4, const int *q7, int W, const int *perm, int *out_pt) {
    int H = N / W;
    int Z[N];
    for (int t = 0; t < N; t++) {
        int ks = (q4[t % 4] + q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - ks + 26) % 26;
        Z[t] = k2std[p_kr];
    }

    int pt[N];
    // Case: Z was formed by writing plaintext into H x W grid and reading out columns according to perm
    // Inverting: write Z into columns by perm, read by rows
    int idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < H; r++) {
            pt[r * W + col] = Z[idx++];
        }
    }

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

// Also test case where Z is read row-by-row with column permutation perm
static inline float eval_q4_q7_row_perm(const int *q4, const int *q7, int W, const int *perm, int *out_pt) {
    int H = N / W;
    int Z[N];
    for (int t = 0; t < N; t++) {
        int ks = (q4[t % 4] + q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - ks + 26) % 26;
        Z[t] = k2std[p_kr];
    }

    int pt[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            pt[idx++] = Z[r * W + perm[c]];
        }
    }

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    int total_restarts = (argc > 1) ? atoi(argv[1]) : 20000;
    int mode = (argc > 2) ? atoi(argv[2]) : 0; // 0 = Columnar invert, 1 = Row-perm

    load_quads();
    init_tables();

    int W = 12;
    printf("======================================================================\n");
    printf("Joint Annealer on RAW PK9: (q4, q7) Clocks + Inner %dx%d Permutation\n", W, N / W);
    printf("Mode: %s | Restarts: %d\n",
           mode == 0 ? "Columnar Transposition Inversion" : "Row-wise Column Permutation",
           total_restarts);
    printf("======================================================================\n");

    float global_best_sc = -999.0f;
    int g_q4[4], g_q7[7], g_perm[12];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 2879;
        float loc_best_sc = -999.0f;
        int l_q4[4], l_q7[7], l_perm[12];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int rep = 0; rep < total_restarts; rep++) {
            int q4[4], q7[7], perm[12];
            for (int i = 0; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;
            for (int i = 0; i < W; i++) perm[i] = i;
            for (int i = W - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
            }

            float cur_sc = (mode == 0) ? eval_q4_q7_trans(q4, q7, W, perm, NULL)
                                       : eval_q4_q7_row_perm(q4, q7, W, perm, NULL);
            float temp = 2.0f;
            float cooling = 0.9992f;

            for (int step = 0; step < 4000; step++) {
                int move_type = rand_r(&seed) % 3;

                int old_v, new_v, pos;
                int c1, c2, tmp;

                if (move_type == 0) {
                    pos = rand_r(&seed) % 4; old_v = q4[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q4[pos] = new_v;
                } else if (move_type == 1) {
                    pos = rand_r(&seed) % 7; old_v = q7[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q7[pos] = new_v;
                } else {
                    c1 = rand_r(&seed) % W;
                    c2 = rand_r(&seed) % W;
                    if (c1 == c2) continue;
                    tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                }

                float sc = (mode == 0) ? eval_q4_q7_trans(q4, q7, W, perm, NULL)
                                       : eval_q4_q7_row_perm(q4, q7, W, perm, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (move_type == 0) q4[pos] = old_v;
                    else if (move_type == 1) q7[pos] = old_v;
                    else { perm[c2] = perm[c1]; perm[c1] = tmp; }
                }

                temp *= cooling;
            }

            // Greedy coordinate descent polish
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int p = 0; p < 4; p++) {
                    int best_v = q4[p], old_v = q4[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q4[p] = (old_v + diff) % 26;
                        float sc = (mode == 0) ? eval_q4_q7_trans(q4, q7, W, perm, NULL)
                                               : eval_q4_q7_row_perm(q4, q7, W, perm, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q4[p]; }
                    }
                    if (best_d > 1e-4f) { q4[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q4[p] = old_v;
                }
                for (int p = 0; p < 7; p++) {
                    int best_v = q7[p], old_v = q7[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q7[p] = (old_v + diff) % 26;
                        float sc = (mode == 0) ? eval_q4_q7_trans(q4, q7, W, perm, NULL)
                                               : eval_q4_q7_row_perm(q4, q7, W, perm, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q7[p]; }
                    }
                    if (best_d > 1e-4f) { q7[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q7[p] = old_v;
                }
                for (int i = 0; i < W - 1; i++) {
                    for (int j = i + 1; j < W; j++) {
                        int t1 = perm[i]; perm[i] = perm[j]; perm[j] = t1;
                        float sc = (mode == 0) ? eval_q4_q7_trans(q4, q7, W, perm, NULL)
                                               : eval_q4_q7_row_perm(q4, q7, W, perm, NULL);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            improved = 1;
                        } else {
                            perm[j] = perm[i]; perm[i] = t1;
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_q4, q4, 4 * sizeof(int));
                memcpy(l_q7, q7, 7 * sizeof(int));
                memcpy(l_perm, perm, W * sizeof(int));

                int pt_arr[N];
                if (mode == 0) eval_q4_q7_trans(q4, q7, W, perm, pt_arr);
                else eval_q4_q7_row_perm(q4, q7, W, perm, pt_arr);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt_arr[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q4, l_q4, 4 * sizeof(int));
                memcpy(g_q7, l_q7, 7 * sizeof(int));
                memcpy(g_perm, l_perm, W * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] Global Best: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  q4: [%d,%d,%d,%d] (KR: %c%c%c%c)\n",
                       g_q4[0], g_q4[1], g_q4[2], g_q4[3],
                       KRYPTOS[g_q4[0]], KRYPTOS[g_q4[1]], KRYPTOS[g_q4[2]], KRYPTOS[g_q4[3]]);
                printf("  q7: [%d,%d,%d,%d,%d,%d,%d] (KR: %c%c%c%c%c%c%c)\n",
                       g_q7[0], g_q7[1], g_q7[2], g_q7[3], g_q7[4], g_q7[5], g_q7[6],
                       KRYPTOS[g_q7[0]], KRYPTOS[g_q7[1]], KRYPTOS[g_q7[2]],
                       KRYPTOS[g_q7[3]], KRYPTOS[g_q7[4]], KRYPTOS[g_q7[5]],
                       KRYPTOS[g_q7[6]]);
                printf("  Perm: [");
                for (int i = 0; i < W; i++) printf("%d%s", g_perm[i], i==W-1?"":", ");
                printf("]\n");
                printf("  PT: %.75s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("%d restarts completed in %.3f s (%.1f restarts/sec)!\n\n",
           total_restarts, elapsed, total_restarts / elapsed);

    printf("======================================================================\n");
    printf("FINAL BEST RESULT (Mode: %d)\n", mode);
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("Plaintext:\n%s\n\n", g_pt);
    printf("Plaintext in %d-char rows:\n", W);
    for (int r = 0; r < N / W; r++) {
        char buf[W + 1];
        memcpy(buf, g_pt + r * W, W);
        buf[W] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}
