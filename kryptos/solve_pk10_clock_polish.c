#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H 12

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
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int alpha_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
}

static const int Q7_PK[7] = {0, 22, 3, 3, 15, 0, 1};

static const int fixed_perm[W] = {
    40, 19, 9, 7, 41, 8, 33, 32, 13, 0,
    20, 16, 14, 15, 28, 22, 30, 38, 21, 31,
    6, 34, 36, 17, 4, 10, 24, 2, 39, 18,
    35, 37, 23, 11, 12, 29, 26, 5, 1, 3,
    25, 27
};

static inline float eval_clocks(const int *q8, const int *q9) {
    int Z[N], pt[N];
    for (int i = 0; i < N; i++) {
        int k = (Q7_PK[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = alpha_to_std[p];
    }
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int base = r * W;
        for (int c = 0; c < W; c++) {
            pt[idx++] = Z[base + fixed_perm[c]];
        }
    }
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 20000;

    printf("======================================================================\n");
    printf("PK10 Clock Polish on Record Permutation (Order Len 42)\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    int seed_q8[8] = {22, 15, 5, 9, 20, 6, 4, 6};
    int seed_q9[9] = {23, 2, 25, 22, 18, 9, 13, 13, 24};

    float global_best_sc = eval_clocks(seed_q8, seed_q9);
    printf("Initial Clocks Score: %.4f\n\n", global_best_sc);

    int g_q8[8], g_q9[9];
    memcpy(g_q8, seed_q8, 8 * sizeof(int));
    memcpy(g_q9, seed_q9, 9 * sizeof(int));
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 4321 + omp_get_thread_num() * 6653;
        float loc_best_sc = -999.0f;
        int l_q8[8], l_q9[9];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < restarts; rep++) {
            int q8[8], q9[9];
            if (rep == 0) {
                memcpy(q8, g_q8, 8 * sizeof(int));
                memcpy(q9, g_q9, 9 * sizeof(int));
            } else if (rep % 2 == 0) {
                memcpy(q8, g_q8, 8 * sizeof(int));
                memcpy(q9, g_q9, 9 * sizeof(int));
                int p8 = rand_r(&seed) % 8;
                q8[p8] = (q8[p8] + rand_r(&seed) % 5 - 2 + 26) % 26;
                int p9 = rand_r(&seed) % 9;
                q9[p9] = (q9[p9] + rand_r(&seed) % 5 - 2 + 26) % 26;
            } else {
                for (int i = 0; i < 8; i++) q8[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;
            }

            float cur_sc = eval_clocks(q8, q9);
            float temp = 1.0f;
            float cooling = 0.995f;

            for (int step = 0; step < 1200; step++) {
                int move = rand_r(&seed) % 17;
                int old_v, new_v;
                if (move < 8) {
                    old_v = q8[move];
                    new_v = (old_v + 1 + rand_r(&seed) % 25) % 26;
                    q8[move] = new_v;
                    float sc = eval_clocks(q8, q9);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q8[move] = old_v;
                    }
                } else {
                    int p = move - 8;
                    old_v = q9[p];
                    new_v = (old_v + 1 + rand_r(&seed) % 25) % 26;
                    q9[p] = new_v;
                    float sc = eval_clocks(q8, q9);
                    float delta = sc - cur_sc;
                    if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = sc;
                    } else {
                        q9[p] = old_v;
                    }
                }
                temp *= cooling;
            }

            // Polish with greedy coordinate descent
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int i = 0; i < 8; i++) {
                    int orig = q8[i];
                    for (int cand = 0; cand < 26; cand++) {
                        if (cand == orig) continue;
                        q8[i] = cand;
                        float sc = eval_clocks(q8, q9);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            orig = cand;
                            imp = 1;
                        }
                    }
                    q8[i] = orig;
                }
                for (int i = 0; i < 9; i++) {
                    int orig = q9[i];
                    for (int cand = 0; cand < 26; cand++) {
                        if (cand == orig) continue;
                        q9[i] = cand;
                        float sc = eval_clocks(q8, q9);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            orig = cand;
                            imp = 1;
                        }
                    }
                    q9[i] = orig;
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_q8, q8, 8 * sizeof(int));
                memcpy(l_q9, q9, 9 * sizeof(int));

                // Generate plaintext
                int Z[N];
                for (int i = 0; i < N; i++) {
                    int k = (Q7_PK[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                    int p = (c_idx[i] - k + 26) % 26;
                    Z[i] = alpha_to_std[p];
                }
                int idx = 0;
                for (int r = 0; r < H; r++) {
                    int base = r * W;
                    for (int c = 0; c < W; c++) {
                        l_pt[idx++] = 'A' + Z[base + fixed_perm[c]];
                    }
                }
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q8, l_q8, 8 * sizeof(int));
                memcpy(g_q9, l_q9, 9 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] NEW RECORD: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Q8: [");
                for (int i = 0; i < 8; i++) printf("%d, ", g_q8[i]);
                printf("]\n  Q9: [");
                for (int i = 0; i < 9; i++) printf("%d, ", g_q9[i]);
                printf("]\n  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("PK10 CLOCK POLISH COMPLETED (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Best Score: %.4f\n", global_best_sc);
    printf("Q8: [");
    for (int i = 0; i < 8; i++) printf("%d%s", g_q8[i], i==7?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 8; i++) printf("%c", KRYPTOS[g_q8[i]]);
    printf(")\n");
    printf("Q9: [");
    for (int i = 0; i < 9; i++) printf("%d%s", g_q9[i], i==8?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 9; i++) printf("%c", KRYPTOS[g_q9[i]]);
    printf(")\n\n");

    printf("Full Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext layout in 12 rows of 42 chars:\n");
    for (int r = 0; r < H; r++) {
        char buf[W + 1];
        memcpy(buf, g_pt + r * W, W);
        buf[W] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}
