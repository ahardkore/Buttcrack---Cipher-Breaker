#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H (N / W)

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int k_to_std[26];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) return;
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
    for (int i = 0; i < 26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }
}

void single_col_decode(const int *in, int len, int width, const int *order, int *out) {
    int h = len / width;
    int grid[20][20];
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            grid[r][col] = in[k++];
        }
    }
    int idx = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < width; c++) {
            out[idx++] = grid[r][c];
        }
    }
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

void word_to_order(const char *w, int len, int *order) {
    typedef struct { char ch; int orig; } Pair;
    Pair p[32];
    for (int i = 0; i < len; i++) { p[i].ch = w[i]; p[i].orig = i; }
    for (int i = 0; i < len - 1; i++) {
        for (int j = i + 1; j < len; j++) {
            if (p[j].ch < p[i].ch || (p[j].ch == p[i].ch && p[j].orig < p[i].orig)) {
                Pair tmp = p[i]; p[i] = p[j]; p[j] = tmp;
            }
        }
    }
    for (int i = 0; i < len; i++) order[i] = p[i].orig;
}

typedef struct {
    char word[16];
    int order[12];
} Word12;

int main() {
    init_tables();
    load_quadgrams();

    FILE *f = fopen("words_12.txt", "r");
    if (!f) return 1;

    Word12 *words = malloc(25000 * sizeof(Word12));
    int n_words = 0;
    char line[64];
    while (fgets(line, sizeof(line), f)) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 12) {
            strcpy(words[n_words].word, w);
            word_to_order(w, 12, words[n_words].order);
            n_words++;
        }
    }
    fclose(f);

    const char *thematic_patterns[] = {
        "SMITH", "WORK", "CRAFT", "FORG", "METAL", "GOLD", "SILVER", "NEEDLE",
        "HAMMER", "ANVIL", "IRON", "STEEL", "BRASS", "COPPER", "TEMPER",
        "QUENCH", "ANNEAL", "WIRE", "DRAW", "BLOW", "FIRE", "COAL", "HEARTH",
        "FURNACE", "CRUCIBLE", "PORTAL", "TEMPLE", "CHURCH", "MONK", "PRIEST",
        "MASTER", "MAKING", "STUDY", "TENYEAR", "YEARS", "MINUTE", "SECOND"
    };
    int n_patterns = sizeof(thematic_patterns) / sizeof(thematic_patterns[0]);

    Word12 *thematic = malloc(5000 * sizeof(Word12));
    int n_them = 0;
    for (int i = 0; i < n_words; i++) {
        int is_them = 0;
        for (int p = 0; p < n_patterns; p++) {
            if (strstr(words[i].word, thematic_patterns[p])) {
                is_them = 1;
                break;
            }
        }
        if (is_them) thematic[n_them++] = words[i];
    }

    long long total_pairs = (long long)n_them * n_them;
    printf("Evaluating Pipeline A: Double Columnar (12, 12) + Period 7 Ascent on %lld pairs...\n", total_pairs);

    float global_best_sc = -999.0f;
    char best_w1[16] = "", best_w2[16] = "";
    int best_shifts[7];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_w1[16] = "", local_w2[16] = "";
        int local_shifts[7];
        char local_pt[N + 1] = "";

        // Precompute coordinate mapping for double columnar
        int map[N];
        int x_indices[N], inter[N];
        for (int i = 0; i < N; i++) x_indices[i] = i;

        #pragma omp for schedule(dynamic, 64)
        for (long long idx = 0; idx < total_pairs; idx++) {
            int i1 = idx / n_them;
            int i2 = idx % n_them;

            // Undo T2 then T1 on indices
            single_col_decode(x_indices, N, 12, thematic[i2].order, inter);
            single_col_decode(inter, N, 12, thematic[i1].order, map);

            // Coordinate ascent on Period 7
            int shifts[7] = {0};
            int X[N], pt[N];
            for (int i = 0; i < N; i++) {
                X[i] = (c_idx[i] - shifts[i % 7] + 26) % 26;
            }
            for (int p = 0; p < N; p++) {
                pt[p] = k_to_std[X[map[p]]];
            }
            float cur_sc = score_plain(pt);

            int improved = 1;
            int passes = 0;
            while (improved && passes < 4) {
                improved = 0;
                passes++;
                for (int j = 0; j < 7; j++) {
                    int old_sh = shifts[j];
                    int best_sh = old_sh;
                    float best_s = cur_sc;

                    for (int sh = 0; sh < 26; sh++) {
                        if (sh == old_sh) continue;
                        for (int o = j; o < N; o += 7) {
                            X[o] = (c_idx[o] - sh + 26) % 26;
                        }
                        for (int p = 0; p < N; p++) {
                            pt[p] = k_to_std[X[map[p]]];
                        }
                        float s = score_plain(pt);
                        if (s > best_s) {
                            best_s = s;
                            best_sh = sh;
                        }
                    }
                    shifts[j] = best_sh;
                    for (int o = j; o < N; o += 7) {
                        X[o] = (c_idx[o] - shifts[j] + 26) % 26;
                    }
                    if (best_sh != old_sh) {
                        cur_sc = best_s;
                        improved = 1;
                    }
                }
            }

            if (cur_sc > -5.2f) {
                #pragma omp critical
                {
                    printf("\n>>> CANDIDATE HIT! Score = %.4f | Words: (%s, %s)\n",
                           cur_sc, thematic[i1].word, thematic[i2].word);
                    printf("  Shifts: ");
                    for (int j = 0; j < 7; j++) printf("%c", KRYPTOS[shifts[j]]);
                    printf("\n  Plaintext: %.80s...\n", pt);
                    fflush(stdout);
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                strcpy(local_w1, thematic[i1].word);
                strcpy(local_w2, thematic[i2].word);
                for (int j = 0; j < 7; j++) local_shifts[j] = shifts[j];
                for (int p = 0; p < N; p++) local_pt[p] = 'A' + pt[p];
                local_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(best_w1, local_w1);
                strcpy(best_w2, local_w2);
                for (int j = 0; j < 7; j++) best_shifts[j] = local_shifts[j];
                strcpy(best_pt, local_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f s (%.1f pairs/sec)\n", elapsed, total_pairs / elapsed);
    printf("Global Best Score: %.4f | Words: (%s, %s)\n", global_best_sc, best_w1, best_w2);
    printf("Shifts (KRYPTOS): ");
    for (int j = 0; j < 7; j++) printf("%c", KRYPTOS[best_shifts[j]]);
    printf("\nPlaintext: %s\n", best_pt);

    return 0;
}
