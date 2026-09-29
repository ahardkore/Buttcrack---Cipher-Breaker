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
static unsigned char valid_quad[26][26][26][26];

void load_quads() {
    memset(valid_quad, 0, sizeof(valid_quad));
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    int cnt = 0;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
                valid_quad[a][b][c][d] = 1;
                cnt++;
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];
static const int p2[W2] = {7, 0, 5, 2, 4, 3, 6, 1};
static const int p1[W1] = {15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 14, 16, 8};

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

static inline float eval_q_system(const int *q4, const int *q7, int *out_defects, float *out_std_sc) {
    int Z[N], mid[N], pt[N];
    for (int t = 0; t < N; t++) {
        int shift = (q4[t % 4] + q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
    invert_col(Z, W2, H2, p2, mid);

    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) {
            pt[r * 18 + c] = mid[p1[c] * 8 + r];
        }
    }

    float raw_sc = 0.0f;
    float opt_sc = 0.0f;
    int defects = 0;

    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 15; c++) {
            int idx = r * 18 + c;
            int a = pt[idx], b = pt[idx+1], c_ch = pt[idx+2], d = pt[idx+3];
            float sc = quad[a][b][c_ch][d];
            raw_sc += sc;
            opt_sc += sc;
            if (!valid_quad[a][b][c_ch][d]) {
                defects++;
                opt_sc -= 20.0f;
            }
        }
    }

    if (out_defects) *out_defects = defects;
    if (out_std_sc) *out_std_sc = raw_sc / 120.0f;
    return opt_sc / 120.0f;
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 5000;
    int steps_per_restart = (argc > 2) ? atoi(argv[2]) : 10000;

    printf("======================================================================\n");
    printf("PK9 Exact 2-Clock (Q4 + Q7) Annealer on Correct 8x18 Grid\n");
    printf("Total Free Clock Parameters: 10 (Q4[1..3], Q7[0..6])\n");
    printf("Restarts: %d | Steps per restart: %d\n", restarts, steps_per_restart);
    printf("======================================================================\n\n");

    float global_best_opt = -999.0f;
    float global_best_std = -999.0f;
    int global_min_def = 999;
    int global_q4[4], global_q7[7];

    // Seed from our linear algebra regression fit:
    int seed_q4[4] = {0, 12, 19, 18};
    int seed_q7[7] = {25, 3, 13, 0, 7, 14, 21};
    int s_def = 0; float s_std = 0.0f;
    float s_opt = eval_q_system(seed_q4, seed_q7, &s_def, &s_std);
    printf("Seed State Fit: StdScore=%.4f | Defects=%d / 120 (%.1f%% valid)\n\n",
           s_std, s_def, (120 - s_def)/120.0f * 100.0f);

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 991188 + omp_get_thread_num() * 7777;

        #pragma omp for schedule(dynamic, 5)
        for (int rep = 0; rep < restarts; rep++) {
            int q4[4], q7[7];
            if (rep == 0) {
                memcpy(q4, seed_q4, sizeof(seed_q4));
                memcpy(q7, seed_q7, sizeof(seed_q7));
            } else if (rep < 100) {
                memcpy(q4, seed_q4, sizeof(seed_q4));
                memcpy(q7, seed_q7, sizeof(seed_q7));
                int idx = 1 + (rand_r(&seed) % 3);
                q4[idx] = (q4[idx] + rand_r(&seed) % 5 - 2 + 26) % 26;
                int jdx = rand_r(&seed) % 7;
                q7[jdx] = (q7[jdx] + rand_r(&seed) % 5 - 2 + 26) % 26;
            } else {
                q4[0] = 0;
                for (int i = 1; i < 4; i++) q4[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;
            }

            int cur_def = 0; float cur_std = 0.0f;
            float cur_opt = eval_q_system(q4, q7, &cur_def, &cur_std);

            float temp = 0.35f;
            float cooling = powf(0.001f / temp, 1.0f / steps_per_restart);

            for (int s = 0; s < steps_per_restart; s++) {
                int move = rand_r(&seed) % 10;
                int old_val;
                if (move < 3) {
                    int pos = 1 + move;
                    old_val = q4[pos];
                    q4[pos] = rand_r(&seed) % 26;
                } else {
                    int pos = move - 3;
                    old_val = q7[pos];
                    q7[pos] = rand_r(&seed) % 26;
                }

                int new_def = 0; float new_std = 0.0f;
                float new_opt = eval_q_system(q4, q7, &new_def, &new_std);

                float diff = new_opt - cur_opt;
                if (diff > 0.0f || expf(diff / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_opt = new_opt;
                    cur_std = new_std;
                    cur_def = new_def;
                } else {
                    if (move < 3) q4[1 + move] = old_val;
                    else q7[move - 3] = old_val;
                }
                temp *= cooling;
            }

            #pragma omp critical
            {
                if (cur_opt > global_best_opt || cur_def < global_min_def) {
                    if (cur_def <= global_min_def) {
                        global_best_opt = cur_opt;
                        global_best_std = cur_std;
                        global_min_def = cur_def;
                        memcpy(global_q4, q4, sizeof(q4));
                        memcpy(global_q7, q7, sizeof(q7));

                        printf("[Thread %d | Rep %d] Record: Defects=%d / 120 (%.1f%% valid) | StdScore=%.4f\n",
                               omp_get_thread_num(), rep, global_min_def,
                               (120 - global_min_def)/120.0f * 100.0f, global_best_std);
                        fflush(stdout);
                    }
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("\n======================================================================\n");
    printf("Q4 + Q7 ANNEALER COMPLETED in %.2f s\n", t1 - t0);
    printf("Global Min Defects: %d / 120 (%.1f%% valid) | StdScore: %.4f\n",
           global_min_def, (120 - global_min_def)/120.0f * 100.0f, global_best_std);
    printf("======================================================================\n\n");

    printf("Q4 = [%d, %d, %d, %d]\n", global_q4[0], global_q4[1], global_q4[2], global_q4[3]);
    printf("Q7 = [%d, %d, %d, %d, %d, %d, %d]\n\n",
           global_q7[0], global_q7[1], global_q7[2], global_q7[3],
           global_q7[4], global_q7[5], global_q7[6]);

    int Z[N], mid[N], pt[N];
    for (int t = 0; t < N; t++) {
        int shift = (global_q4[t % 4] + global_q7[t % 7]) % 26;
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
    invert_col(Z, W2, H2, p2, mid);
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) {
            pt[r * 18 + c] = mid[p1[c] * 8 + r];
        }
    }

    printf("Plaintext Grid (8 rows x 18 cols):\n");
    for (int r = 0; r < 8; r++) {
        printf("  Row %d: ", r);
        for (int c = 0; c < 18; c++) putchar('A' + pt[r * 18 + c]);
        putchar('\n');
    }

    return 0;
}
