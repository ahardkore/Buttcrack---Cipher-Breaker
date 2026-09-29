#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H 8

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

static inline float score_quads(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

void decode_amsco(const int *z, int start_pat, const int *order, int *pt) {
    int cell_len[H][W];
    int col_tot[W];
    memset(col_tot, 0, sizeof(col_tot));

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            int l = (start_pat == 1) ? ((r + c) % 2 + 1) : ((r + c + 1) % 2 + 1);
            cell_len[r][c] = l;
            col_tot[c] += l;
        }
    }

    int col_chars[W][32];
    int z_idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = order[c_idx];
        for (int i = 0; i < col_tot[col]; i++) {
            col_chars[col][i] = z[z_idx++];
        }
    }

    int col_read_ptr[W];
    memset(col_read_ptr, 0, sizeof(col_read_ptr));
    int pt_idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            int l = cell_len[r][c];
            for (int k = 0; k < l; k++) {
                pt[pt_idx++] = col_chars[c][col_read_ptr[c]++];
            }
        }
    }
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

    WordOrder *words = malloc(25000 * sizeof(WordOrder));
    int n_words = load_words("words_12.txt", words, 25000);
    printf("Loaded %d dictionary words of length 12.\n", n_words);

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

    printf("Testing AMSCO Width 12 across top 50 clock candidates...\n\n");

    float global_best_sc = -999.0f;
    char global_best_word[16];
    int global_best_cand = -1, global_best_pat = 1;
    char global_best_pt[N+1];

    double t0 = omp_get_wtime();

    for (int t = 0; t < 50; t++) {
        ClockCand *c = &cands[t];
        int z[N];
        decrypt_to_z(c->mode, c->q4, c->q7, z);

        #pragma omp parallel
        {
            float local_best = -999.0f;
            char local_w[16] = "";
            int local_pat = 1;
            char local_pt[N+1];

            #pragma omp for schedule(dynamic, 100)
            for (int w_idx = 0; w_idx < n_words; w_idx++) {
                for (int pat = 1; pat <= 2; pat++) {
                    int pt[N];
                    decode_amsco(z, pat, words[w_idx].order, pt);
                    float sc = score_quads(pt);

                    if (sc > local_best) {
                        local_best = sc;
                        strcpy(local_w, words[w_idx].word);
                        local_pat = pat;
                        for (int k = 0; k < N; k++) local_pt[k] = pt[k] + 'A';
                        local_pt[N] = 0;
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best > global_best_sc) {
                    global_best_sc = local_best;
                    strcpy(global_best_word, local_w);
                    global_best_cand = t;
                    global_best_pat = local_pat;
                    strcpy(global_best_pt, local_pt);

                    printf(">>> NEW BEST: %.4f | Cand #%d (Mode %d) | Pat %d | Word: %s <<<\n",
                           local_best, t, c->mode, local_pat, local_w);
                    printf("  PT: %.100s...\n\n", local_pt);
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("AMSCO Width 12 sweep completed in %.2f seconds.\n", elapsed);
    printf("Global Best Score: %.4f | Word: %s (Cand #%d, Pat %d)\n",
           global_best_sc, global_best_word, global_best_cand, global_best_pat);

    return 0;
}
