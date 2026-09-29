#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504
#define COLS 42
#define ROWS 12

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];
static float unigram_logp[26];

// Standard English unigram log-frequencies
static const float standard_unigrams[26] = {
    0.08167f, 0.01492f, 0.02782f, 0.04253f, 0.12702f, 0.02228f, 0.02015f, // A-G
    0.06094f, 0.06966f, 0.00153f, 0.00772f, 0.04025f, 0.02406f, 0.06749f, // H-N
    0.07507f, 0.01929f, 0.00095f, 0.05987f, 0.06327f, 0.09056f, 0.02758f, // O-U
    0.00978f, 0.02360f, 0.00150f, 0.01974f, 0.00074f                     // V-Z
};

static void load_tables(void) {
    for (int i = 0; i < 26; i++) {
        unigram_logp[i] = logf(standard_unigrams[i]);
    }
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Missing english_quads.tsv\n"); exit(1); }
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        char q[5]; float sc;
        if (sscanf(buf, "%4s %f", q, &sc) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qtable[a][b][c][d] = sc;
                valid_q[a][b][c][d] = 1;
            }
        }
    }
    fclose(f);
}

// Compute monogram fitness for Z under candidate clocks
static inline float eval_unigram_fitness(const int q7[7], const int q8[8], const int q9[9], float *out_ioc, int *out_rare) {
    int counts[26] = {0};
    float score = 0.0f;
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (q7[i%7] + q8[i%8] + q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        char pt_char = KRYPTOS[pt_idx];
        int std_idx = pt_char - 'A';
        counts[std_idx]++;
        score += unigram_logp[std_idx];
    }
    int sum_pairs = 0;
    for (int i = 0; i < 26; i++) sum_pairs += counts[i] * (counts[i] - 1);
    *out_ioc = (float)sum_pairs / (float)(N * (N - 1));
    *out_rare = counts['J'-'A'] + counts['Q'-'A'] + counts['X'-'A'] + counts['Z'-'A'];
    return score / (float)N;
}

static inline void compute_grid(const int q7[7], const int q8[8], const int q9[9], char cols[COLS][ROWS]) {
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (q7[i%7] + q8[i%8] + q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            cols[c][r] = Z[c * ROWS + r];
        }
    }
}

static inline void eval_grid_order(const char cols[COLS][ROWS], const int order[COLS], float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= COLS - 4; c++) {
            int a = cols[order[c]][r] - 'A';
            int b = cols[order[c+1]][r] - 'A';
            int c_char = cols[order[c+2]][r] - 'A';
            int d = cols[order[c+3]][r] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 468.0f;
    *out_def = def;
}

int main(void) {
    load_tables();

    // 1. Injected Q7 from PK9 Row 3:
    // PK9 Row 3: [3, 22, 5, 0, 10, 7, 6]
    int q7_injected[7] = {3, 22, 5, 0, 10, 7, 6};

    printf("======================================================================\n");
    printf("TESTING PK9 ROW-3 INJECTED Q7 ON PK10: [3, 22, 5, 0, 10, 7, 6]\n");
    printf("======================================================================\n");

    // 2. Optimize Q8 (8 params) and Q9 (9 params) to maximize monogram fitness and IoC
    printf("\nStage 1: Annealing (Q8, Q9) given Injected Q7...\n");

    int best_q8[8], best_q9[9];
    float best_mono_fit = -999.0f;
    float best_ioc = 0.0f;
    int best_rare = 999;

    #pragma omp parallel
    {
        unsigned int seed = 999 + omp_get_thread_num() * 31337;
        int local_q8[8], local_q9[9];
        for (int i = 0; i < 8; i++) local_q8[i] = rand_r(&seed) % 26;
        for (int i = 0; i < 9; i++) local_q9[i] = rand_r(&seed) % 26;

        float cur_ioc; int cur_rare;
        float cur_fit = eval_unigram_fitness(q7_injected, local_q8, local_q9, &cur_ioc, &cur_rare);

        int steps = 300000;
        float T_start = 0.5f, T_end = 0.001f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_q8[8], next_q9[9];
            memcpy(next_q8, local_q8, sizeof(local_q8));
            memcpy(next_q9, local_q9, sizeof(local_q9));

            if (rand_r(&seed) % 2 == 0) {
                next_q8[rand_r(&seed) % 8] = rand_r(&seed) % 26;
            } else {
                next_q9[rand_r(&seed) % 9] = rand_r(&seed) % 26;
            }

            float next_ioc; int next_rare;
            float next_fit = eval_unigram_fitness(q7_injected, next_q8, next_q9, &next_ioc, &next_rare);

            // Objective: unigram log-likelihood + bonus for IoC - penalty for rare
            float cur_obj = cur_fit + (cur_ioc * 10.0f) - (cur_rare * 0.02f);
            float next_obj = next_fit + (next_ioc * 10.0f) - (next_rare * 0.02f);
            float d_fit = next_obj - cur_obj;

            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(local_q8, next_q8, sizeof(local_q8));
                memcpy(local_q9, next_q9, sizeof(local_q9));
                cur_fit = next_fit;
                cur_ioc = next_ioc;
                cur_rare = next_rare;
            }
        }

        #pragma omp critical
        {
            float my_obj = cur_fit + (cur_ioc * 10.0f) - (cur_rare * 0.02f);
            float glob_obj = best_mono_fit + (best_ioc * 10.0f) - (best_rare * 0.02f);
            if (my_obj > glob_obj) {
                best_mono_fit = cur_fit;
                best_ioc = cur_ioc;
                best_rare = cur_rare;
                memcpy(best_q8, local_q8, sizeof(local_q8));
                memcpy(best_q9, local_q9, sizeof(local_q9));
                printf("[Thread %d] Best Monogram State: Fit=%.4f | IoC=%.5f | Rare=%d / 504\n",
                       omp_get_thread_num(), best_mono_fit, best_ioc, best_rare);
            }
        }
    }

    printf("\nOptimized Clocks for Injected Q7:\n");
    printf("Q7: [3, 22, 5, 0, 10, 7, 6]\n");
    printf("Q8: ["); for(int i=0;i<8;i++) printf("%d%s", best_q8[i], i==7?"":", "); printf("]\n");
    printf("Q9: ["); for(int i=0;i<9;i++) printf("%d%s", best_q9[i], i==8?"":", "); printf("]\n");
    printf("Monogram IoC: %.5f | Rare Letters: %d (%.2f%%)\n", best_ioc, best_rare, best_rare/504.0f*100.0f);

    // 3. Stage 2: Anneal 42-column TSP grid on this intermediate text Z
    printf("\nStage 2: Annealing 42-Column TSP Transposition Grid...\n");
    char cols[COLS][ROWS];
    compute_grid(q7_injected, best_q8, best_q9, cols);

    int best_order[COLS];
    float best_tsp_sc = -999.0f;
    int best_tsp_def = 999;

    #pragma omp parallel
    {
        unsigned int seed = 777 + omp_get_thread_num() * 12345;
        int cur_order[COLS];
        for (int i = 0; i < COLS; i++) cur_order[i] = i;
        for (int i = COLS - 1; i > 0; i--) {
            int j = rand_r(&seed) % (i + 1);
            int t = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = t;
        }

        float cur_sc; int cur_def;
        eval_grid_order(cols, cur_order, &cur_sc, &cur_def);

        int local_best_order[COLS];
        memcpy(local_best_order, cur_order, sizeof(cur_order));
        float local_best_sc = cur_sc;
        int local_best_def = cur_def;

        int steps = 400000;
        float T_start = 0.5f, T_end = 0.001f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_order[COLS];
            memcpy(next_order, cur_order, sizeof(cur_order));

            int m = rand_r(&seed) % 3;
            int i = rand_r(&seed) % COLS;
            int j = rand_r(&seed) % COLS;

            if (m == 0) {
                int tmp = next_order[i]; next_order[i] = next_order[j]; next_order[j] = tmp;
            } else if (m == 1) {
                if (i > j) { int t = i; i = j; j = t; }
                while (i < j) {
                    int tmp = next_order[i]; next_order[i] = next_order[j]; next_order[j] = tmp;
                    i++; j--;
                }
            } else {
                int val = next_order[i];
                if (i < j) {
                    for (int k = i; k < j; k++) next_order[k] = next_order[k+1];
                    next_order[j] = val;
                } else if (i > j) {
                    for (int k = i; k > j; k--) next_order[k] = next_order[k-1];
                    next_order[j] = val;
                }
            }

            float next_sc; int next_def;
            eval_grid_order(cols, next_order, &next_sc, &next_def);

            float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);
            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(cur_order, next_order, sizeof(cur_order));
                cur_sc = next_sc;
                cur_def = next_def;

                if (cur_def < local_best_def || (cur_def == local_best_def && cur_sc > local_best_sc)) {
                    local_best_def = cur_def;
                    local_best_sc = cur_sc;
                    memcpy(local_best_order, cur_order, sizeof(cur_order));
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_def < best_tsp_def || (local_best_def == best_tsp_def && local_best_sc > best_tsp_sc)) {
                best_tsp_def = local_best_def;
                best_tsp_sc = local_best_sc;
                memcpy(best_order, local_best_order, sizeof(best_order));
                printf("[Thread %d] New TSP Optimum: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
                       omp_get_thread_num(), best_tsp_sc, best_tsp_def, (468 - best_tsp_def)/468.0f * 100.0f);
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL INJECTED Q7 RESULTS ON PK10:\n");
    printf("Quadgram Score: %.4f | Defects: %d / 468 (%.1f%% valid)\n",
           best_tsp_sc, best_tsp_def, (468 - best_tsp_def)/468.0f * 100.0f);
    printf("Baseline Record: Score = -6.9436 | Defects = 186 / 468 (60.3%% valid)\n");
    if (best_tsp_def < 186) {
        printf("RESULT: Injected Q7 BREAKS THE PK10 RECORD!\n");
    } else {
        printf("RESULT: Injected Q7 trails baseline record by %d defects.\n", best_tsp_def - 186);
    }

    // Print resulting rows
    printf("\nPlaintext Sample (First 3 Rows):\n");
    for (int r = 0; r < 3; r++) {
        printf("Row %d: ", r);
        for (int c = 0; c < COLS; c++) putchar(cols[best_order[c]][r]);
        putchar('\n');
    }

    return 0;
}
