#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
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
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

typedef struct {
    char str[8];
    int kr[4];
    int std[4];
} Word4;

typedef struct {
    char str[10];
    int kr[7];
    int std[7];
} Word7;

static Word4 *w4 = NULL; static int n4 = 0;
static Word7 *w7 = NULL; static int n7 = 0;

void load_words() {
    FILE *f = fopen("all_words.txt", "r");
    if (!f) { printf("Cannot open all_words.txt\n"); exit(1); }

    int cap4 = 10000, cap7 = 40000;
    w4 = malloc(cap4 * sizeof(Word4));
    w7 = malloc(cap7 * sizeof(Word7));

    char buf[128];
    while (fscanf(f, "%127s", buf) == 1) {
        int l = strlen(buf);
        int valid = 1;
        for (int i = 0; i < l; i++) {
            if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] -= 32;
            if (buf[i] < 'A' || buf[i] > 'Z') { valid = 0; break; }
        }
        if (!valid) continue;

        if (l == 4) {
            strcpy(w4[n4].str, buf);
            for (int i = 0; i < 4; i++) {
                w4[n4].std[i] = buf[i] - 'A';
                w4[n4].kr[i] = hpos[(unsigned char)buf[i]];
            }
            n4++;
        } else if (l == 7) {
            strcpy(w7[n7].str, buf);
            for (int i = 0; i < 7; i++) {
                w7[n7].std[i] = buf[i] - 'A';
                w7[n7].kr[i] = hpos[(unsigned char)buf[i]];
            }
            n7++;
        }
    }
    fclose(f);
    printf("Loaded words: W4 = %d, W7 = %d (Total pairs = %ld)\n", n4, n7, (long)n4 * n7);
}

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

typedef struct {
    float score;
    char w4_str[8];
    char w7_str[10];
    char pt[N + 1];
} Candidate;

int main() {
    load_quads();
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)UNDONE[i]];
        ct_std[i] = UNDONE[i] - 'A';
    }
    load_words();

    for (int mode = 0; mode < 2; mode++) {
        printf("====================================================\n");
        printf("Testing Mode: %s on PK9 (undone)\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Alphabet");
        printf("====================================================\n");

        double t0 = omp_get_wtime();

        #define TOP_N 10
        Candidate top_cands[TOP_N];
        for (int i = 0; i < TOP_N; i++) top_cands[i].score = -999.0f;

        #pragma omp parallel
        {
            Candidate loc_cands[TOP_N];
            for (int i = 0; i < TOP_N; i++) loc_cands[i].score = -999.0f;

            #pragma omp for schedule(dynamic, 64)
            for (int i4 = 0; i4 < n4; i4++) {
                const int *q4 = (mode == 0) ? w4[i4].kr : w4[i4].std;

                // Pre-subtract q4 from ct
                int rem_kr[N], rem_std[N];
                for (int t = 0; t < N; t++) {
                    if (mode == 0) {
                        rem_kr[t] = (ct_kr[t] - q4[t % 4] + 26) % 26;
                    } else {
                        rem_std[t] = (ct_std[t] - q4[t % 4] + 26) % 26;
                    }
                }

                for (int i7 = 0; i7 < n7; i7++) {
                    const int *q7 = (mode == 0) ? w7[i7].kr : w7[i7].std;

                    int pt[N];
                    for (int t = 0; t < N; t++) {
                        if (mode == 0) {
                            int p_kr = (rem_kr[t] - q7[t % 7] + 26) % 26;
                            pt[t] = k2std[p_kr];
                        } else {
                            pt[t] = (rem_std[t] - q7[t % 7] + 26) % 26;
                        }
                    }

                    // Quick heuristic check on first 40 chars to speed up by 4x
                    float s_head = 0.0f;
                    for (int i = 0; i < 37; i++) {
                        s_head += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                    }
                    if (s_head < 37 * -6.8f) continue;

                    float sc = score_pt(pt);

                    if (sc > loc_cands[TOP_N - 1].score) {
                        for (int k = 0; k < TOP_N; k++) {
                            if (sc > loc_cands[k].score) {
                                for (int j = TOP_N - 1; j > k; j--) loc_cands[j] = loc_cands[j - 1];
                                loc_cands[k].score = sc;
                                strcpy(loc_cands[k].w4_str, w4[i4].str);
                                strcpy(loc_cands[k].w7_str, w7[i7].str);
                                for (int t = 0; t < N; t++) loc_cands[k].pt[t] = 'A' + pt[t];
                                loc_cands[k].pt[N] = '\0';
                                break;
                            }
                        }
                    }
                }
            }

            #pragma omp critical
            {
                for (int k = 0; k < TOP_N; k++) {
                    float s = loc_cands[k].score;
                    if (s > top_cands[TOP_N - 1].score) {
                        for (int j = 0; j < TOP_N; j++) {
                            if (s > top_cands[j].score) {
                                for (int m = TOP_N - 1; m > j; m--) top_cands[m] = top_cands[m - 1];
                                top_cands[j] = loc_cands[k];
                                break;
                            }
                        }
                    }
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Search completed in %.3f s!\n\n", elapsed);

        printf("=== TOP 5 (W4, W7) CANDIDATES (Mode %d) ===\n", mode);
        for (int k = 0; k < 5; k++) {
            Candidate *c = &top_cands[k];
            printf("Rank %d: Score = %.4f | W4: %s, W7: %s\n", k + 1, c->score, c->w4_str, c->w7_str);
            printf("  PT: %.75s...\n\n", c->pt);
        }
    }

    free(w4); free(w7);
    return 0;
}
