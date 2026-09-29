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

static inline float eval_double_col(const int *p1, const int *p2, char *out_plain) {
    char G2[12][12];
    for (int k = 0; k < 12; k++) {
        int col = p2[k];
        for (int r = 0; r < 12; r++) G2[r][col] = X[k * 12 + r];
    }

    char Y[N];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) Y[idx++] = G2[r][c];
    }

    char G1[12][12];
    for (int k = 0; k < 12; k++) {
        int col = p1[k];
        for (int r = 0; r < 12; r++) G1[r][col] = Y[k * 12 + r];
    }

    int pt[N];
    idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) pt[idx++] = G1[r][c] - 'A';
    }

    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    sc /= (N - 3);

    if (out_plain) {
        for (int i = 0; i < N; i++) out_plain[i] = 'A' + pt[i];
        out_plain[N] = '\0';
    }

    return sc;
}

typedef struct {
    char word[16];
    int order[12];
} WordOrder;

static WordOrder words[1000];
static int n_words = 0;

void load_theophilus_12() {
    FILE *f = fopen("theophilus_hendrie.txt", "r");
    if (!f) return;
    char buf[1024];
    while (fscanf(f, "%1023s", buf) == 1) {
        char clean[64]; int clen = 0;
        for (int i = 0; buf[i]; i++) {
            if (isalpha(buf[i])) clean[clen++] = toupper(buf[i]);
        }
        clean[clen] = 0;
        if (clen == 12) {
            // Check if unique
            int exists = 0;
            for (int i = 0; i < n_words; i++) {
                if (strcmp(words[i].word, clean) == 0) { exists = 1; break; }
            }
            if (!exists && n_words < 1000) {
                strcpy(words[n_words].word, clean);
                word_to_order(clean, words[n_words].order);
                n_words++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d unique 12-letter words from Theophilus\n", n_words);
}

int main() {
    init_tables();
    load_quadgrams();
    load_theophilus_12();

    long long total_pairs = (long long)n_words * n_words;
    printf("Evaluating all %lld pairs of (W1, W2) on PK9...\n", total_pairs);

    float global_best_sc = -999.0f;
    char best_w1[16] = "", best_w2[16] = "";
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_w1[16] = "", local_w2[16] = "";
        char local_pt[N + 1] = "";

        #pragma omp for schedule(dynamic, 16)
        for (int i = 0; i < n_words; i++) {
            for (int j = 0; j < n_words; j++) {
                char pt_buf[N + 1];
                float sc = eval_double_col(words[i].order, words[j].order, pt_buf);

                if (sc > -5.5f) {
                    #pragma omp critical
                    {
                        printf("\n>>> CANDIDATE HIT! Score = %.4f | Words: (%s, %s)\n",
                               sc, words[i].word, words[j].word);
                        printf("  PT: %s\n\n", pt_buf);
                        fflush(stdout);
                    }
                }

                if (sc > local_best_sc) {
                    local_best_sc = sc;
                    strcpy(local_w1, words[i].word);
                    strcpy(local_w2, words[j].word);
                    strcpy(local_pt, pt_buf);
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
    printf("\nFinished in %.2f s (%.1f thousand pairs/sec)\n", elapsed, total_pairs / (elapsed * 1000.0));
    printf("Global Best Score = %.4f | Words: (%s, %s)\n", global_best_sc, best_w1, best_w2);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}
