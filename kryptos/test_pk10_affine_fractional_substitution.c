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
static const char *STANDARD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int base_q7[7] = {0, 9, 5, 17, 10, 2, 24};
static const int base_q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
static const int base_q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

static const int base_order[COLS] = {
    29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16,
    20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9,
    41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
};

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];

static void load_quads(void) {
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

static inline void eval_mapped_grid(const char cols[COLS][ROWS], const char map[26], float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < ROWS; r++) {
        for (int c = 0; c <= COLS - 4; c++) {
            int a = map[cols[base_order[c]][r] - 'A'] - 'A';
            int b = map[cols[base_order[c+1]][r] - 'A'] - 'A';
            int c_char = map[cols[base_order[c+2]][r] - 'A'] - 'A';
            int d = map[cols[base_order[c+3]][r] - 'A'] - 'A';
            sc += qtable[a][b][c_char][d];
            if (!valid_q[a][b][c_char][d]) def++;
        }
    }
    *out_sc = sc / 468.0f;
    *out_def = def;
}

int main(void) {
    load_quads();

    // 1. Precompute baseline Z and grid
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (base_q7[i%7] + base_q8[i%8] + base_q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }
    char cols[COLS][ROWS];
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            cols[c][r] = Z[c * ROWS + r];
        }
    }

    char identity_map[26];
    for (int i = 0; i < 26; i++) identity_map[i] = 'A' + i;

    float base_sc; int base_def;
    eval_mapped_grid(cols, identity_map, &base_sc, &base_def);
    printf("Initial Baseline Record: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
           base_sc, base_def, (468 - base_def)/468.0f * 100.0f);

    // Test 1: All 312 Affine Mappings: c -> (a*c + b) % 26
    printf("\n=== Test 1: Evaluating all 312 Affine Mappings c -> (a*c + b) mod 26 ===\n");
    int coprime_a[] = {1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25};
    int n_a = sizeof(coprime_a) / sizeof(coprime_a[0]);

    float best_affine_sc = base_sc;
    int best_affine_def = base_def;
    int best_a = 1, best_b = 0;

    for (int ia = 0; ia < n_a; ia++) {
        int a = coprime_a[ia];
        for (int b = 0; b < 26; b++) {
            char map[26];
            for (int x = 0; x < 26; x++) {
                map[x] = 'A' + (a * x + b) % 26;
            }
            float sc; int def;
            eval_mapped_grid(cols, map, &sc, &def);
            if (def < best_affine_def || (def == best_affine_def && sc > best_affine_sc)) {
                best_affine_def = def;
                best_affine_sc = sc;
                best_a = a;
                best_b = b;
                printf("  New Best Affine (a=%2d, b=%2d): Score = %.4f | Defects = %d\n",
                       a, b, best_affine_sc, best_affine_def);
            }
        }
    }
    printf("Best Affine Result: a=%d, b=%d | Score = %.4f | Defects = %d / 468\n",
           best_a, best_b, best_affine_sc, best_affine_def);

    // Test 2: Standard Alphabet Interpretation vs Kryptos Alphabet Interpretation
    printf("\n=== Test 2: Standard Alphabet Indexing Interpretation ===\n");
    char Z_std[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(STANDARD, PK10_CT[i]) - STANDARD;
        int shift = (base_q7[i%7] + base_q8[i%8] + base_q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z_std[i] = STANDARD[pt_idx];
    }
    char cols_std[COLS][ROWS];
    for (int c = 0; c < COLS; c++) {
        for (int r = 0; r < ROWS; r++) {
            cols_std[c][r] = Z_std[c * ROWS + r];
        }
    }
    float std_sc; int std_def;
    eval_mapped_grid(cols_std, identity_map, &std_sc, &std_def);
    printf("Standard Alphabet Decryption: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
           std_sc, std_def, (468 - std_def)/468.0f * 100.0f);

    // Test 3: Kryptos-to-Standard Substitution Map: c -> STANDARD[KRYPTOS.index(c)]
    printf("\n=== Test 3: Kryptos-to-Standard Direct Substitution Mapping ===\n");
    char k2std_map[26];
    for (int i = 0; i < 26; i++) {
        char ch = 'A' + i;
        int kr_idx = strchr(KRYPTOS, ch) - KRYPTOS;
        k2std_map[i] = STANDARD[kr_idx];
    }
    float k2std_sc; int k2std_def;
    eval_mapped_grid(cols, k2std_map, &k2std_sc, &k2std_def);
    printf("Kryptos-to-Standard Map: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
           k2std_sc, k2std_def, (468 - k2std_def)/468.0f * 100.0f);

    // Test 4: General Monoalphabetic Substitution Annealing on the 26 Letters
    printf("\n=== Test 4: Monoalphabetic Substitution Simulated Annealing (26! space) ===\n");
    char best_mono_map[26];
    memcpy(best_mono_map, identity_map, sizeof(identity_map));
    float best_mono_sc = base_sc;
    int best_mono_def = base_def;

    #pragma omp parallel
    {
        unsigned int seed = 8888 + omp_get_thread_num() * 1777;
        char cur_map[26];
        memcpy(cur_map, identity_map, sizeof(identity_map));
        float cur_sc = base_sc;
        int cur_def = base_def;

        char local_best_map[26];
        memcpy(local_best_map, identity_map, sizeof(identity_map));
        float local_best_sc = base_sc;
        int local_best_def = base_def;

        int steps = 250000;
        float T_start = 0.5f, T_end = 0.001f;

        for (int s = 0; s < steps; s++) {
            float frac = (float)s / steps;
            float T = T_start * powf(T_end / T_start, frac);

            char next_map[26];
            memcpy(next_map, cur_map, sizeof(cur_map));

            // Swap two letters in substitution alphabet
            int i = rand_r(&seed) % 26;
            int j = rand_r(&seed) % 26;
            char tmp = next_map[i]; next_map[i] = next_map[j]; next_map[j] = tmp;

            float next_sc; int next_def;
            eval_mapped_grid(cols, next_map, &next_sc, &next_def);

            float d_fit = (cur_def - next_def) * 1.5f + (next_sc - cur_sc);
            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(cur_map, next_map, sizeof(cur_map));
                cur_sc = next_sc;
                cur_def = next_def;

                if (cur_def < local_best_def || (cur_def == local_best_def && cur_sc > local_best_sc)) {
                    local_best_def = cur_def;
                    local_best_sc = cur_sc;
                    memcpy(local_best_map, cur_map, sizeof(cur_map));
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_def < best_mono_def || (local_best_def == best_mono_def && local_best_sc > best_mono_sc)) {
                best_mono_def = local_best_def;
                best_mono_sc = local_best_sc;
                memcpy(best_mono_map, local_best_map, sizeof(best_mono_map));
                printf("[Thread %d] NEW BEST SUBSTITUTION MAP: Score = %.4f | Defects = %d / 468\n",
                       omp_get_thread_num(), best_mono_sc, best_mono_def);
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL FRACTIONAL / AFFINE SUBSTITUTION AUDIT RESULT:\n");
    printf("Best Score: %.4f | Best Defects: %d / 468 (%.1f%% valid)\n",
           best_mono_sc, best_mono_def, (468 - best_mono_def)/468.0f * 100.0f);
    printf("Identity Baseline: Score = %.4f | Defects = %d / 468 (%.1f%% valid)\n",
           base_sc, base_def, (468 - base_def)/468.0f * 100.0f);

    if (best_mono_def < base_def) {
        printf("RESULT: Secondary substitution improved plaintext!\n");
        printf("Map: ");
        for (int i = 0; i < 26; i++) printf("%c->%c ", 'A'+i, best_mono_map[i]);
        printf("\n");
    } else {
        printf("RESULT: IDENTITY MAP IS STRICTLY OPTIMAL. No secondary affine or monoalphabetic layer exists.\n");
    }

    return 0;
}
