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
static int k2std[26];

// Proven GF(2) parity vectors
static const int par_q7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int par_q8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int par_q9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

void init_tables() {
    for (int i = 0; i < 26; i++) k2std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
}

static inline float score_matrix(const int *pt) {
    float sc = 0.0f;
    for (int r = 0; r < H; r++) {
        const int *row = pt + r * W;
        for (int c = 0; c < W - 3; c++) {
            sc += quad[row[c]][row[c+1]][row[c+2]][row[c+3]];
        }
    }
    return sc / (H * (W - 3));
}

// Fast check: returns 1 if Z passes English monogram criteria, 0 otherwise
static inline int passes_monogram_filter(const int *Z, float *out_ioc, int *out_rare, int *out_e) {
    int counts[26] = {0};
    for (int i = 0; i < N; i++) counts[Z[i]]++;

    int rare = counts[9] + counts[16] + counts[23] + counts[25]; // J, Q, X, Z
    if (rare > 14) return 0;

    int e_cnt = counts[4]; // E
    if (e_cnt < 30) return 0;

    int sp = 0;
    for (int c = 0; c < 26; c++) sp += counts[c] * (counts[c] - 1);
    float ioc = (float)sp / (N * (N - 1));
    if (ioc < 0.044f) return 0;

    if (out_ioc) *out_ioc = ioc;
    if (out_rare) *out_rare = rare;
    if (out_e) *out_e = e_cnt;
    return 1;
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 10000;

    printf("======================================================================\n");
    printf("PK10 Attack: Hard Monogram Linguistic Filter + Parity Constrained TSP\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    float global_best_ioc = 0.0f;
    int global_best_rare = 99;
    int best_q7[7], best_q8[8], best_q9[9], best_order[W];
    char best_pt[N + 1];

    const int init_order[W] = {
        30, 38, 21, 3, 25, 40, 17, 36, 12, 10, 29, 33, 8, 41, 7, 32, 20, 0, 23, 34, 19,
        2, 22, 27, 6, 37, 31, 24, 39, 18, 28, 35, 11, 13, 4, 26, 15, 5, 1, 14, 16, 9
    };

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 98765 + omp_get_thread_num() * 7777;
        float loc_best = -999.0f;
        float loc_ioc = 0.0f;
        int loc_rare = 99;
        int loc_q7[7], loc_q8[8], loc_q9[9], loc_order[W];
        char loc_pt[N + 1];

        #pragma omp for schedule(dynamic, 20)
        for (int rep = 0; rep < restarts; rep++) {
            int q7[7], q8[8], q9[9], order[W];

            // Initialize clocks adhering to GF(2) parity
            q7[0] = 0;
            for (int i = 1; i < 7; i++) q7[i] = par_q7[i] + 2 * (rand_r(&seed) % 13);
            q8[0] = 0;
            for (int i = 1; i < 8; i++) q8[i] = par_q8[i] + 2 * (rand_r(&seed) % 13);
            for (int i = 0; i < 9; i++) q9[i] = par_q9[i] + 2 * (rand_r(&seed) % 13);

            int Z[N];
            for (int i = 0; i < N; i++) {
                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                int p = (c_idx[i] - k + 26) % 26;
                Z[i] = k2std[p];
            }

            // Quick linguistic pre-filter
            float ioc; int rare, e_cnt;
            if (!passes_monogram_filter(Z, &ioc, &rare, &e_cnt)) continue;

            memcpy(order, init_order, W * sizeof(int));
            int grid[H][W], pt[N];
            int idx = 0;
            for (int c = 0; c < W; c++) {
                int col = order[c];
                for (int r = 0; r < H; r++) grid[r][col] = Z[idx++];
            }
            idx = 0;
            for (int r = 0; r < H; r++)
                for (int c = 0; c < W; c++) pt[idx++] = grid[r][c];

            float cur_sc = score_matrix(pt);

            // Polish order with 500 TSP swaps
            for (int step = 0; step < 500; step++) {
                int a = rand_r(&seed) % W;
                int b = rand_r(&seed) % W;
                if (a == b) continue;
                int t = order[a]; order[a] = order[b]; order[b] = t;

                idx = 0;
                for (int c = 0; c < W; c++) {
                    int col = order[c];
                    for (int r = 0; r < H; r++) grid[r][col] = Z[idx++];
                }
                idx = 0;
                for (int r = 0; r < H; r++)
                    for (int c = 0; c < W; c++) pt[idx++] = grid[r][c];

                float sc = score_matrix(pt);
                if (sc > cur_sc) {
                    cur_sc = sc;
                } else {
                    order[b] = order[a]; order[a] = t;
                }
            }

            if (cur_sc > loc_best) {
                loc_best = cur_sc;
                loc_ioc = ioc;
                loc_rare = rare;
                memcpy(loc_q7, q7, 7 * sizeof(int));
                memcpy(loc_q8, q8, 8 * sizeof(int));
                memcpy(loc_q9, q9, 9 * sizeof(int));
                memcpy(loc_order, order, W * sizeof(int));
                for (int i = 0; i < N; i++) loc_pt[i] = 'A' + pt[i];
                loc_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_sc) {
                global_best_sc = loc_best;
                global_best_ioc = loc_ioc;
                global_best_rare = loc_rare;
                memcpy(best_q7, loc_q7, 7 * sizeof(int));
                memcpy(best_q8, loc_q8, 8 * sizeof(int));
                memcpy(best_q9, loc_q9, 9 * sizeof(int));
                memcpy(best_order, loc_order, W * sizeof(int));
                strcpy(best_pt, loc_pt);
                printf("[Thread %d] Record: Score=%.4f, IoC=%.5f, Rare=%d (%.1f%%)\n",
                       omp_get_thread_num(), global_best_sc, global_best_ioc, global_best_rare,
                       (float)global_best_rare/N*100.0f);
                printf("  PT: %.60s...\n\n", best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("PK10 ATTACK COMPLETED in %.2f s | Best Score: %.4f\n", elapsed, global_best_sc);
    printf("======================================================================\n");
    printf("Monogram IoC: %.5f | Rare Letters: %d (%.1f%%)\n",
           global_best_ioc, global_best_rare, (float)global_best_rare/N*100.0f);
    printf("Final Q7: [");
    for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"":", ");
    printf("]\nFinal Q8: [");
    for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7?"":", ");
    printf("]\nFinal Q9: [");
    for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8?"":", ");
    printf("]\n\nFull Plaintext:\n%s\n\n", best_pt);

    return 0;
}
