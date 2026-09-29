#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W 12
#define H 12

static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Failed to open english_quads.tsv\n"); exit(1); }
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
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = hpos[(unsigned char)PK9_CT[i]];
    }
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

// Single Columnar mapping (12x12)
void make_columnar_mapping(const int *order, int *mapping) {
    int idx = 0;
    for (int i = 0; i < W; i++) {
        int c = order[i];
        for (int r = 0; r < H; r++) {
            mapping[idx++] = c + r * W;
        }
    }
}

// Nihilist Transposition mapping (12x12)
// grid is filled by rows, permuted cols and rows by order, read by cols (or rows)
void make_nihilist_mapping(const int *order, int takeoff_rows, int *mapping) {
    // col_order: column p in output was original column order[p]
    // row_order: row q in output was original row order[q]
    int idx = 0;
    if (takeoff_rows) {
        for (int r = 0; r < H; r++) {
            int orig_r = order[r];
            for (int c = 0; c < W; c++) {
                int orig_c = order[c];
                mapping[idx++] = orig_r * W + orig_c;
            }
        }
    } else {
        // takeoff by columns
        for (int c = 0; c < W; c++) {
            int orig_c = order[c];
            for (int r = 0; r < H; r++) {
                int orig_r = order[r];
                mapping[idx++] = orig_r * W + orig_c;
            }
        }
    }
}

// Optimize shifts for a given mapping and period P
float optimize_shifts(int P, const int *mapping, int *best_shifts, char *best_pt_out) {
    int shifts[32];
    for (int j = 0; j < P; j++) shifts[j] = 0;

    int pt[N];
    for (int o = 0; o < N; o++) {
        int dec_k = (c_idx[o] - shifts[o % P] + 26) % 26;
        pt[mapping[o]] = k_to_std[dec_k];
    }
    float cur_sc = score_plain(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 8) {
        improved = 0;
        passes++;
        for (int j = 0; j < P; j++) {
            int old_sh = shifts[j];
            int best_sh = old_sh;
            float best_s = cur_sc;

            for (int sh = 0; sh < 26; sh++) {
                if (sh == old_sh) continue;
                for (int o = j; o < N; o += P) {
                    int dec_k = (c_idx[o] - sh + 26) % 26;
                    pt[mapping[o]] = k_to_std[dec_k];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_sh = sh;
                }
            }
            if (best_sh != old_sh) {
                shifts[j] = best_sh;
                cur_sc = best_s;
                improved = 1;
            }
            for (int o = j; o < N; o += P) {
                int dec_k = (c_idx[o] - shifts[j] + 26) % 26;
                pt[mapping[o]] = k_to_std[dec_k];
            }
        }
    }

    if (best_shifts) {
        for (int j = 0; j < P; j++) best_shifts[j] = shifts[j];
    }
    if (best_pt_out) {
        for (int i = 0; i < N; i++) best_pt_out[i] = 'A' + pt[i];
        best_pt_out[N] = '\0';
    }
    return cur_sc;
}

typedef struct {
    char word[16];
    int order[W];
} WordOrder;

static WordOrder words[30000];
static int num_words = 0;

void load_words() {
    FILE *f = fopen("words_12.txt", "r");
    if (!f) { printf("Cannot open words_12.txt\n"); exit(1); }
    char line[64];
    while (fgets(line, sizeof(line), f) && num_words < 25000) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 12) {
            strcpy(words[num_words].word, w);
            // compute argsort order
            typedef struct { char ch; int orig_idx; } Pair;
            Pair p[12];
            for (int i = 0; i < 12; i++) { p[i].ch = w[i]; p[i].orig_idx = i; }
            for (int i = 0; i < 11; i++) {
                for (int j = i + 1; j < 12; j++) {
                    if (p[j].ch < p[i].ch || (p[j].ch == p[i].ch && p[j].orig_idx < p[i].orig_idx)) {
                        Pair tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }
                }
            }
            for (int i = 0; i < 12; i++) words[num_words].order[i] = p[i].orig_idx;
            num_words++;
        }
    }
    fclose(f);
    printf("Loaded %d 12-letter words.\n", num_words);
}

void test_mode(const char *name, int mode, int P) {
    printf("\n=== Testing %s with Period %d on %d words ===\n", name, P, num_words);
    float global_best = -999.0f;
    char best_word[16] = "";
    int best_order[12];
    int best_shifts[32];
    char best_pt[N+1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_best_word[16] = "";
        int local_best_order[12];
        int local_best_shifts[32];
        char local_best_pt[N+1];

        #pragma omp for schedule(dynamic, 50)
        for (int i = 0; i < num_words; i++) {
            int mapping[N];
            if (mode == 0) {
                make_columnar_mapping(words[i].order, mapping);
            } else if (mode == 1) {
                make_nihilist_mapping(words[i].order, 0, mapping);
            } else {
                make_nihilist_mapping(words[i].order, 1, mapping);
            }

            int shifts[32];
            char pt[N+1];
            float sc = optimize_shifts(P, mapping, shifts, pt);

            if (sc > local_best) {
                local_best = sc;
                strcpy(local_best_word, words[i].word);
                for (int k = 0; k < 12; k++) local_best_order[k] = words[i].order[k];
                for (int j = 0; j < P; j++) local_best_shifts[j] = shifts[j];
                strcpy(local_best_pt, pt);
            }
        }

        #pragma omp critical
        {
            if (local_best > global_best) {
                global_best = local_best;
                strcpy(best_word, local_best_word);
                for (int k = 0; k < 12; k++) best_order[k] = local_best_order[k];
                for (int j = 0; j < P; j++) best_shifts[j] = local_best_shifts[j];
                strcpy(best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s (%.1f words/sec)\n", elapsed, num_words / elapsed);
    printf("Best score: %.4f (Word: %s)\n", global_best, best_word);
    printf("Order: ");
    for (int k = 0; k < 12; k++) printf("%d ", best_order[k]);
    printf("\nShifts (KRYPTOS): ");
    for (int j = 0; j < P; j++) printf("%c", KRYPTOS[best_shifts[j]]);
    printf("\nPlaintext: %s\n", best_pt);
}

int main() {
    load_quadgrams();
    init_tables();
    load_words();

    // 1. Single Columnar 12x12, Period 7
    test_mode("Single Columnar (12x12)", 0, 7);

    // 2. Nihilist Col Takeoff, Period 7
    test_mode("Nihilist Col Takeoff (12x12)", 1, 7);

    // 3. Nihilist Row Takeoff, Period 7
    test_mode("Nihilist Row Takeoff (12x12)", 2, 7);

    // 4. Single Columnar 12x12, Period 12
    test_mode("Single Columnar (12x12)", 0, 12);

    // 5. Single Columnar 12x12, Period 14
    test_mode("Single Columnar (12x12)", 0, 14);
    test_mode("Single Columnar (12x12)", 0, 28);

    return 0;
}
