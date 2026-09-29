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
static int Z[N];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];

    const int s[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
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

static inline float eval_double_col(const int *p1, const int *p2, int *out_pt) {
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

    int restarts = (argc > 1) ? atoi(argv[1]) : 50000;

    printf("======================================================================\n");
    printf("PK9 Double Columnar (18, 8) Ultra Annealer on Fixed Z\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    int seed_p1[W1] = {5, 1, 12, 2, 11, 10, 4, 3, 17, 7, 13, 14, 9, 8, 15, 0, 16, 6};
    int seed_p2[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

    int dummy[N];
    float global_best_sc = eval_double_col(seed_p1, seed_p2, dummy);
    printf("Baseline Seed Score: %.4f\n\n", global_best_sc);

    int g_p1[W1], g_p2[W2];
    memcpy(g_p1, seed_p1, W1 * sizeof(int));
    memcpy(g_p2, seed_p2, W2 * sizeof(int));
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 55555 + omp_get_thread_num() * 11113;
        float loc_best_sc = global_best_sc;
        int l_p1[W1], l_p2[W2];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < restarts; rep++) {
            int p1[W1], p2[W2];
            if (rep == 0) {
                memcpy(p1, g_p1, W1 * sizeof(int));
                memcpy(p2, g_p2, W2 * sizeof(int));
            } else if (rep % 2 == 0) {
                memcpy(p1, g_p1, W1 * sizeof(int));
                memcpy(p2, g_p2, W2 * sizeof(int));
                int s1 = 1 + rand_r(&seed) % 3;
                for (int s = 0; s < s1; s++) {
                    int c1 = rand_r(&seed) % W1, c2 = rand_r(&seed) % W1;
                    int t = p1[c1]; p1[c1] = p1[c2]; p1[c2] = t;
                }
                int s2 = 1 + rand_r(&seed) % 2;
                for (int s = 0; s < s2; s++) {
                    int c1 = rand_r(&seed) % W2, c2 = rand_r(&seed) % W2;
                    int t = p2[c1]; p2[c1] = p2[c2]; p2[c2] = t;
                }
            } else {
                for (int i = 0; i < W1; i++) p1[i] = i;
                for (int i = W1 - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int t = p1[i]; p1[i] = p1[j]; p1[j] = t;
                }
                for (int i = 0; i < W2; i++) p2[i] = i;
                for (int i = W2 - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int t = p2[i]; p2[i] = p2[j]; p2[j] = t;
                }
            }

            int pt[N];
            float cur_sc = eval_double_col(p1, p2, pt);
            float temp = 1.0f;
            float cooling = 0.998f;

            for (int step = 0; step < 1500; step++) {
                int move = rand_r(&seed) % 2;
                if (move == 0) {
                    int c1 = rand_r(&seed) % W1, c2 = rand_r(&seed) % W1;
                    if (c1 == c2) continue;
                    int t = p1[c1]; p1[c1] = p1[c2]; p1[c2] = t;
                    float sc = eval_double_col(p1, p2, pt);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        t = p1[c1]; p1[c1] = p1[c2]; p1[c2] = t;
                    }
                } else {
                    int c1 = rand_r(&seed) % W2, c2 = rand_r(&seed) % W2;
                    if (c1 == c2) continue;
                    int t = p2[c1]; p2[c1] = p2[c2]; p2[c2] = t;
                    float sc = eval_double_col(p1, p2, pt);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        t = p2[c1]; p2[c1] = p2[c2]; p2[c2] = t;
                    }
                }
                temp *= cooling;
            }

            // Polish 2-opt
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int i = 0; i < W2 - 1; i++) {
                    for (int j = i + 1; j < W2; j++) {
                        int t = p2[i]; p2[i] = p2[j]; p2[j] = t;
                        float sc = eval_double_col(p1, p2, pt);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            imp = 1;
                        } else {
                            t = p2[i]; p2[i] = p2[j]; p2[j] = t;
                        }
                    }
                }
                for (int i = 0; i < W1 - 1; i++) {
                    for (int j = i + 1; j < W1; j++) {
                        int t = p1[i]; p1[i] = p1[j]; p1[j] = t;
                        float sc = eval_double_col(p1, p2, pt);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            imp = 1;
                        } else {
                            t = p1[i]; p1[i] = p1[j]; p1[j] = t;
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_p1, p1, W1 * sizeof(int));
                memcpy(l_p2, p2, W2 * sizeof(int));
                eval_double_col(p1, p2, pt);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_p1, l_p1, W1 * sizeof(int));
                memcpy(g_p2, l_p2, W2 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] NEW RECORD: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  P1: [");
                for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
                printf("]\n");
                printf("  P2: [");
                for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
                printf("]\n");
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("RUN COMPLETED (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Best Score: %.4f\n", global_best_sc);
    printf("P1 (W=18): [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n");
    printf("P2 (W=8):  [");
    for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
    printf("]\n\n");

    printf("Full Plaintext:\n%s\n\n", g_pt);
    printf("Plaintext layout in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[W1 + 1];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}
