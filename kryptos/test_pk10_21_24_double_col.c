#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W1 21
#define H1 24
#define W2 24
#define H2 21

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

// Invert double columnar:
// Z was produced by writing P (H1 x W1) by rows -> reading out columns permuted by p1 -> writing into (H2 x W2) by rows -> reading out columns permuted by p2 -> Z
// To invert:
// 1. Write Z into columns of (H2 x W2) permuted by p2 -> read out by rows = mid (H2 x W2)
// 2. Write mid into columns of (H1 x W1) permuted by p1 -> read out by rows = P (H1 x W1)
static inline float eval_double_col_21_24(const int *p1, const int *p2, int *pt_out) {
    int g2[H2][W2];
    int idx = 0;
    for (int c = 0; c < W2; c++) {
        int col = p2[c];
        for (int r = 0; r < H2; r++) {
            g2[r][col] = Z[idx++];
        }
    }

    int mid[N];
    idx = 0;
    for (int r = 0; r < H2; r++) {
        for (int c = 0; c < W2; c++) {
            mid[idx++] = g2[r][c];
        }
    }

    int g1[H1][W1];
    idx = 0;
    for (int c = 0; c < W1; c++) {
        int col = p1[c];
        for (int r = 0; r < H1; r++) {
            g1[r][col] = mid[idx++];
        }
    }

    idx = 0;
    for (int r = 0; r < H1; r++) {
        for (int c = 0; c < W1; c++) {
            pt_out[idx++] = g1[r][c];
        }
    }

    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad[pt_out[i]][pt_out[i+1]][pt_out[i+2]][pt_out[i+3]];
    }
    return sc / (N - 3);
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 5000;

    printf("======================================================================\n");
    printf("PK10 Coupled Double-Columnar Annealer: W1=21 (3x7) x W2=24 (3x8)\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int g_p1[W1], g_p2[W2];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 44444 + omp_get_thread_num() * 9973;
        float loc_best_sc = -999.0f;
        int l_p1[W1], l_p2[W2];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 50)
        for (int rep = 0; rep < restarts; rep++) {
            int p1[W1], p2[W2];
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

            int pt[N];
            float cur_sc = eval_double_col_21_24(p1, p2, pt);
            float temp = 1.0f;
            float cooling = 0.998f;

            for (int step = 0; step < 2000; step++) {
                int move = rand_r(&seed) % 2;
                if (move == 0) {
                    int c1 = rand_r(&seed) % W1, c2 = rand_r(&seed) % W1;
                    if (c1 == c2) continue;
                    int t = p1[c1]; p1[c1] = p1[c2]; p1[c2] = t;
                    float sc = eval_double_col_21_24(p1, p2, pt);
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
                    float sc = eval_double_col_21_24(p1, p2, pt);
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
                        float sc = eval_double_col_21_24(p1, p2, pt);
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
                        float sc = eval_double_col_21_24(p1, p2, pt);
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
                eval_double_col_21_24(p1, p2, pt);
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
                printf("  PT: %.70s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("PK10 (21, 24) RUN COMPLETED (%d restarts in %.3f s)\n", restarts, elapsed);
    printf("======================================================================\n");
    printf("Best Score: %.4f\n", global_best_sc);
    printf("P1 (W=21): [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n");
    printf("P2 (W=24): [");
    for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
    printf("]\n\n");

    printf("Full Plaintext:\n%s\n\n", g_pt);
    printf("Plaintext layout in %d rows of %d chars:\n", H1, W1);
    for (int r = 0; r < H1; r++) {
        char buf[W1 + 1];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}
