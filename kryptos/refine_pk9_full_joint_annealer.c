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
        for (int r = 0; r < h; r++) dst[r * w + col] = src[idx++];
    }
}

static inline float eval_full_system(const int *shifts28, const int *p1, const int *p2, int *out_pt) {
    int Z[N];
    for (int t = 0; t < N; t++) {
        int s = shifts28[t % 28];
        int p_kr = (ct_kr[t] - s + 26) % 26;
        Z[t] = k2std[p_kr];
    }

    int mid[N], pt[N];
    invert_col(Z, W2, H2, p2, mid);
    invert_col(mid, W1, H1, p1, pt);

    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    // Optimal unigram shifts (IDGLLOSDOPEUHADDADASUKMOIDGP):
    int init_shifts[28] = {
        15, 10, 13, 17, 17, 5, 6, 10, 5, 3, 11, 21, 14, 7, 10, 10, 7, 10, 7, 6, 21, 0, 18, 5, 15, 10, 13, 3
    };

    // Best permutations from ultra annealer (Score -5.3743):
    int init_p1[W1] = {6, 5, 13, 1, 10, 16, 0, 9, 3, 2, 17, 4, 8, 15, 12, 14, 11, 7};
    int init_p2[W2] = {0, 5, 3, 1, 7, 2, 6, 4};

    int total_restarts = (argc > 1) ? atoi(argv[1]) : 10000;

    printf("======================================================================\n");
    printf("Joint Polishing Annealer on RAW PK9: 28 Shifts + Double Columnar (18, 8)\n");
    printf("Seed Fitness: %.4f | Restarts: %d\n",
           eval_full_system(init_shifts, init_p1, init_p2, NULL), total_restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -5.3743f;
    int g_shifts[28], g_p1[W1], g_p2[W2];
    memcpy(g_shifts, init_shifts, 28 * sizeof(int));
    memcpy(g_p1, init_p1, W1 * sizeof(int));
    memcpy(g_p2, init_p2, W2 * sizeof(int));
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 2027;
        float loc_best_sc = -999.0f;
        int l_shifts[28], l_p1[W1], l_p2[W2];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < total_restarts; rep++) {
            int shifts[28], p1[W1], p2[W2];
            memcpy(shifts, g_shifts, 28 * sizeof(int));
            memcpy(p1, g_p1, W1 * sizeof(int));
            memcpy(p2, g_p2, W2 * sizeof(int));

            // Small perturbation to escape local basin
            if (rep > 0) {
                int n_mut = 1 + rand_r(&seed) % 3;
                for (int m = 0; m < n_mut; m++) {
                    int pos = rand_r(&seed) % 28;
                    shifts[pos] = (shifts[pos] + (rand_r(&seed) % 5) - 2 + 26) % 26;
                }
                int c1 = rand_r(&seed) % W1, c2 = rand_r(&seed) % W1;
                int tmp = p1[c1]; p1[c1] = p1[c2]; p1[c2] = tmp;
            }

            float cur_sc = eval_full_system(shifts, p1, p2, NULL);
            float temp = 0.8f;
            float cooling = 0.999f;

            for (int step = 0; step < 4000; step++) {
                int move_type = rand_r(&seed) % 3;

                int old_s, new_s, pos;
                int c1, c2, tmp;

                if (move_type == 0) {
                    pos = rand_r(&seed) % 28;
                    old_s = shifts[pos];
                    new_s = (old_s + 1 + (rand_r(&seed) % 25)) % 26;
                    shifts[pos] = new_s;
                } else if (move_type == 1) {
                    c1 = rand_r(&seed) % W1;
                    c2 = rand_r(&seed) % W1;
                    if (c1 == c2) continue;
                    tmp = p1[c1]; p1[c1] = p1[c2]; p1[c2] = tmp;
                } else {
                    c1 = rand_r(&seed) % W2;
                    c2 = rand_r(&seed) % W2;
                    if (c1 == c2) continue;
                    tmp = p2[c1]; p2[c1] = p2[c2]; p2[c2] = tmp;
                }

                float sc = eval_full_system(shifts, p1, p2, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (move_type == 0) shifts[pos] = old_s;
                    else if (move_type == 1) { p1[c2] = p1[c1]; p1[c1] = tmp; }
                    else { p2[c2] = p2[c1]; p2[c1] = tmp; }
                }

                temp *= cooling;
            }

            // Polish with greedy coordinate descent on shifts and column swaps
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int p = 0; p < 28; p++) {
                    int best_s = shifts[p], old_s = shifts[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        shifts[p] = (old_s + diff) % 26;
                        float sc = eval_full_system(shifts, p1, p2, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_s = shifts[p]; }
                    }
                    if (best_d > 1e-4f) { shifts[p] = best_s; cur_sc += best_d; improved = 1; }
                    else shifts[p] = old_s;
                }
                for (int i = 0; i < W2 - 1; i++) {
                    for (int j = i + 1; j < W2; j++) {
                        int t2 = p2[i]; p2[i] = p2[j]; p2[j] = t2;
                        float sc = eval_full_system(shifts, p1, p2, NULL);
                        if (sc > cur_sc + 1e-4f) { cur_sc = sc; improved = 1; }
                        else { p2[j] = p2[i]; p2[i] = t2; }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_shifts, shifts, 28 * sizeof(int));
                memcpy(l_p1, p1, W1 * sizeof(int));
                memcpy(l_p2, p2, W2 * sizeof(int));

                int pt_arr[N];
                eval_full_system(shifts, p1, p2, pt_arr);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt_arr[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_shifts, l_shifts, 28 * sizeof(int));
                memcpy(g_p1, l_p1, W1 * sizeof(int));
                memcpy(g_p2, l_p2, W2 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] BREAKTHROUGH: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("FINAL OPTIMAL RESULT (%d restarts in %.3f s)\n", total_restarts, elapsed);
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("Shifts: [");
    for (int i = 0; i < 28; i++) printf("%d%s", g_shifts[i], i==27?"":", ");
    printf("]\n");
    printf("Key KR: ");
    for (int i = 0; i < 28; i++) printf("%c", KRYPTOS[g_shifts[i]]);
    printf("\nOrder 1 (W1=18): [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n");
    printf("Order 2 (W2=8):  [");
    for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
    printf("]\n\n");
    printf("Full Plaintext:\n%s\n", g_pt);

    return 0;
}
