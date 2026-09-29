#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];
static float quad[26][26][26][26];

void load_models() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Missing english_quadgrams.txt\n"); exit(1); }
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26)
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        kr_to_std[i] = ALPH[i] - 'A';
        std_to_kr[ALPH[i] - 'A'] = i;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

// Word to permutation
void word_to_perm(const char *w, int *perm, int len) {
    for (int i = 0; i < len; i++) {
        int rank = 0;
        for (int j = 0; j < len; j++) {
            if (w[j] < w[i] || (w[j] == w[i] && j < i)) rank++;
        }
        perm[i] = rank;
    }
}

static const char *THEMATIC_7[] = {
    "NEEDLES", "DRAWPIN", "HAMMERS", "STRIKES", "ANVILSS", "FORGING", "SMITHSY",
    "BURNING", "GLOWING", "HEATING", "FURNACE", "BELLOWS", "CHISELS", "QUENCHY",
    "ANNEALS", "TEMPERS", "PIERCED", "PUNCHED", "STURGEO", "ORGANAR", "CYMBALS",
    "TEXTILE", "PATRONS", "BRODERI", "ARABICQ", "YTALIQU", "MORESQU",
    "KRYPTOS", "SHADING", "NUANCES", "ILLUSIO", "PASSAGE", "CHAMBER",
    "TEMPERA", "WHITESM", "PELLEGR", "SEVENTH", "ANVILST", "DRAWPLA",
    "IRONGLO", "COPPERP", "SILVERS", "GOLDENS", "ARCHIVE", "SECRETS"
};
static const int NUM_Q7 = sizeof(THEMATIC_7) / sizeof(THEMATIC_7[0]);

int main() {
    load_models();
    printf("Models loaded. Loading 12-letter words...\n");

    FILE *fw = fopen("words_12.txt", "r");
    if (!fw) { printf("Cannot open words_12.txt\n"); exit(1); }
    char (*words12)[16] = malloc(25000 * 16);
    int num_w12 = 0;
    char line[64];
    while (fgets(line, sizeof(line), fw)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (strlen(line) == 12) {
            for (int i = 0; i < 12; i++) {
                if (line[i] >= 'a' && line[i] <= 'z') line[i] -= 32;
            }
            strcpy(words12[num_w12++], line);
        }
    }
    fclose(fw);
    printf("Loaded %d 12-letter words. Precomputing permutations...\n", num_w12);

    int (*perms12)[12] = malloc(num_w12 * sizeof(int[12]));
    int (*inv_perms12)[12] = malloc(num_w12 * sizeof(int[12]));
    for (int i = 0; i < num_w12; i++) {
        word_to_perm(words12[i], perms12[i], 12);
        for (int c = 0; c < 12; c++) {
            inv_perms12[i][perms12[i][c]] = c;
        }
    }

    printf("Evaluating %d thematic Q7 keywords against %d W12 permutations (%ld total tests)...\n",
           NUM_Q7, num_w12, (long)NUM_Q7 * num_w12);

    float global_best_sc = -999.0f;
    char best_w7[16] = "";
    char best_w12[16] = "";
    char best_pt[N+1] = "";

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_w7[16] = "";
        char local_w12[16] = "";
        char local_pt[N+1] = "";

        #pragma omp for schedule(dynamic, 1)
        for (int q_idx = 0; q_idx < NUM_Q7; q_idx++) {
            const char *w7 = THEMATIC_7[q_idx];
            int q7_kr[7], q7_std[7];
            for (int j = 0; j < 7; j++) {
                q7_kr[j] = std_to_kr[w7[j] - 'A'];
                q7_std[j] = w7[j] - 'A';
            }

            for (int w_idx = 0; w_idx < num_w12; w_idx++) {
                const int *p = perms12[w_idx];

                // Test Model: P[r*12 + c] = decrypt(CT[p[c]*12 + r], K)
                // where K = q4[r % 4] + q7[(5*p[c] + r) % 7]
                // Kryptos Vigenere:
                // Precompute base letters Y[r][c] for q4=0
                int Y[H][W];
                for (int r = 0; r < H; r++) {
                    for (int c = 0; c < W; c++) {
                        int ct_val = ct_kr[p[c] * H + r];
                        int k7 = q7_kr[(5 * p[c] + r) % 7];
                        Y[r][c] = (ct_val - k7 + 26) % 26;
                    }
                }

                // Optimize q4[0], q4[1], q4[2], q4[3]
                int best_q4[4] = {0, 0, 0, 0};
                float total_sc = 0.0f;

                for (int m = 0; m < 4; m++) {
                    // rows m, m+4, m+8
                    float best_group_sc = -1e9f;
                    int best_v = 0;
                    for (int v = 0; v < 26; v++) {
                        float group_sc = 0.0f;
                        for (int k = 0; k < 3; k++) {
                            int r = m + 4 * k;
                            int row_letters[12];
                            for (int c = 0; c < 12; c++) {
                                int p_kr = (Y[r][c] - v + 26) % 26;
                                row_letters[c] = kr_to_std[p_kr];
                            }
                            for (int i = 0; i < 9; i++) {
                                group_sc += quad[row_letters[i]][row_letters[i+1]][row_letters[i+2]][row_letters[i+3]];
                            }
                        }
                        if (group_sc > best_group_sc) {
                            best_group_sc = group_sc;
                            best_v = v;
                        }
                    }
                    best_q4[m] = best_v;
                    total_sc += best_group_sc;
                }

                float avg_sc = total_sc / (12 * 9);
                if (avg_sc > local_best_sc) {
                    local_best_sc = avg_sc;
                    strcpy(local_w7, w7);
                    strcpy(local_w12, words12[w_idx]);

                    // Reconstruct PT
                    int idx = 0;
                    for (int r = 0; r < H; r++) {
                        int v = best_q4[r % 4];
                        for (int c = 0; c < W; c++) {
                            int p_kr = (Y[r][c] - v + 26) % 26;
                            local_pt[idx++] = kr_to_std[p_kr] + 'A';
                        }
                    }
                    local_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(best_w7, local_w7);
                strcpy(best_w12, local_w12);
                strcpy(best_pt, local_pt);
                printf("NEW BEST: %.4f | Q7: %s | W12: %s\n", global_best_sc, best_w7, best_w12);
                printf("PT: %.100s\n\n", best_pt);
            }
        }
    }

    printf("Search complete! Global best score: %.4f\n", global_best_sc);
    printf("Best Q7: %s | Best W12: %s\n", best_w7, best_w12);
    printf("Full Plaintext:\n%s\n", best_pt);

    return 0;
}
