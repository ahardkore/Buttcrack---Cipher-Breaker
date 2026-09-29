#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const int q2_4[4] = {0, 1, 0, 0};
static const int q2_5[5] = {0, 0, 1, 0, 0};
static const int q2_6[6] = {0, 0, 0, 1, 0, 0};
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};

static int c_idx[N];
static int alpha_to_std[26];
static int char_to_k[256];
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
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK8_CT[i]];
    }
}

static inline int is_k_odd(char c) {
    int idx = char_to_k[(unsigned char)c];
    return idx % 2;
}

static inline int match_parity(const char *w, int len, const int *pat) {
    for (int i = 0; i < len; i++) {
        if (is_k_odd(w[i]) != pat[i]) return 0;
    }
    return 1;
}

typedef struct { char word[8]; int idx[7]; } WordItem;

static WordItem list4[1000]; static int n4 = 0;
static WordItem list5[1000]; static int n5 = 0;
static WordItem list6[100];  static int n6 = 0;
static WordItem list7[1000]; static int n7 = 0;

void load_matching_words() {
    FILE *f; char buf[64];

    f = fopen("words_4.txt", "r");
    while (fgets(buf, sizeof(buf), f)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 4 && match_parity(buf, 4, q2_4)) {
            strcpy(list4[n4].word, buf);
            for (int i = 0; i < 4; i++) list4[n4].idx[i] = char_to_k[(unsigned char)buf[i]];
            n4++;
        }
    }
    fclose(f);

    f = fopen("words_5.txt", "r");
    while (fgets(buf, sizeof(buf), f)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 5 && match_parity(buf, 5, q2_5)) {
            strcpy(list5[n5].word, buf);
            for (int i = 0; i < 5; i++) list5[n5].idx[i] = char_to_k[(unsigned char)buf[i]];
            n5++;
        }
    }
    fclose(f);

    f = fopen("words_6.txt", "r");
    while (fgets(buf, sizeof(buf), f)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 6 && match_parity(buf, 6, q2_6)) {
            strcpy(list6[n6].word, buf);
            for (int i = 0; i < 6; i++) list6[n6].idx[i] = char_to_k[(unsigned char)buf[i]];
            n6++;
        }
    }
    fclose(f);

    f = fopen("words_7.txt", "r");
    while (fgets(buf, sizeof(buf), f)) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 7 && match_parity(buf, 7, q2_7)) {
            strcpy(list7[n7].word, buf);
            for (int i = 0; i < 7; i++) list7[n7].idx[i] = char_to_k[(unsigned char)buf[i]];
            n7++;
        }
    }
    fclose(f);

    printf("Loaded parity-matching words: n4=%d, n5=%d, n6=%d, n7=%d\n", n4, n5, n6, n7);
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    init_tables();
    load_quadgrams();
    load_matching_words();

    long long total_quads = (long long)n4 * n5 * n6 * n7;
    printf("Evaluating all %lld word quadruples on PK8...\n", total_quads);

    float global_best_sc = -999.0f;
    char best_w4[8] = "", best_w5[8] = "", best_w6[8] = "", best_w7[8] = "";
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_w4[8] = "", local_w5[8] = "", local_w6[8] = "", local_w7[8] = "";
        char local_pt[N + 1] = "";

        int pt[N];

        #pragma omp for schedule(dynamic, 64)
        for (int i4 = 0; i4 < n4; i4++) {
            const WordItem *pw4 = &list4[i4];

            for (int i5 = 0; i5 < n5; i5++) {
                const WordItem *pw5 = &list5[i5];

                int k20[20];
                for (int i = 0; i < 20; i++) {
                    k20[i] = (pw4->idx[i % 4] + pw5->idx[i % 5]) % 26;
                }

                for (int i6 = 0; i6 < n6; i6++) {
                    const WordItem *pw6 = &list6[i6];

                    for (int i7 = 0; i7 < n7; i7++) {
                        const WordItem *pw7 = &list7[i7];

                        // Decrypt full text
                        for (int i = 0; i < N; i++) {
                            int k = (k20[i % 20] + pw6->idx[i % 6] + pw7->idx[i % 7]) % 26;
                            int p = (c_idx[i] - k + 26) % 26;
                            pt[i] = alpha_to_std[p];
                        }

                        // Early check on first 12 chars
                        float early_sc = 0.0f;
                        for (int i = 0; i < 9; i++) early_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        if (early_sc < -55.0f) continue; // Early exit

                        float sc = score_plain(pt);

                        if (sc > -5.5f) {
                            #pragma omp critical
                            {
                                printf("\n>>> HIT! Score = %.4f | (%s, %s, %s, %s)\n",
                                       sc, pw4->word, pw5->word, pw6->word, pw7->word);
                                char s_pt[N + 1];
                                for (int i = 0; i < N; i++) s_pt[i] = 'A' + pt[i];
                                s_pt[N] = '\0';
                                printf("  PT: %s\n\n", s_pt);
                                fflush(stdout);
                            }
                        }

                        if (sc > local_best_sc) {
                            local_best_sc = sc;
                            strcpy(local_w4, pw4->word);
                            strcpy(local_w5, pw5->word);
                            strcpy(local_w6, pw6->word);
                            strcpy(local_w7, pw7->word);
                            for (int i = 0; i < N; i++) local_pt[i] = 'A' + pt[i];
                            local_pt[N] = '\0';
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(best_w4, local_w4);
                strcpy(best_w5, local_w5);
                strcpy(best_w6, local_w6);
                strcpy(best_w7, local_w7);
                strcpy(best_pt, local_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted in %.2f s (%.1f million quads/sec)\n", elapsed, total_quads / (elapsed * 1e6));
    printf("Global Best Score = %.4f | Words: (%s, %s, %s, %s)\n",
           global_best_sc, best_w4, best_w5, best_w6, best_w7);
    printf("Plaintext: %s\n", best_pt);

    return 0;
}
