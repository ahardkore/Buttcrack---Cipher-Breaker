#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int q4[4] = {16, 23, 22, 18};
static const int q7[7] = {10, 19, 17, 25, 16, 18, 10};

static int c_idx[N];
static int alpha_to_std[26];
static char X[N + 1];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) exit(1);
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;

    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        X[i] = 'A' + alpha_to_std[p];
    }
    X[N] = '\0';
}

void word_to_order(const char *w, int *order) {
    int idx[12];
    for (int i = 0; i < 12; i++) idx[i] = i;
    for (int i = 0; i < 12; i++) {
        for (int j = i + 1; j < 12; j++) {
            if (w[idx[i]] > w[idx[j]] || (w[idx[i]] == w[idx[j]] && idx[i] > idx[j])) {
                int tmp = idx[i]; idx[i] = idx[j]; idx[j] = tmp;
            }
        }
    }
    for (int rank = 0; rank < 12; rank++) {
        order[rank] = idx[rank];
    }
}

typedef struct {
    char word[16];
    int order[12];
} WordOrder;

static WordOrder words[25000];
static int n_words = 0;

void load_english_12() {
    FILE *f = fopen("words_12.txt", "r");
    if (!f) return;
    char buf[64];
    while (fgets(buf, sizeof(buf), f) && n_words < 25000) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 12) {
            char clean[16]; int clen = 0;
            for (int i = 0; buf[i]; i++) {
                if (isalpha(buf[i])) clean[clen++] = toupper(buf[i]);
            }
            clean[clen] = 0;
            if (clen == 12) {
                strcpy(words[n_words].word, clean);
                word_to_order(clean, words[n_words].order);
                n_words++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d 12-letter English words\n", n_words);
}

int main() {
    init_tables();
    load_quadgrams();
    load_english_12();

    long long total_pairs = (long long)n_words * n_words;
    printf("Evaluating all %lld pairs of English (W1, W2) on PK9 with fast row-pruning...\n", total_pairs);

    float global_best_sc = -999.0f;
    char best_w1[16] = "", best_w2[16] = "";
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_w1[16] = "", local_w2[16] = "";
        char local_pt[N + 1] = "";

        char G2[12][12];
        char Y[N];
        char G1[12][12];
        int pt[N];

        #pragma omp for schedule(dynamic, 16)
        for (int i = 0; i < n_words; i++) {
            const int *p1 = words[i].order;

            for (int j = 0; j < n_words; j++) {
                const int *p2 = words[j].order;

                // Invert pi2 to get Y
                for (int k = 0; k < 12; k++) {
                    int col = p2[k];
                    for (int r = 0; r < 12; r++) G2[r][col] = X[k * 12 + r];
                }

                int idx = 0;
                for (int r = 0; r < 12; r++) {
                    for (int c = 0; c < 12; c++) Y[idx++] = G2[r][c];
                }

                // Invert pi1 for first 3 rows (36 chars)
                for (int k = 0; k < 12; k++) {
                    int col = p1[k];
                    for (int r = 0; r < 3; r++) G1[r][col] = Y[k * 12 + r];
                }

                idx = 0;
                for (int r = 0; r < 3; r++) {
                    for (int c = 0; c < 12; c++) pt[idx++] = G1[r][c] - 'A';
                }

                // Fast early prefix score on first 33 quadgrams
                float prefix_sc = 0.0f;
                for (int k = 0; k < 33; k++) {
                    prefix_sc += quad[pt[k]][pt[k+1]][pt[k+2]][pt[k+3]];
                }
                if (prefix_sc < -235.0f) continue; // Early prune (random 33 quads is ~ -245)

                // Complete remaining 9 rows
                for (int k = 0; k < 12; k++) {
                    int col = p1[k];
                    for (int r = 3; r < 12; r++) G1[r][col] = Y[k * 12 + r];
                }

                for (int r = 3; r < 12; r++) {
                    for (int c = 0; c < 12; c++) pt[idx++] = G1[r][c] - 'A';
                }

                float sc = 0.0f;
                for (int k = 0; k < N - 3; k++) {
                    sc += quad[pt[k]][pt[k+1]][pt[k+2]][pt[k+3]];
                }
                sc /= (N - 3);

                if (sc > -5.5f) {
                    #pragma omp critical
                    {
                        printf("\n>>> CANDIDATE HIT! Score = %.4f | Words: (%s, %s)\n",
                               sc, words[i].word, words[j].word);
                        char full_pt[N + 1];
                        for (int k = 0; k < N; k++) full_pt[k] = 'A' + pt[k];
                        full_pt[N] = '\0';
                        printf("  PT: %s\n\n", full_pt);
                        fflush(stdout);
                    }
                }

                if (sc > local_best_sc) {
                    local_best_sc = sc;
                    strcpy(local_w1, words[i].word);
                    strcpy(local_w2, words[j].word);
                    for (int k = 0; k < N; k++) local_pt[k] = 'A' + pt[k];
                    local_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(best_w1, local_w1);
                strcpy(best_w2, local_w2);
                strcpy(best_pt, local_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted all %lld pairs in %.2f s (%.1f million pairs/sec)\n",
           total_pairs, elapsed, total_pairs / (elapsed * 1e6));
    printf("Global Best Score = %.4f | Words: (%s, %s)\n", global_best_sc, best_w1, best_w2);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}
