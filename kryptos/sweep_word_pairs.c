#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *C_STR = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int C[144];
static const int N = 144;

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.5f;
                }
            }
        }
    }
    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0]-'A', c1 = q[1]-'A', c2 = q[2]-'A', c3 = q[3]-'A';
            if (c0>=0&&c0<26&&c1>=0&&c1<26&&c2>=0&&c2<26&&c3>=0&&c3<26) {
                quad_table[c0][c1][c2][c3] = sc;
            }
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        int std = ALPH_K[i] - 'A';
        k_to_std[i] = std;
        std_to_k[std] = i;
    }
    for (int i = 0; i < N; i++) {
        C[i] = std_to_k[C_STR[i] - 'A'];
    }
}

// Load words of length L
int load_words(int L, char (*words)[16], int (*shifts_k)[16], int (*shifts_s)[16], int max_w) {
    char filename[64];
    sprintf(filename, "/home/user/words_%d.txt", L);
    FILE *f = fopen(filename, "r");
    if (!f) { fprintf(stderr, "Cannot open %s\n", filename); exit(1); }
    int count = 0;
    char line[32];
    while (fscanf(f, "%s", line) == 1 && count < max_w) {
        if ((int)strlen(line) == L) {
            strcpy(words[count], line);
            for (int i = 0; i < L; i++) {
                shifts_k[count][i] = std_to_k[line[i] - 'A'];
                shifts_s[count][i] = line[i] - 'A';
            }
            count++;
        }
    }
    fclose(f);
    return count;
}

#define MAX_WORDS 60000
static char words_A[MAX_WORDS][16];
static int shifts_A_k[MAX_WORDS][16];
static int shifts_A_s[MAX_WORDS][16];

static char words_B[MAX_WORDS][16];
static int shifts_B_k[MAX_WORDS][16];
static int shifts_B_s[MAX_WORDS][16];

void sweep_pair(int la, int lb, int is_kryptos, int mode) {
    int count_A = load_words(la, words_A, shifts_A_k, shifts_A_s, MAX_WORDS);
    int count_B = load_words(lb, words_B, shifts_B_k, shifts_B_s, MAX_WORDS);
    uint64_t total_pairs = (uint64_t)count_A * (uint64_t)count_B;
    printf("\n=== Sweeping (%d, %d): %d x %d = %lu pairs | Alph: %s | Mode: %s ===\n",
           la, lb, count_A, count_B, total_pairs, is_kryptos ? "KRYPTOS" : "STD",
           mode == 0 ? "Vigenere" : "Beaufort");

    double t0 = omp_get_wtime();
    float global_best_sc = -999.0f;
    char best_wa[16] = "", best_wb[16] = "";
    char best_pt[150] = "";

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_wa[16] = "", local_wb[16] = "";
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 64)
        for (int i = 0; i < count_A; i++) {
            const int *sa = is_kryptos ? shifts_A_k[i] : shifts_A_s[i];

            for (int j = 0; j < count_B; j++) {
                const int *sb = is_kryptos ? shifts_B_k[j] : shifts_B_s[j];

                // Fast pre-filter on first 28 chars
                int pt_fast[28];
                float fast_sc = 0.0f;
                for (int pos = 0; pos < 28; pos++) {
                    int k = (sa[pos % la] + sb[pos % lb]) % 26;
                    int ci = C[pos];
                    int pi;
                    if (mode == 0) pi = (ci - k + 26) % 26;
                    else pi = (k - ci + 26) % 26;

                    if (is_kryptos) pt_fast[pos] = k_to_std[pi];
                    else pt_fast[pos] = pi;
                }

                for (int pos = 0; pos < 25; pos++) {
                    fast_sc += quad_table[pt_fast[pos]][pt_fast[pos+1]][pt_fast[pos+2]][pt_fast[pos+3]];
                }
                // Threshold: -185.0 for 25 quadgrams is avg -7.4 per quadgram
                if (fast_sc < -185.0f) continue;

                // Full evaluation on 144 chars
                int pt[144];
                for (int pos = 0; pos < N; pos++) {
                    int k = (sa[pos % la] + sb[pos % lb]) % 26;
                    int ci = C[pos];
                    int pi;
                    if (mode == 0) pi = (ci - k + 26) % 26;
                    else pi = (k - ci + 26) % 26;

                    if (is_kryptos) pt[pos] = k_to_std[pi];
                    else pt[pos] = pi;
                }

                float full_sc = 0.0f;
                for (int pos = 0; pos < N - 3; pos++) {
                    full_sc += quad_table[pt[pos]][pt[pos+1]][pt[pos+2]][pt[pos+3]];
                }
                full_sc /= (N - 3);

                if (full_sc > local_best_sc) {
                    local_best_sc = full_sc;
                    strcpy(local_wa, words_A[i]);
                    strcpy(local_wb, words_B[j]);
                    for (int pos = 0; pos < N; pos++) local_pt[pos] = pt[pos] + 'A';
                    local_pt[N] = '\0';

                    if (full_sc > -6.0f) {
                        #pragma omp critical
                        {
                            printf("  >>> HIT! %s + %s | sc=%.3f\n    PT: %s\n",
                                   local_wa, local_wb, full_sc, local_pt);
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(best_wa, local_wa);
                strcpy(best_wb, local_wb);
                strcpy(best_pt, local_pt);
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Done in %.2fs. Best: %s + %s | sc=%.3f\n  PT: %.70s...\n",
           t1 - t0, best_wa, best_wb, global_best_sc, best_pt);
}

int main() {
    init();

    // 1. Clocks (4, 7) on KRYPTOS Vigenere
    sweep_pair(4, 7, 1, 0);

    // 2. Clocks (4, 7) on KRYPTOS Beaufort
    sweep_pair(4, 7, 1, 1);

    // 3. Clocks (5, 7) on KRYPTOS Vigenere
    sweep_pair(5, 7, 1, 0);

    // 4. Clocks (5, 7) on KRYPTOS Beaufort
    sweep_pair(5, 7, 1, 1);

    // 5. Clocks (3, 7) on KRYPTOS Vigenere
    sweep_pair(3, 7, 1, 0);

    return 0;
}
