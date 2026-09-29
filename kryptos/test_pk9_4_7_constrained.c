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

void make_columnar_mapping(const int *order, int *mapping) {
    int idx = 0;
    for (int i = 0; i < W; i++) {
        int c = order[i];
        for (int r = 0; r < H; r++) {
            mapping[idx++] = c + r * W;
        }
    }
}

// Optimize {4, 7} clock shifts via coordinate ascent
float optimize_4_7(const int *mapping, int *best_q4, int *best_q7, char *best_pt_out) {
    int q4[4] = {0, 0, 0, 0};
    int q7[7] = {0, 0, 0, 0, 0, 0, 0};

    int pt[N];
    for (int o = 0; o < N; o++) {
        int sh = (q4[o % 4] + q7[o % 7]) % 26;
        int dec_k = (c_idx[o] - sh + 26) % 26;
        pt[mapping[o]] = k_to_std[dec_k];
    }
    float cur_sc = score_plain(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 6) {
        improved = 0;
        passes++;

        // Optimize q4[1..3] (gauge fix q4[0] = 0)
        for (int j = 1; j < 4; j++) {
            int old_val = q4[j];
            int best_v = old_val;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_val) continue;
                q4[j] = v;
                for (int o = j; o < N; o += 4) {
                    int sh = (q4[j] + q7[o % 7]) % 26;
                    int dec_k = (c_idx[o] - sh + 26) % 26;
                    pt[mapping[o]] = k_to_std[dec_k];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_v = v;
                }
            }
            q4[j] = best_v;
            for (int o = j; o < N; o += 4) {
                int sh = (q4[j] + q7[o % 7]) % 26;
                int dec_k = (c_idx[o] - sh + 26) % 26;
                pt[mapping[o]] = k_to_std[dec_k];
            }
            if (best_v != old_val) {
                cur_sc = best_s;
                improved = 1;
            }
        }

        // Optimize q7[0..6]
        for (int j = 0; j < 7; j++) {
            int old_val = q7[j];
            int best_v = old_val;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_val) continue;
                q7[j] = v;
                for (int o = j; o < N; o += 7) {
                    int sh = (q4[o % 4] + q7[j]) % 26;
                    int dec_k = (c_idx[o] - sh + 26) % 26;
                    pt[mapping[o]] = k_to_std[dec_k];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_v = v;
                }
            }
            q7[j] = best_v;
            for (int o = j; o < N; o += 7) {
                int sh = (q4[o % 4] + q7[j]) % 26;
                int dec_k = (c_idx[o] - sh + 26) % 26;
                pt[mapping[o]] = k_to_std[dec_k];
            }
            if (best_v != old_val) {
                cur_sc = best_s;
                improved = 1;
            }
        }
    }

    if (best_q4) for (int j = 0; j < 4; j++) best_q4[j] = q4[j];
    if (best_q7) for (int j = 0; j < 7; j++) best_q7[j] = q7[j];
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
}

typedef struct {
    float sc;
    char word[16];
    int order[12];
    int q4[4];
    int q7[7];
    char pt[N+1];
} Candidate;

int compare_cands(const void *a, const void *b) {
    float diff = ((Candidate*)b)->sc - ((Candidate*)a)->sc;
    return (diff > 0) - (diff < 0);
}

int main() {
    load_quadgrams();
    init_tables();
    load_words();

    printf("Evaluating %d words under Columnar 12x12 + {4, 7} Clocks...\n", num_words);

    Candidate *all_cands = malloc(num_words * sizeof(Candidate));
    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic, 100)
    for (int i = 0; i < num_words; i++) {
        int mapping[N];
        make_columnar_mapping(words[i].order, mapping);
        int q4[4], q7[7];
        char pt[N+1];
        float sc = optimize_4_7(mapping, q4, q7, pt);

        all_cands[i].sc = sc;
        strcpy(all_cands[i].word, words[i].word);
        for (int k = 0; k < 12; k++) all_cands[i].order[k] = words[i].order[k];
        for (int j = 0; j < 4; j++) all_cands[i].q4[j] = q4[j];
        for (int j = 0; j < 7; j++) all_cands[i].q7[j] = q7[j];
        strcpy(all_cands[i].pt, pt);
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s (%.1f words/sec)\n", elapsed, num_words / elapsed);

    qsort(all_cands, num_words, sizeof(Candidate), compare_cands);

    printf("\n=== Top 10 Candidates for Columnar 12x12 + {4, 7} Clocks ===\n");
    for (int i = 0; i < 10; i++) {
        printf("\nRank %d: Score = %.4f | Word = %s\n", i + 1, all_cands[i].sc, all_cands[i].word);
        printf("Order: ");
        for (int k = 0; k < 12; k++) printf("%d ", all_cands[i].order[k]);
        printf("\nq4 (KRYPTOS): ");
        for (int j = 0; j < 4; j++) printf("%c", KRYPTOS[all_cands[i].q4[j]]);
        printf(" | q7 (KRYPTOS): ");
        for (int j = 0; j < 7; j++) printf("%c", KRYPTOS[all_cands[i].q7[j]]);
        printf("\nPlaintext: %s\n", all_cands[i].pt);
    }

    free(all_cands);
    return 0;
}
