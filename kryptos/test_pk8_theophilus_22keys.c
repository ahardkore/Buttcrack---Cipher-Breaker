#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 153

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
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

void test_corpus(const char *filename) {
    FILE *f = fopen(filename, "r");
    if (!f) { printf("Cannot open %s\n", filename); return; }

    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *buf = malloc(sz + 1);
    fread(buf, 1, sz, f);
    buf[sz] = '\0';
    fclose(f);

    // Filter letters
    char *text = malloc(sz + 1);
    long n_letters = 0;
    for (long i = 0; i < sz; i++) {
        char c = buf[i];
        if (c >= 'a' && c <= 'z') text[n_letters++] = c - 32;
        else if (c >= 'A' && c <= 'Z') text[n_letters++] = c;
    }
    text[n_letters] = '\0';
    free(buf);

    printf("Loaded %s: %ld letters.\n", filename, n_letters);
    if (n_letters < 22) { free(text); return; }

    float best_sc = -999.0f;
    char best_sub[23] = "";
    char best_pt[N + 1] = "";
    int best_part = 0;
    int best_mode = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best = -999.0f;
        char loc_sub[23] = "";
        char loc_pt[N + 1] = "";
        int loc_part = 0;
        int loc_mode = 0;

        #pragma omp for schedule(dynamic, 1000)
        for (long i = 0; i <= n_letters - 22; i++) {
            char sub[23];
            memcpy(sub, text + i, 22);
            sub[22] = '\0';

            int sub_kr[22], sub_std[22];
            for (int k = 0; k < 22; k++) {
                sub_kr[k] = hpos[(unsigned char)sub[k]];
                sub_std[k] = sub[k] - 'A';
            }

            // Mode 0: KRYPTOS shifts, Mode 1: Standard shifts
            for (int mode = 0; mode < 2; mode++) {
                const int *vals = (mode == 0) ? sub_kr : sub_std;

                // Partition 0: 4, 5, 6, 7
                // Partition 1: 7, 6, 5, 4
                for (int part = 0; part < 2; part++) {
                    int q4[4], q5[5], q6[6], q7[7];
                    if (part == 0) {
                        for (int k=0; k<4; k++) q4[k] = vals[k];
                        for (int k=0; k<5; k++) q5[k] = vals[4+k];
                        for (int k=0; k<6; k++) q6[k] = vals[9+k];
                        for (int k=0; k<7; k++) q7[k] = vals[15+k];
                    } else {
                        for (int k=0; k<7; k++) q7[k] = vals[k];
                        for (int k=0; k<6; k++) q6[k] = vals[7+k];
                        for (int k=0; k<5; k++) q5[k] = vals[13+k];
                        for (int k=0; k<4; k++) q4[k] = vals[18+k];
                    }

                    int pt[N];
                    for (int t = 0; t < N; t++) {
                        int k = (q4[t % 4] + q5[t % 5] + q6[t % 6] + q7[t % 7]) % 26;
                        if (mode == 0) {
                            int p_kr = (ct_kr[t] - k + 26) % 26;
                            pt[t] = k2std[p_kr];
                        } else {
                            pt[t] = (ct_std[t] - k + 26) % 26;
                        }
                    }

                    float sc = score_pt(pt);
                    if (sc > -5.5f) {
                        #pragma omp critical
                        {
                            char pt_str[N + 1];
                            for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt[t];
                            pt_str[N] = '\0';
                            printf(">>> BREAKTHROUGH HIT! Score: %.4f | Sub: %s | Part: %d | Mode: %d <<<\n",
                                   sc, sub, part, mode);
                            printf("  PT: %s\n\n", pt_str);
                        }
                    }

                    if (sc > loc_best) {
                        loc_best = sc;
                        strcpy(loc_sub, sub);
                        loc_part = part;
                        loc_mode = mode;
                        for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                        loc_pt[N] = '\0';
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best > best_sc) {
                best_sc = loc_best;
                strcpy(best_sub, loc_sub);
                strcpy(best_pt, loc_pt);
                best_part = loc_part;
                best_mode = loc_mode;
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Evaluated %ld 22-letter substrings in %.3f s\n", n_letters - 21, elapsed);
    printf("Best Score: %.4f | Sub: %s | Part: %d | Mode: %d\n", best_sc, best_sub, best_part, best_mode);
    printf("PT: %.70s...\n\n", best_pt);

    free(text);
}

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];
        ct_std[i] = PK8_CT[i] - 'A';
    }

    test_corpus("theophilus_book3_english.txt");
    test_corpus("theophilus_hendrie.txt");
    test_corpus("candidate_running_keys.txt");

    return 0;
}
