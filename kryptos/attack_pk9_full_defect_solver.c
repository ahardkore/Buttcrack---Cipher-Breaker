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
#define TOTAL_QUADS 120

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

static inline float eval_state(const int *s, const int *p1, int *out_defects, float *out_std_sc) {
    int Z[N], mid[N], pt[N];
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
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
    if (out_std_sc) *out_std_sc = raw_sc / TOTAL_QUADS;
    return opt_sc / TOTAL_QUADS;
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 2000;
    int steps_per_restart = (argc > 2) ? atoi(argv[2]) : 25000;

    const int base_s[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 8, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};
    const int base_p1[W1] = {15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 8, 16, 14};

    int init_def = 0; float init_std = 0.0f;
    float init_opt = eval_state(base_s, base_p1, &init_def, &init_std);

    printf("======================================================================\n");
    printf("PK9 Joint Shift & Permutation Defect Minimizer\n");
    printf("Initial: StdScore=%.4f | Defects=%d / %d (%.1f%% valid)\n",
           init_std, init_def, TOTAL_QUADS, (1.0f - (float)init_def/TOTAL_QUADS)*100.0f);
    printf("Restarts: %d | Steps per restart: %d\n", restarts, steps_per_restart);
    printf("======================================================================\n\n");

    float global_best_opt = init_opt;
    float global_best_std = init_std;
    int global_min_def = init_def;
    int global_s[28], global_p1[W1];
    memcpy(global_s, base_s, sizeof(base_s));
    memcpy(global_p1, base_p1, sizeof(base_p1));

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 771122 + omp_get_thread_num() * 12345;

        #pragma omp for schedule(dynamic, 1)
        for (int rep = 0; rep < restarts; rep++) {
            int cur_s[28], cur_p1[W1];
            memcpy(cur_s, base_s, sizeof(base_s));
            memcpy(cur_p1, base_p1, sizeof(base_p1));

            if (rep > 0) {
                // Perturb p1
                int perturbations = 2 + (rand_r(&seed) % 4);
                for (int k = 0; k < perturbations; k++) {
                    int a = rand_r(&seed) % W1;
                    int b = rand_r(&seed) % W1;
                    int t = cur_p1[a]; cur_p1[a] = cur_p1[b]; cur_p1[b] = t;
                }
            }

            int cur_def = 0; float cur_std = 0.0f;
            float cur_opt = eval_state(cur_s, cur_p1, &cur_def, &cur_std);

            float temp = 0.30f;
            float cooling = powf(0.001f / temp, 1.0f / steps_per_restart);

            for (int step = 0; step < steps_per_restart; step++) {
                int move_type = rand_r(&seed) % 100;
                int backup_s[28], backup_p1[W1];
                memcpy(backup_s, cur_s, sizeof(cur_s));
                memcpy(backup_p1, cur_p1, sizeof(cur_p1));

                if (move_type < 40) {
                    // 2-opt subsegment reverse in p1
                    int a = rand_r(&seed) % W1;
                    int b = rand_r(&seed) % W1;
                    if (a > b) { int t = a; a = b; b = t; }
                    while (a < b) {
                        int t = cur_p1[a]; cur_p1[a] = cur_p1[b]; cur_p1[b] = t;
                        a++; b--;
                    }
                } else if (move_type < 75) {
                    // Swap in p1
                    int a = rand_r(&seed) % W1;
                    int b = rand_r(&seed) % W1;
                    int t = cur_p1[a]; cur_p1[a] = cur_p1[b]; cur_p1[b] = t;
                } else {
                    // Perturb a shift in cur_s
                    int pos = rand_r(&seed) % 28;
                    int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25; // +1 or -1 mod 26
                    cur_s[pos] = (cur_s[pos] + delta) % 26;
                }

                int new_def = 0; float new_std = 0.0f;
                float new_opt = eval_state(cur_s, cur_p1, &new_def, &new_std);

                float diff = new_opt - cur_opt;
                if (diff > 0.0f || expf(diff / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_opt = new_opt;
                    cur_std = new_std;
                    cur_def = new_def;
                } else {
                    memcpy(cur_s, backup_s, sizeof(cur_s));
                    memcpy(cur_p1, backup_p1, sizeof(cur_p1));
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
                        memcpy(global_s, cur_s, sizeof(cur_s));
                        memcpy(global_p1, cur_p1, sizeof(cur_p1));

                        printf("[Thread %d | Rep %d] Record: Defects=%d / %d (%.1f%% valid) | StdScore=%.4f\n",
                               omp_get_thread_num(), rep, global_min_def, TOTAL_QUADS,
                               (1.0f - (float)global_min_def / TOTAL_QUADS) * 100.0f, global_best_std);
                        fflush(stdout);

                        FILE *fout = fopen("pk9_joint_best.txt", "w");
                        if (fout) {
                            int Z[N], mid[N], pt[N];
                            for (int t = 0; t < N; t++) {
                                int shift = global_s[t % 28];
                                int p_kr = (ct_kr[t] - shift + 26) % 26;
                                Z[t] = k2std[p_kr];
                            }
                            invert_col(Z, W2, H2, p2, mid);
                            for (int r = 0; r < 8; r++) {
                                for (int c = 0; c < 18; c++) {
                                    pt[r * 18 + c] = mid[global_p1[c] * 8 + r];
                                }
                            }
                            fprintf(fout, "# PK9 Record Defects: %d / %d | StdScore: %.4f\n", global_min_def, TOTAL_QUADS, global_best_std);
                            fprintf(fout, "s = [");
                            for (int k = 0; k < 28; k++) fprintf(fout, "%d%s", global_s[k], k < 27 ? ", " : "]\n");
                            fprintf(fout, "p1 = [");
                            for (int k = 0; k < W1; k++) fprintf(fout, "%d%s", global_p1[k], k < W1-1 ? ", " : "]\n\n");
                            for (int r = 0; r < 8; r++) {
                                fprintf(fout, "Row %d: ", r);
                                for (int c = 0; c < 18; c++) fputc('A' + pt[r * 18 + c], fout);
                                fputc('\n', fout);
                            }
                            fclose(fout);
                        }
                    }
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("\n======================================================================\n");
    printf("PK9 JOINT DEFECT MINIMIZER COMPLETED in %.2f s\n", t1 - t0);
    printf("Global Min Defects: %d / %d (%.1f%% valid) | StdScore: %.4f\n",
           global_min_def, TOTAL_QUADS, (1.0f - (float)global_min_def / TOTAL_QUADS) * 100.0f, global_best_std);
    printf("======================================================================\n");

    return 0;
}
