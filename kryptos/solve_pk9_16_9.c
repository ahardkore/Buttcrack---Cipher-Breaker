#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W1 16
#define H1 9
#define W2 9
#define H2 16

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

    int restarts = (argc > 1) ? atoi(argv[1]) : 15000;

    printf("======================================================================\n");
    printf("Joint Polishing Annealer on RAW PK9 under Pair (16, 9)\n");
    printf("Grid: 9 rows x 16 cols | Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    int init_shifts[28] = {15, 10, 13, 17, 17, 5, 6, 10, 5, 3, 11, 21, 14, 7, 10, 10, 7, 10, 7, 6, 21, 0, 18, 5, 15, 10, 13, 3};
    int init_p1[W1] = {14, 13, 15, 0, 11, 5, 4, 2, 8, 3, 6, 9, 12, 10, 1, 7};
    int init_p2[W2] = {0, 3, 5, 6, 8, 7, 2, 4, 1};

    float global_best_sc = -5.6065f;
    int g_shifts[28], g_p1[W1], g_p2[W2];
    memcpy(g_shifts, init_shifts, 28 * sizeof(int));
    memcpy(g_p1, init_p1, W1 * sizeof(int));
    memcpy(g_p2, init_p2, W2 * sizeof(int));
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 999 + omp_get_thread_num() * 3779;
        float loc_best_sc = -999.0f;
        int l_shifts[28], l_p1[W1], l_p2[W2];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int shifts[28], p1[W1], p2[W2];
            memcpy(shifts, g_shifts, 28 * sizeof(int));
            memcpy(p1, g_p1, W1 * sizeof(int));
            memcpy(p2, g_p2, W2 * sizeof(int));

            if (rep > 0) {
                int muts = 1 + rand_r(&seed) % 3;
                for (int m = 0; m < muts; m++) {
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
                int old_s, new_s, pos, c1, c2, tmp;

                if (move_type == 0) {
                    pos = rand_r(&seed) % 28; old_s = shifts[pos];
                    new_s = (old_s + 1 + (rand_r(&seed) % 25)) % 26;
                    shifts[pos] = new_s;
                } else if (move_type == 1) {
                    c1 = rand_r(&seed) % W1; c2 = rand_r(&seed) % W1;
                    if (c1 == c2) continue;
                    tmp = p1[c1]; p1[c1] = p1[c2]; p1[c2] = tmp;
                } else {
                    c1 = rand_r(&seed) % W2; c2 = rand_r(&seed) % W2;
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
                printf("[Thread %d] BREAKTHROUGH on (16, 9): %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("FINAL RESULT for Pair (16, 9) [%d restarts in %.3f s]\n", restarts, elapsed);
    printf("Score: %.4f\n", global_best_sc);
    printf("Order 1 (W1=16): [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n");
    printf("Order 2 (W2=9):  [");
    for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
    printf("]\n\n");
    printf("Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext in 9 rows of 16 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[17];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}
