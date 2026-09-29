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
static int Z[N];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }

    const int Q7_PK[7] = {0, 22, 3, 3, 15, 0, 1};
    const int q8[8] = {22, 15, 5, 9, 20, 6, 4, 6};
    const int q9[9] = {23, 2, 25, 22, 18, 9, 13, 13, 24};

    for (int i = 0; i < N; i++) {
        int k = (Q7_PK[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = alpha_to_std[p];
    }
}

static inline float eval_perm(const int *perm) {
    int pt[N];
    int idx = 0;
    for (int r = 0; r < H; r++) {
        int base = r * W;
        for (int c = 0; c < W; c++) {
            pt[idx++] = Z[base + perm[c]];
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

    int restarts = (argc > 1) ? atoi(argv[1]) : 50000;

    printf("======================================================================\n");
    printf("PK10 High-Throughput 42-Column Annealer (Pure Transposition on Fixed Z)\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    int seed_perm[W] = {
        4, 6, 34, 19, 29, 13, 11, 8, 35, 21,
        2, 40, 37, 18, 38, 0, 26, 30, 14, 16,
        9, 10, 24, 3, 32, 41, 22, 39, 20, 1,
        15, 7, 28, 5, 33, 31, 25, 17, 36, 12, 27, 23
    };

    float global_best_sc = eval_perm(seed_perm);
    printf("Initial Seed Score: %.4f\n\n", global_best_sc);

    int g_perm[W];
    memcpy(g_perm, seed_perm, W * sizeof(int));
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 9999 + omp_get_thread_num() * 8831;
        float loc_best_sc = -999.0f;
        int l_perm[W];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < restarts; rep++) {
            int perm[W];
            if (rep == 0) {
                memcpy(perm, g_perm, W * sizeof(int));
            } else if (rep % 2 == 0) {
                // Mutate global best
                memcpy(perm, g_perm, W * sizeof(int));
                int num_swaps = 1 + rand_r(&seed) % 5;
                for (int s = 0; s < num_swaps; s++) {
                    int c1 = rand_r(&seed) % W, c2 = rand_r(&seed) % W;
                    int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                }
            } else {
                // Random permutation
                for (int i = 0; i < W; i++) perm[i] = i;
                for (int i = W - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = perm[i]; perm[i] = perm[j]; perm[j] = tmp;
                }
            }

            float cur_sc = eval_perm(perm);
            float temp = 1.0f;
            float cooling = 0.999f;

            for (int step = 0; step < 2500; step++) {
                int c1 = rand_r(&seed) % W;
                int c2 = rand_r(&seed) % W;
                if (c1 == c2) continue;

                int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                float sc = eval_perm(perm);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    perm[c2] = perm[c1]; perm[c1] = tmp;
                }

                temp *= cooling;
            }

            // Polish with 2-opt swaps
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int i = 0; i < W - 1; i++) {
                    for (int j = i + 1; j < W; j++) {
                        int t = perm[i]; perm[i] = perm[j]; perm[j] = t;
                        float sc = eval_perm(perm);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            improved = 1;
                        } else {
                            perm[j] = perm[i]; perm[i] = t;
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_perm, perm, W * sizeof(int));
                int idx = 0;
                for (int r = 0; r < H; r++) {
                    int base = r * W;
                    for (int c = 0; c < W; c++) {
                        l_pt[idx++] = 'A' + Z[base + perm[c]];
                    }
                }
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_perm, l_perm, W * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] NEW RECORD: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  Order: [");
                for (int i = 0; i < 10; i++) printf("%d, ", g_perm[i]);
                printf("...]\n");
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("PK10 42-COL RUN COMPLETED (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Best Score: %.4f\n", global_best_sc);
    printf("Order (len 42): [");
    for (int i = 0; i < W; i++) printf("%d%s", g_perm[i], i==W-1?"":", ");
    printf("]\n\n");

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
