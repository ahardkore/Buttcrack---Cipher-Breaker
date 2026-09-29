#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H (N / W) // 12

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

// Fixed Q7 from PK8/PK9:
static const int Q7_PK[7] = {0, 22, 3, 3, 15, 0, 1};

static inline float eval_full_pk10(const int *q8, const int *q9, const int *perm, int *out_pt) {
    int Z[N];
    for (int i = 0; i < N; i++) {
        int k = (Q7_PK[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        Z[i] = alpha_to_std[p];
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
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 5000;

    printf("======================================================================\n");
    printf("Joint 42-Column Annealer on PK10 (Q8, Q9, Perm42)\n");
    printf("Grid: 12 rows x 42 cols | Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    // Seed from two-clock run
    int seed_q8[8] = {4, 18, 24, 21, 8, 25, 19, 5};
    int seed_q9[9] = {8, 14, 1, 19, 20, 15, 13, 2, 24};
    int seed_perm[W];
    for (int i = 0; i < W; i++) seed_perm[i] = i;

    float global_best_sc = -999.0f;
    int g_q8[8], g_q9[9], g_perm[W];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 777 + omp_get_thread_num() * 3137;
        float loc_best_sc = -999.0f;
        int l_q8[8], l_q9[9], l_perm[W];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 10)
        for (int rep = 0; rep < restarts; rep++) {
            int q8[8], q9[9], perm[W];
            memcpy(q8, seed_q8, 8 * sizeof(int));
            memcpy(q9, seed_q9, 9 * sizeof(int));
            for (int i = 0; i < W; i++) perm[i] = i;

            // Perturb initial state
            if (rep > 0) {
                int swaps = 1 + rand_r(&seed) % 8;
                for (int s = 0; s < swaps; s++) {
                    int c1 = rand_r(&seed) % W, c2 = rand_r(&seed) % W;
                    int tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                }
                int p8 = rand_r(&seed) % 8;
                q8[p8] = (q8[p8] + (rand_r(&seed) % 5) - 2 + 26) % 26;
                int p9 = rand_r(&seed) % 9;
                q9[p9] = (q9[p9] + (rand_r(&seed) % 5) - 2 + 26) % 26;
            }

            float cur_sc = eval_full_pk10(q8, q9, perm, NULL);
            float temp = 1.5f;
            float cooling = 0.9992f;

            for (int step = 0; step < 4500; step++) {
                int move_type = rand_r(&seed) % 3;
                int old_v, new_v, pos, c1, c2, tmp;

                if (move_type == 0) {
                    pos = rand_r(&seed) % 8; old_v = q8[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q8[pos] = new_v;
                } else if (move_type == 1) {
                    pos = rand_r(&seed) % 9; old_v = q9[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q9[pos] = new_v;
                } else {
                    c1 = rand_r(&seed) % W; c2 = rand_r(&seed) % W;
                    if (c1 == c2) continue;
                    tmp = perm[c1]; perm[c1] = perm[c2]; perm[c2] = tmp;
                }

                float sc = eval_full_pk10(q8, q9, perm, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (move_type == 0) q8[pos] = old_v;
                    else if (move_type == 1) q9[pos] = old_v;
                    else { perm[c2] = perm[c1]; perm[c1] = tmp; }
                }

                temp *= cooling;
            }

            // Polish with 2-opt swaps on columns
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int i = 0; i < W - 1; i++) {
                    for (int j = i + 1; j < W; j++) {
                        int t = perm[i]; perm[i] = perm[j]; perm[j] = t;
                        float sc = eval_full_pk10(q8, q9, perm, NULL);
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
                memcpy(l_q8, q8, 8 * sizeof(int));
                memcpy(l_q9, q9, 9 * sizeof(int));
                memcpy(l_perm, perm, W * sizeof(int));

                int pt_arr[N];
                eval_full_pk10(q8, q9, perm, pt_arr);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt_arr[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q8, l_q8, 8 * sizeof(int));
                memcpy(g_q9, l_q9, 9 * sizeof(int));
                memcpy(g_perm, l_perm, W * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] PK10 RECORD: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("FINAL OPTIMAL PK10 RESULT (%d restarts in %.3f s)\n", restarts, elapsed);
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
    printf(")\n");
    printf("Order (len 42): [");
    for (int i = 0; i < W; i++) printf("%d%s", g_perm[i], i==W-1?"":", ");
    printf("]\n\n");

    printf("Full Plaintext:\n%s\n\n", g_pt);

    printf("Plaintext layout in 12 rows of 42 chars:\n");
    for (int r = 0; r < H; r++) {
        char buf[43];
        memcpy(buf, g_pt + r * W, W);
        buf[W] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}
