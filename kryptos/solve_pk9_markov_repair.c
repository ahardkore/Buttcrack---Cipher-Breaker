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

static const int p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
static const int p2[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

static int pt_to_z[N];
static int z_mod28[N];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];

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
        z_mod28[i] = pt_to_z[i] % 28;
    }
}

static inline float eval_shifts(const int *shifts28, int *out_pt) {
    int pt[N];
    for (int i = 0; i < N; i++) {
        int z_idx = pt_to_z[i];
        int s = shifts28[z_mod28[i]];
        int p_kr = (ct_kr[z_idx] - s + 26) % 26;
        pt[i] = k2std[p_kr];
    }
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

    int base_shifts[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};

    float base_sc = eval_shifts(base_shifts, NULL);
    printf("======================================================================\n");
    printf("PK9 Markov Boundary Repair Engine (Multi-Shift Neighborhood Sweep)\n");
    printf("Baseline Fitness: %.4f\n", base_sc);
    printf("======================================================================\n\n");

    // Boundary shift indices: {5, 8, 10, 11, 14, 16, 19, 21, 24, 25}
    int target_indices[10] = {5, 8, 10, 11, 14, 16, 19, 21, 24, 25};

    float global_best_sc = base_sc;
    int g_shifts[28];
    memcpy(g_shifts, base_shifts, 28 * sizeof(int));
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    // Multi-restart simulated annealing over the 10 boundary shifts with local search
    int restarts = (argc > 1) ? atoi(argv[1]) : 50000;

    #pragma omp parallel
    {
        unsigned int seed = 9999 + omp_get_thread_num() * 3779;
        float loc_best_sc = base_sc;
        int l_shifts[28];
        memcpy(l_shifts, base_shifts, 28 * sizeof(int));
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < restarts; rep++) {
            int cur_shifts[28];
            memcpy(cur_shifts, g_shifts, 28 * sizeof(int));

            // Small perturbation on boundary shifts
            if (rep > 0) {
                int muts = 1 + rand_r(&seed) % 4;
                for (int m = 0; m < muts; m++) {
                    int idx = target_indices[rand_r(&seed) % 10];
                    cur_shifts[idx] = (cur_shifts[idx] + (rand_r(&seed) % 5) - 2 + 26) % 26;
                }
            }

            float cur_sc = eval_shifts(cur_shifts, NULL);
            float temp = 0.6f;
            float cooling = 0.9992f;

            for (int step = 0; step < 2000; step++) {
                int idx = target_indices[rand_r(&seed) % 10];
                int old_v = cur_shifts[idx];
                int new_v = (old_v + (rand_r(&seed) % 5) - 2 + 26) % 26;
                cur_shifts[idx] = new_v;

                float sc = eval_shifts(cur_shifts, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    cur_shifts[idx] = old_v;
                }

                temp *= cooling;
            }

            // Polish with coordinate descent on the 10 boundary shifts
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int i = 0; i < 10; i++) {
                    int idx = target_indices[i];
                    int old_v = cur_shifts[idx];
                    int best_v = old_v;
                    float best_s = cur_sc;

                    for (int diff = 1; diff < 26; diff++) {
                        cur_shifts[idx] = (old_v + diff) % 26;
                        float sc = eval_shifts(cur_shifts, NULL);
                        if (sc > best_s + 1e-4f) {
                            best_s = sc;
                            best_v = cur_shifts[idx];
                        }
                    }

                    cur_shifts[idx] = best_v;
                    if (best_v != old_v) {
                        cur_sc = best_s;
                        improved = 1;
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_shifts, cur_shifts, 28 * sizeof(int));
                int pt_arr[N];
                eval_shifts(cur_shifts, pt_arr);
                for (int t = 0; t < N; t++) l_pt[t] = 'A' + pt_arr[t];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_shifts, l_shifts, 28 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] MARKOV BREAKTHROUGH: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("MARKOV REPAIR COMPLETED in %.3f s\n", elapsed);
    printf("======================================================================\n");
    printf("Final Score: %.4f\n", global_best_sc);
    printf("Final Shifts: [");
    for (int i = 0; i < 28; i++) printf("%d%s", g_shifts[i], i==27?"":", ");
    printf("]\n");
    printf("Key in KR:    ");
    for (int i = 0; i < 28; i++) printf("%c", KRYPTOS[g_shifts[i]]);
    printf("\n\n");

    int final_pt[N];
    eval_shifts(g_shifts, final_pt);
    char pt_str[N + 1];
    for (int i = 0; i < N; i++) pt_str[i] = 'A' + final_pt[i];
    pt_str[N] = '\0';

    printf("Full Plaintext:\n%s\n\n", pt_str);

    printf("Plaintext layout in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[19];
        memcpy(buf, pt_str + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}
