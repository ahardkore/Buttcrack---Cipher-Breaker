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
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

// Word storage
typedef struct {
    char str[8];
    int kr[7];
    int std[7];
} Word;

static Word *w4 = NULL;
static int n4 = 0;
static Word *w7 = NULL;
static int n7 = 0;

void load_wordlists() {
    FILE *f = fopen("all_words.txt", "r");
    if (!f) { printf("Cannot open all_words.txt\n"); exit(1); }

    int cap4 = 10000, cap7 = 50000;
    w4 = malloc(cap4 * sizeof(Word));
    w7 = malloc(cap7 * sizeof(Word));

    char buf[128];
    while (fscanf(f, "%127s", buf) == 1) {
        int len = strlen(buf);
        int valid = 1;
        for (int i = 0; i < len; i++) {
            if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] -= 32;
            if (buf[i] < 'A' || buf[i] > 'Z') { valid = 0; break; }
        }
        if (!valid) continue;

        if (len == 4) {
            if (n4 >= cap4) { cap4 *= 2; w4 = realloc(w4, cap4 * sizeof(Word)); }
            strcpy(w4[n4].str, buf);
            for (int i = 0; i < 4; i++) {
                w4[n4].std[i] = buf[i] - 'A';
                w4[n4].kr[i] = hpos[(unsigned char)buf[i]];
            }
            n4++;
        } else if (len == 7) {
            if (n7 >= cap7) { cap7 *= 2; w7 = realloc(w7, cap7 * sizeof(Word)); }
            strcpy(w7[n7].str, buf);
            for (int i = 0; i < 7; i++) {
                w7[n7].std[i] = buf[i] - 'A';
                w7[n7].kr[i] = hpos[(unsigned char)buf[i]];
            }
            n7++;
        }
    }
    fclose(f);
    printf("Loaded %d 4-letter words and %d 7-letter words from dictionary.\n", n4, n7);
}

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK9_CT[i]];
        ct_std[i] = PK9_CT[i] - 'A';
    }

    load_wordlists();

    printf("Starting exhaustive sweep of %ld word pairs on PK9...\n", (long)n4 * n7);
    double t0 = omp_get_wtime();

    // Mode 0: Quagmire III (KRYPTOS offsets)
    // Mode 1: Standard Vigenere (A-Z offsets)
    for (int mode = 0; mode < 2; mode++) {
        printf("\n=========================================\n");
        printf("Testing Mode: %s\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Vigenere (A-Z)");
        printf("=========================================\n");

        float best_sc = -999.0f;
        char best_w4[8] = "", best_w7[8] = "";
        char best_pt[150] = "";

        #pragma omp parallel
        {
            float loc_best = -999.0f;
            char loc_w4[8] = "", loc_w7[8] = "";
            char loc_pt[150] = "";

            #pragma omp for schedule(dynamic, 16)
            for (int i = 0; i < n4; i++) {
                int q4[4];
                if (mode == 0) for (int k=0; k<4; k++) q4[k] = w4[i].kr[k];
                else for (int k=0; k<4; k++) q4[k] = w4[i].std[k];

                for (int j = 0; j < n7; j++) {
                    int q7[7];
                    if (mode == 0) for (int k=0; k<7; k++) q7[k] = w7[j].kr[k];
                    else for (int k=0; k<7; k++) q7[k] = w7[j].std[k];

                    // Stage 1: Quick filter on first 16 chars
                    int pt16[16];
                    for (int t = 0; t < 16; t++) {
                        int k = (q4[t % 4] + q7[t % 7]) % 26;
                        if (mode == 0) {
                            int p_kr = (ct_kr[t] - k + 26) % 26;
                            pt16[t] = k2std[p_kr];
                        } else {
                            pt16[t] = (ct_std[t] - k + 26) % 26;
                        }
                    }

                    float s16 = 0.0f;
                    for (int t = 0; t < 13; t++) {
                        s16 += quad[pt16[t]][pt16[t+1]][pt16[t+2]][pt16[t+3]];
                    }
                    s16 /= 13.0f;

                    // Threshold: English quadgram average is ~-4.5. Random is -9.0.
                    if (s16 < -5.6f) continue;

                    // Stage 2: Full 144 chars evaluation
                    int pt[N];
                    for (int t = 0; t < N; t++) {
                        int k = (q4[t % 4] + q7[t % 7]) % 26;
                        if (mode == 0) {
                            int p_kr = (ct_kr[t] - k + 26) % 26;
                            pt[t] = k2std[p_kr];
                        } else {
                            pt[t] = (ct_std[t] - k + 26) % 26;
                        }
                    }

                    float s_full = 0.0f;
                    for (int t = 0; t < N - 3; t++) {
                        s_full += quad[pt[t]][pt[t+1]][pt[t+2]][pt[t+3]];
                    }
                    s_full /= (N - 3);

                    if (s_full > -5.2f) {
                        #pragma omp critical
                        {
                            char pt_str[N + 1];
                            for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt[t];
                            pt_str[N] = '\0';
                            printf(">>> HIGH SCORING HIT! Score: %.4f | W4: %s | W7: %s <<<\n",
                                   s_full, w4[i].str, w7[j].str);
                            printf("  PT: %s\n\n", pt_str);
                        }
                    }

                    if (s_full > loc_best) {
                        loc_best = s_full;
                        strcpy(loc_w4, w4[i].str);
                        strcpy(loc_w7, w7[j].str);
                        for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                        loc_pt[N] = '\0';
                    }
                }
            }

            #pragma omp critical
            {
                if (loc_best > best_sc) {
                    best_sc = loc_best;
                    strcpy(best_w4, loc_w4);
                    strcpy(best_w7, loc_w7);
                    strcpy(best_pt, loc_pt);
                }
            }
        }

        printf("Best Score: %.4f | W4: %s | W7: %s\n", best_sc, best_w4, best_w7);
        printf("PT: %s\n", best_pt);
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nAll word pair sweeps completed in %.3f seconds!\n", elapsed);

    free(w4);
    free(w7);
    return 0;
}
