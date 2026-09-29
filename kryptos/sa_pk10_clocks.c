#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdint.h>
#include <omp.h>

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kryptos_to_num[26];
static int num_to_kryptos[26];

static const char *pk10_raw = 
"HNNZUGQGOGTCHTRHGYEZTDNCTAKNELETPEFTALMOTSUHNIUETRNSEWFHGATENGY"
"FAWAVNACHHOEURRTSTTMROEVEVUEVSIOIURDSMECWANTIMCTXWEDTRTDEDMRTFEE"
"UTEAXHOEIKHHHIVIADEVEDOAESESHNETTYWEFIHHSTNTTENUWTVIEXMRTDHADGUE"
"SHTATWNEFROOHATFTERKSRTYHEEEFSOEEFSEFRITNEATSTHEDMREEYNDESHTATW"
"MEFVOOHTTFTERLSRTEYEFESOEEFSEERITNETTTTHRDMRDEYNDESHTATWIEFROOHA"
"TETERKSRTYEEEEFSOEEFNEFRITNETTATTHEDMRCEYNEETHTATWIEFROOHATETKR"
"SKTYHEEEFSOEEFNEFAITNETTATTHEDMRCEYNDESHTATWMEVOOHATFTERKSRTEYE"
"EFEFSEERITNETTTTHRDMRDEYNDESHTATWIEFROOHATETERKSRTYEEEEFSOEEFNE";

static int pk10_kr[504];
static int pk10_std[504];
static float quad[26][26][26][26];

static const int q7_fixed[7] = {5, 5, 8, 7, 16, 10, 22};

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) {
        printf("Error: english_quadgrams.txt not found!\n");
        exit(1);
    }
    char buf[64];
    double total = 0;
    while (fgets(buf, sizeof(buf), f)) {
        char qg[8];
        double cnt;
        if (sscanf(buf, "%s %lf", qg, &cnt) == 2) {
            total += cnt;
        }
    }
    rewind(f);
    while (fgets(buf, sizeof(buf), f)) {
        char qg[8];
        double cnt;
        if (sscanf(buf, "%s %lf", qg, &cnt) == 2 && strlen(qg) == 4) {
            int a = qg[0] - 'A';
            int b = qg[1] - 'A';
            int c = qg[2] - 'A';
            int d = qg[3] - 'A';
            quad[a][b][c][d] = (float)log10(cnt / total);
        }
    }
    fclose(f);
}

void init() {
    for (int i = 0; i < 26; i++) {
        kryptos_to_num[KRYPTOS[i] - 'A'] = i;
        num_to_kryptos[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < 504; i++) {
        pk10_kr[i] = kryptos_to_num[pk10_raw[i] - 'A'];
        pk10_std[i] = pk10_raw[i] - 'A';
    }
}

static inline float score_text(const int *txt, int len) {
    float s = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        s += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (len - 3);
}

// Mode 0: Kryptos Vigenere: P_kr = (C_kr - K) % 26
// Mode 1: Kryptos Beaufort: P_kr = (K - C_kr) % 26
// Mode 2: Std Vigenere: P = (C - K) % 26
// Mode 3: Std Beaufort: P = (K - C) % 26
void decrypt_pk10(const int *q8, const int *q9, int mode, int *out) {
    for (int i = 0; i < 504; i++) {
        int k = (q7_fixed[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        if (mode == 0) {
            int p_kr = (pk10_kr[i] - k + 26) % 26;
            out[i] = num_to_kryptos[p_kr];
        } else if (mode == 1) {
            int p_kr = (k - pk10_kr[i] + 26) % 26;
            out[i] = num_to_kryptos[p_kr];
        } else if (mode == 2) {
            out[i] = (pk10_std[i] - k + 26) % 26;
        } else if (mode == 3) {
            out[i] = (k - pk10_std[i] + 26) % 26;
        }
    }
}

int main() {
    load_quadgrams();
    init();

    printf("Starting SA on PK10 Clocks Q8 and Q9 across 4 cipher modes...\n");

    for (int mode = 0; mode < 4; mode++) {
        printf("\n=== Testing Mode %d ===\n", mode);
        #pragma omp parallel
        {
            unsigned int seed = time(NULL) ^ (omp_get_thread_num() * 12345);
            int best_local_q8[8], best_local_q9[9];
            float best_local_sc = -999.0f;

            for (int restart = 0; restart < 50; restart++) {
                int q8[8], q9[9];
                q8[0] = 0;
                for (int i = 1; i < 8; i++) q8[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;

                int plain[504];
                decrypt_pk10(q8, q9, mode, plain);
                float cur_sc = score_text(plain, 504);

                float T = 1.0f;
                float T_min = 0.001f;
                float alpha = 0.99995f;

                for (int step = 0; step < 100000; step++) {
                    int var = rand_r(&seed) % 16;
                    int delta = (rand_r(&seed) % 2 == 0) ? 1 : 25;
                    int old_val;

                    if (var < 7) {
                        old_val = q8[var + 1];
                        q8[var + 1] = (old_val + delta) % 26;
                    } else {
                        old_val = q9[var - 7];
                        q9[var - 7] = (old_val + delta) % 26;
                    }

                    decrypt_pk10(q8, q9, mode, plain);
                    float new_sc = score_text(plain, 504);

                    float diff = new_sc - cur_sc;
                    if (diff > 0 || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                        cur_sc = new_sc;
                        if (cur_sc > best_local_sc) {
                            best_local_sc = cur_sc;
                            memcpy(best_local_q8, q8, sizeof(q8));
                            memcpy(best_local_q9, q9, sizeof(q9));
                            if (best_local_sc > -6.0f) {
                                printf("[Thread %d] Mode %d NEW HIGH: %.4f\n", omp_get_thread_num(), mode, best_local_sc);
                            }
                        }
                    } else {
                        if (var < 7) {
                            q8[var + 1] = old_val;
                        } else {
                            q9[var - 7] = old_val;
                        }
                    }

                    T *= alpha;
                    if (T < T_min) T = T_min;
                }
            }

            #pragma omp critical
            {
                if (best_local_sc > -7.0f) {
                    printf("Mode %d Global candidate score: %.4f\n", mode, best_local_sc);
                    printf("q8: "); for (int i = 0; i < 8; i++) printf("%d ", best_local_q8[i]); printf("\n");
                    printf("q9: "); for (int i = 0; i < 9; i++) printf("%d ", best_local_q9[i]); printf("\n");
                    int plain[504];
                    decrypt_pk10(best_local_q8, best_local_q9, mode, plain);
                    char out[505];
                    for (int i = 0; i < 504; i++) out[i] = plain[i] + 'A';
                    out[504] = '\0';
                    printf("Plaintext preview:\n%.120s\n\n", out);
                }
            }
        }
    }

    return 0;
}
