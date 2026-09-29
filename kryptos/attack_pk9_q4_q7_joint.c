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

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) {
            dst[r * w + col] = src[idx++];
        }
    }
}

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 2000;

    printf("======================================================================\n");
    printf("PK9 Attack: Joint Optimization of (Q4, Q7) Clocks and Transposition\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int best_q4[4], best_q7[7];
    int best_p1[18], best_p2[8];
    char best_pt[N + 1];

    // Seed permutations from our known frontier:
    const int init_p1[18] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
    const int init_p2[8] = {7, 0, 5, 2, 4, 3, 6, 1};
    const int init_q7[7] = {0, 22, 3, 3, 15, 0, 1};

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 54321 + omp_get_thread_num() * 1111;
        float loc_best = -999.0f;
        int loc_q4[4], loc_q7[7], loc_p1[18], loc_p2[8];
        char loc_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int q4[4], q7[7], p1[18], p2[8];
            q4[0] = 0;
            for (int i = 1; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;

            // 50% start near known good p1, p2; 50% random
            if (rand_r(&seed) % 2 == 0) {
                memcpy(p1, init_p1, 18 * sizeof(int));
                memcpy(p2, init_p2, 8 * sizeof(int));
                // perturb slightly
                int s1 = rand_r(&seed) % 18, s2 = rand_r(&seed) % 18;
                int t = p1[s1]; p1[s1] = p1[s2]; p1[s2] = t;
            } else {
                for (int i = 0; i < 18; i++) p1[i] = i;
                for (int i = 17; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int t = p1[i]; p1[i] = p1[j]; p1[j] = t;
                }
                for (int i = 0; i < 8; i++) p2[i] = i;
                for (int i = 7; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int t = p2[i]; p2[i] = p2[j]; p2[j] = t;
                }
            }

            int Z_loc[N], mid[N], pt[N];
            for (int t = 0; t < N; t++) {
                int shift = (q4[t % 4] + q7[t % 7]) % 26;
                int p_kr = (ct_kr[t] - shift + 26) % 26;
                Z_loc[t] = k2std[p_kr];
            }
            invert_col(Z_loc, W2, H2, p2, mid);
            invert_col(mid, W1, H1, p1, pt);
            float cur_sc = score_text(pt, N);

            // Simulated Annealing
            float temp = 0.5f;
            float cooling = 0.992f;

            for (int step = 0; step < 2000; step++) {
                int move = rand_r(&seed) % 20;

                if (move < 3) {
                    // change q4
                    int idx = 1 + (move % 3);
                    int old_v = q4[idx];
                    q4[idx] = rand_r(&seed) % 26;

                    for (int t = 0; t < N; t++) {
                        int shift = (q4[t % 4] + q7[t % 7]) % 26;
                        int p_kr = (ct_kr[t] - shift + 26) % 26;
                        Z_loc[t] = k2std[p_kr];
                    }
                    invert_col(Z_loc, W2, H2, p2, mid);
                    invert_col(mid, W1, H1, p1, pt);
                    float sc = score_text(pt, N);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q4[idx] = old_v;
                    }
                } else if (move < 10) {
                    // change q7
                    int idx = move - 3;
                    int old_v = q7[idx];
                    q7[idx] = rand_r(&seed) % 26;

                    for (int t = 0; t < N; t++) {
                        int shift = (q4[t % 4] + q7[t % 7]) % 26;
                        int p_kr = (ct_kr[t] - shift + 26) % 26;
                        Z_loc[t] = k2std[p_kr];
                    }
                    invert_col(Z_loc, W2, H2, p2, mid);
                    invert_col(mid, W1, H1, p1, pt);
                    float sc = score_text(pt, N);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q7[idx] = old_v;
                    }
                } else if (move < 16) {
                    // swap in p1
                    int i = rand_r(&seed) % 18;
                    int j = rand_r(&seed) % 18;
                    if (i == j) continue;
                    int t = p1[i]; p1[i] = p1[j]; p1[j] = t;

                    invert_col(mid, W1, H1, p1, pt);
                    float sc = score_text(pt, N);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        p1[j] = p1[i]; p1[i] = t;
                    }
                } else {
                    // swap in p2
                    int i = rand_r(&seed) % 8;
                    int j = rand_r(&seed) % 8;
                    if (i == j) continue;
                    int t = p2[i]; p2[i] = p2[j]; p2[j] = t;

                    invert_col(Z_loc, W2, H2, p2, mid);
                    invert_col(mid, W1, H1, p1, pt);
                    float sc = score_text(pt, N);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        p2[j] = p2[i]; p2[i] = t;
                    }
                }

                temp *= cooling;
            }

            if (cur_sc > loc_best) {
                loc_best = cur_sc;
                memcpy(loc_q4, q4, 4 * sizeof(int));
                memcpy(loc_q7, q7, 7 * sizeof(int));
                memcpy(loc_p1, p1, 18 * sizeof(int));
                memcpy(loc_p2, p2, 8 * sizeof(int));
                for (int i = 0; i < N; i++) loc_pt[i] = 'A' + pt[i];
                loc_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_sc) {
                global_best_sc = loc_best;
                memcpy(best_q4, loc_q4, 4 * sizeof(int));
                memcpy(best_q7, loc_q7, 7 * sizeof(int));
                memcpy(best_p1, loc_p1, 18 * sizeof(int));
                memcpy(best_p2, loc_p2, 8 * sizeof(int));
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] Record: Score=%.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
                printf("  Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
                       best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
                printf("  PT: %.60s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("ATTACK COMPLETED in %.2f s | Best Score: %.4f\n", elapsed, global_best_sc);
    printf("======================================================================\n");
    printf("Final Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
    printf("Final Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    printf("Final P1: [");
    for (int i = 0; i < 18; i++) printf("%d%s", best_p1[i], i==17?"":", ");
    printf("]\nFinal P2: [");
    for (int i = 0; i < 8; i++) printf("%d%s", best_p2[i], i==7?"":", ");
    printf("]\n\nFull Plaintext:\n%s\n", best_pt);

    return 0;
}
