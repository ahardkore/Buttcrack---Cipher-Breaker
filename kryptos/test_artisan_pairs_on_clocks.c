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
static float quad_table[26][26][26][26];

void load_models() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) exit(1);
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

void decrypt_to_z(int mode, const int *q4, const int *q7, int *z) {
    for (int i = 0; i < N; i++) {
        int sh = (q4[i % 4] + q7[i % 7]) % 26;
        if (mode == 0) z[i] = (ct_std[i] - sh + 26) % 26;
        else if (mode == 1) z[i] = (sh - ct_std[i] + 26) % 26;
        else if (mode == 2) {
            int kr_p = (ct_kr[i] - sh + 26) % 26;
            z[i] = kr_to_std[kr_p];
        } else {
            int kr_p = (sh - ct_kr[i] + 26) % 26;
            z[i] = kr_to_std[kr_p];
        }
    }
}

static inline void col_decrypt(const int *in, const int *order, int *out) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < H; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < H; r++)
        for (int c = 0; c < W; c++) out[idx++] = grid[r][c];
}

static inline float score_quads(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

typedef struct {
    char word[16];
    int order[12];
} WordOrder;

int load_words(const char *fn, WordOrder *out, int max_w) {
    FILE *f = fopen(fn, "r");
    if (!f) return 0;
    char line[128];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_w) {
        char w[32];
        if (sscanf(line, "%s", w) != 1) continue;
        if (strlen(w) != 12) continue;
        int ok = 1;
        for (int i = 0; i < 12; i++) {
            if (w[i] < 'A' || w[i] > 'Z') { ok = 0; break; }
        }
        if (!ok) continue;

        WordOrder *wo = &out[count];
        strcpy(wo->word, w);
        for (int i = 0; i < 12; i++) wo->order[i] = i;
        for (int i = 0; i < 11; i++) {
            for (int j = i + 1; j < 12; j++) {
                if (w[wo->order[i]] > w[wo->order[j]]) {
                    int t = wo->order[i]; wo->order[i] = wo->order[j]; wo->order[j] = t;
                }
            }
        }
        count++;
    }
    fclose(f);
    return count;
}

typedef struct {
    int mode;
    double ll;
    int q4[4];
    int q7[7];
} ClockCand;

int main() {
    load_models();
    printf("Models loaded.\n");

    WordOrder words[1000];
    int n_words = load_words("theophilus_english_12.txt", words, 500);
    n_words += load_words("craft_words_12.txt", words + n_words, 500);
    printf("Loaded %d unique 12-letter artisan/Theophilus words.\n", n_words);

    FILE *f = fopen("top_clocks.csv", "r");
    if (!f) return 1;
    char line[256];
    fgets(line, sizeof(line), f);

    ClockCand cands[2000];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < 2000) {
        ClockCand *c = &cands[count];
        char dummy1[32], dummy2[32], dummy3[32], dummy4[32];
        if (sscanf(line, "%d,%lf,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s",
                   &c->mode, &c->ll,
                   &c->q4[0], &c->q4[1], &c->q4[2], &c->q4[3],
                   &c->q7[0], &c->q7[1], &c->q7[2], &c->q7[3], &c->q7[4], &c->q7[5], &c->q7[6],
                   dummy1, dummy2, dummy3, dummy4) >= 13) {
            count++;
        }
    }
    fclose(f);

    // Test top 20 clock candidates
    int test_indices[20];
    for (int i = 0; i < 20; i++) test_indices[i] = i;

    printf("Sweeping all %d x %d = %d artisan word pairs across top 20 clock candidates...\n\n",
           n_words, n_words, n_words * n_words);

    float global_best_sc = -999.0f;
    char global_w1[16], global_w2[16];
    int global_cand_idx = -1;
    int global_best_pt[N];

    double t0 = omp_get_wtime();

    for (int t = 0; t < 20; t++) {
        int idx = test_indices[t];
        ClockCand *c = &cands[idx];
        int z[N];
        decrypt_to_z(c->mode, c->q4, c->q7, z);

        #pragma omp parallel
        {
            float local_best = -999.0f;
            char local_w1[16], local_w2[16];
            int local_pt[N];

            #pragma omp for schedule(dynamic)
            for (int i = 0; i < n_words; i++) {
                int mid[N], pt[N];
                col_decrypt(z, words[i].order, mid);

                for (int j = 0; j < n_words; j++) {
                    col_decrypt(mid, words[j].order, pt);
                    float sc = score_quads(pt);

                    if (sc > local_best) {
                        local_best = sc;
                        strcpy(local_w1, words[i].word);
                        strcpy(local_w2, words[j].word);
                        memcpy(local_pt, pt, sizeof(pt));
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best > global_best_sc) {
                    global_best_sc = local_best;
                    strcpy(global_w1, local_w1);
                    strcpy(global_w2, local_w2);
                    global_cand_idx = idx;
                    memcpy(global_best_pt, local_pt, sizeof(local_pt));

                    char pt_str[N+1];
                    for (int k = 0; k < N; k++) pt_str[k] = local_pt[k] + 'A';
                    pt_str[N] = 0;

                    printf(">>> NEW BEST: %.4f | Mode %d | Cand #%d | Pair: %s o %s <<<\n",
                           local_best, c->mode, idx, local_w1, local_w2);
                    printf("  PT: %.100s...\n\n", pt_str);
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Sweep completed in %.2f seconds.\n", elapsed);
    printf("Global Best Score: %.4f\n", global_best_sc);
    if (global_best_sc > -999.0f) {
        char final_pt[N+1];
        for (int k = 0; k < N; k++) final_pt[k] = global_best_pt[k] + 'A';
        final_pt[N] = 0;
        printf("Best Pair: %s o %s (Cand #%d)\n", global_w1, global_w2, global_cand_idx);
        printf("Plaintext:\n%s\n", final_pt);
    }

    return 0;
}
