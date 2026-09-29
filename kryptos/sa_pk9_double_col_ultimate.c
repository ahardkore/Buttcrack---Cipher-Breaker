#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";

// Two intermediate text candidates
static const char *Z_cands[2] = {
    // Cand 0: Pure Q7 derived intermediate
    "KTNWGSTYKVOVNSENPXAVKTOSXMSKQSEMMJPWHLASMEYGYNOSIHRECTNSSNOEETLLCOLTIEAIORPEAXTABEMSNNSFXMSUHOILNSUTGTBEZCYWEDMASNCDDCOUMTJTDSUMTATTNEUWJWFAIHIK",
    // Cand 1: Q4 x Q7 derived intermediate
    "KLBQKNSFKCANNSKPPXCSGLQJEMUWQNKIOPOAHTCPMELWYNAJYRJUVTBPSSQBXLNRCMNRIEVZOROUQENLUEAPNSUCEOBOHMLHNSDHGTDUFVLAXDATSSXAWVAOMLMRDSDYTASHSXDAPWRTIRTW"
};

static float quadgrams[26][26][26][26];

void load_quads(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("english_quadgrams.txt missing\n"); exit(1); }
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    fseek(f, 0, SEEK_SET);
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)cnt / total);
            }
        }
    }
    fclose(f);
}

// Complete columnar decryption
static inline void col_decrypt(const char *in, const int *order, char *out, int w, int h) {
    char grid[H][W];
    int idx = 0;
    for (int k = 0; k < w; k++) {
        int col = order[k];
        for (int r = 0; r < h; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) out[idx++] = grid[r][c];
    out[N] = '\0';
}

static inline float score_pt(const char *pt) {
    float sc = 0;
    for (int t = 0; t < N - 3; t++) {
        int a = pt[t] - 'A';
        int b = pt[t+1] - 'A';
        int c = pt[t+2] - 'A';
        int d = pt[t+3] - 'A';
        sc += quadgrams[a][b][c][d];
    }
    return sc / (N - 3);
}

// Fast xorshift PRNG per thread
static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

static inline float rand_float(unsigned int *state) {
    return (float)xorshift32(state) / 4294967296.0f;
}

int main(int argc, char **argv) {
    load_quads();

    int total_restarts = (argc > 1) ? atoi(argv[1]) : 64;
    int steps_per_restart = (argc > 2) ? atoi(argv[2]) : 500000;

    printf("Starting Double Columnar SA on PK9: %d restarts, %d steps each\n",
        total_restarts, steps_per_restart);

    float global_best_sc = -1e9f;
    char global_best_pt[N + 1];
    int global_best_o1[W], global_best_o2[W];
    int global_best_cand = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 12345));

        #pragma omp for schedule(dynamic, 1)
        for (int run = 0; run < total_restarts; run++) {
            int cand_idx = run % 2;
            const char *src_z = Z_cands[cand_idx];

            int o1[W], o2[W];
            for (int i = 0; i < W; i++) { o1[i] = i; o2[i] = i; }

            // Random shuffle
            for (int i = W - 1; i > 0; i--) {
                int j1 = xorshift32(&seed) % (i + 1);
                int t = o1[i]; o1[i] = o1[j1]; o1[j1] = t;
                int j2 = xorshift32(&seed) % (i + 1);
                t = o2[i]; o2[i] = o2[j2]; o2[j2] = t;
            }

            char z1[N + 1], pt[N + 1];
            col_decrypt(src_z, o2, z1, W, H);
            col_decrypt(z1, o1, pt, W, H);
            float cur_sc = score_pt(pt);

            float best_sc = cur_sc;
            int best_o1[W], best_o2[W];
            char best_pt[N + 1];
            memcpy(best_o1, o1, sizeof(o1));
            memcpy(best_o2, o2, sizeof(o2));
            strcpy(best_pt, pt);

            float temp = 2.0f;
            float cooling = expf(logf(0.01f / 2.0f) / steps_per_restart);

            for (int step = 0; step < steps_per_restart; step++) {
                int which = xorshift32(&seed) % 2; // modify o1 or o2
                int *target_o = which ? o2 : o1;

                int i = xorshift32(&seed) % W;
                int j = xorshift32(&seed) % W;
                while (i == j) j = xorshift32(&seed) % W;

                // Swap move
                int tmp = target_o[i]; target_o[i] = target_o[j]; target_o[j] = tmp;

                col_decrypt(src_z, o2, z1, W, H);
                col_decrypt(z1, o1, pt, W, H);
                float new_sc = score_pt(pt);

                float delta = new_sc - cur_sc;
                if (delta > 0 || rand_float(&seed) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_sc) {
                        best_sc = cur_sc;
                        memcpy(best_o1, o1, sizeof(o1));
                        memcpy(best_o2, o2, sizeof(o2));
                        strcpy(best_pt, pt);
                    }
                } else {
                    // Revert
                    target_o[j] = target_o[i]; target_o[i] = tmp;
                }

                temp *= cooling;
            }

            #pragma omp critical
            {
                if (best_sc > global_best_sc) {
                    global_best_sc = best_sc;
                    global_best_cand = cand_idx;
                    memcpy(global_best_o1, best_o1, sizeof(best_o1));
                    memcpy(global_best_o2, best_o2, sizeof(best_o2));
                    strcpy(global_best_pt, best_pt);
                    printf("[Run %2d] New Global Best: %.4f (Cand %d)\n",
                        run, global_best_sc, global_best_cand);
                    printf("  PT: %s\n", global_best_pt);
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("\nCompleted in %.2f seconds!\n", t1 - t0);
    printf("Global Best Score: %.4f\n", global_best_sc);
    printf("Best Cand: %d\n", global_best_cand);
    printf("Order 1: [");
    for (int i = 0; i < W; i++) printf("%d%s", global_best_o1[i], i < W - 1 ? ", " : "]\n");
    printf("Order 2: [");
    for (int i = 0; i < W; i++) printf("%d%s", global_best_o2[i], i < W - 1 ? ", " : "]\n");
    printf("Plaintext: %s\n", global_best_pt);

    return 0;
}
