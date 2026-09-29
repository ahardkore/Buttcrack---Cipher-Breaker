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
    int shifts[32];
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

    int P = 28;
    printf("Evaluating %d words under Period %d...\n", num_words, P);

    Candidate *all_cands = malloc(num_words * sizeof(Candidate));

    #pragma omp parallel for schedule(dynamic, 50)
    for (int i = 0; i < num_words; i++) {
        int mapping[N];
        make_columnar_mapping(words[i].order, mapping);
        int shifts[32];
        char pt[N+1];
        float sc = optimize_shifts(P, mapping, shifts, pt);

        all_cands[i].sc = sc;
        strcpy(all_cands[i].word, words[i].word);
        for (int k = 0; k < 12; k++) all_cands[i].order[k] = words[i].order[k];
        for (int j = 0; j < P; j++) all_cands[i].shifts[j] = shifts[j];
        strcpy(all_cands[i].pt, pt);
    }

    qsort(all_cands, num_words, sizeof(Candidate), compare_cands);

    printf("\n=== Top 15 Candidates for Period 28 ===\n");
    for (int i = 0; i < 15; i++) {
        printf("\nRank %d: Score = %.4f | Word = %s\n", i + 1, all_cands[i].sc, all_cands[i].word);
        printf("Order: ");
        for (int k = 0; k < 12; k++) printf("%d ", all_cands[i].order[k]);
        printf("\nShifts (KRYPTOS): ");
        for (int j = 0; j < P; j++) printf("%c", KRYPTOS[all_cands[i].shifts[j]]);
        printf("\nPlaintext: %s\n", all_cands[i].pt);
    }

    free(all_cands);
    return 0;
}
