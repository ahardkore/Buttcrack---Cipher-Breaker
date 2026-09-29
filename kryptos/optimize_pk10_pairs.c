#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int q2_8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int q2_9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

// Seed keys from optimize_pk10_monograms
static const int seed_q7[7] = {20, 3, 1, 13, 14, 22, 8};
static const int seed_q8[8] = {24, 0, 4, 21, 2, 5, 10, 0};
static const int seed_q9[9] = {0, 0, 11, 19, 7, 25, 6, 6, 0};

static int c_idx[N];
static int alpha_to_std[26];
static float quad[26][26][26][26];

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

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
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
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

    int q13_7[7], q13_8[8], q13_9[9];
    for (int i = 0; i < 7; i++) q13_7[i] = seed_q7[i] % 13;
    for (int i = 0; i < 8; i++) q13_8[i] = seed_q8[i] % 13;
    for (int i = 0; i < 9; i++) q13_9[i] = seed_q9[i] % 13;

    int q7[7], q8[8], q9[9];
    for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], q13_7[i]);
    for (int i = 0; i < 8; i++) q8[i] = crt(q2_8[i], q13_8[i]);
    for (int i = 0; i < 9; i++) q9[i] = crt(q2_9[i], q13_9[i]);

    int pt[N];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
    }

    float cur_sc = score_plain(pt);
    printf("Initial Seed Score = %.4f\n", cur_sc);

    // Free variables: 7 for q7, 7 for q8 (q8[7]=0 gauge), 8 for q9 (q9[8]=0 gauge).
    // Total 22 variables:
    // 0..6: q7[0..6]
    // 7..13: q8[0..6]
    // 14..21: q9[0..7]

    int improved = 1;
    int pass = 0;

    while (improved && pass < 30) {
        improved = 0;
        pass++;
        printf("\n--- Pass %d (Current Best: %.4f) ---\n", pass, cur_sc);

        // 1. Single variable pass
        for (int v = 0; v < 22; v++) {
            int which = (v < 7) ? 0 : ((v < 14) ? 1 : 2);
            int pos = (v < 7) ? v : ((v < 14) ? v - 7 : v - 14);
            int old_val = (which == 0) ? q13_7[pos] : ((which == 1) ? q13_8[pos] : q13_9[pos]);
            int best_val = old_val;
            float best_s = cur_sc;

            for (int test_v = 0; test_v < 13; test_v++) {
                if (test_v == old_val) continue;
                if (which == 0) q7[pos] = crt(q2_7[pos], test_v);
                else if (which == 1) q8[pos] = crt(q2_8[pos], test_v);
                else q9[pos] = crt(q2_9[pos], test_v);

                for (int i = 0; i < N; i++) {
                    int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                    pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_val = test_v;
                }
            }

            if (best_val != old_val) {
                if (which == 0) { q13_7[pos] = best_val; q7[pos] = crt(q2_7[pos], best_val); }
                else if (which == 1) { q13_8[pos] = best_val; q8[pos] = crt(q2_8[pos], best_val); }
                else { q13_9[pos] = best_val; q9[pos] = crt(q2_9[pos], best_val); }
                cur_sc = best_s;
                improved = 1;
                printf("  [1-var] Var %d (%s[%d]) -> %d | New Score = %.4f\n",
                       v, which==0?"q7":(which==1?"q8":"q9"), pos, best_val, cur_sc);
            } else {
                if (which == 0) q7[pos] = crt(q2_7[pos], old_val);
                else if (which == 1) q8[pos] = crt(q2_8[pos], old_val);
                else q9[pos] = crt(q2_9[pos], old_val);
            }
        }

        // 2. Pairwise 2-variable joint pass across all 231 pairs
        #pragma omp parallel for schedule(dynamic, 1)
        for (int v1 = 0; v1 < 22; v1++) {
            for (int v2 = v1 + 1; v2 < 22; v2++) {
                int which1 = (v1 < 7) ? 0 : ((v1 < 14) ? 1 : 2);
                int pos1 = (v1 < 7) ? v1 : ((v1 < 14) ? v1 - 7 : v1 - 14);
                int which2 = (v2 < 7) ? 0 : ((v2 < 14) ? 1 : 2);
                int pos2 = (v2 < 7) ? v2 : ((v2 < 14) ? v2 - 7 : v2 - 14);

                int local_q7[7], local_q8[8], local_q9[9];
                int local_pt[N];
                for (int i = 0; i < 7; i++) local_q7[i] = q7[i];
                for (int i = 0; i < 8; i++) local_q8[i] = q8[i];
                for (int i = 0; i < 9; i++) local_q9[i] = q9[i];

                int old_val1 = (which1 == 0) ? q13_7[pos1] : ((which1 == 1) ? q13_8[pos1] : q13_9[pos1]);
                int old_val2 = (which2 == 0) ? q13_7[pos2] : ((which2 == 1) ? q13_8[pos2] : q13_9[pos2]);

                int best_val1 = old_val1, best_val2 = old_val2;
                float best_s = cur_sc;

                for (int val1 = 0; val1 < 13; val1++) {
                    if (which1 == 0) local_q7[pos1] = crt(q2_7[pos1], val1);
                    else if (which1 == 1) local_q8[pos1] = crt(q2_8[pos1], val1);
                    else local_q9[pos1] = crt(q2_9[pos1], val1);

                    for (int val2 = 0; val2 < 13; val2++) {
                        if (val1 == old_val1 && val2 == old_val2) continue;

                        if (which2 == 0) local_q7[pos2] = crt(q2_7[pos2], val2);
                        else if (which2 == 1) local_q8[pos2] = crt(q2_8[pos2], val2);
                        else local_q9[pos2] = crt(q2_9[pos2], val2);

                        for (int i = 0; i < N; i++) {
                            int k = (local_q7[i % 7] + local_q8[i % 8] + local_q9[i % 9]) % 26;
                            local_pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        float s = score_plain(local_pt);
                        if (s > best_s) {
                            best_s = s;
                            best_val1 = val1;
                            best_val2 = val2;
                        }
                    }
                }

                if (best_s > cur_sc + 0.005f) {
                    #pragma omp critical
                    {
                        if (best_s > cur_sc) {
                            cur_sc = best_s;
                            if (which1 == 0) { q13_7[pos1] = best_val1; q7[pos1] = crt(q2_7[pos1], best_val1); }
                            else if (which1 == 1) { q13_8[pos1] = best_val1; q8[pos1] = crt(q2_8[pos1], best_val1); }
                            else { q13_9[pos1] = best_val1; q9[pos1] = crt(q2_9[pos1], best_val1); }

                            if (which2 == 0) { q13_7[pos2] = best_val2; q7[pos2] = crt(q2_7[pos2], best_val2); }
                            else if (which2 == 1) { q13_8[pos2] = best_val2; q8[pos2] = crt(q2_8[pos2], best_val2); }
                            else { q13_9[pos2] = best_val2; q9[pos2] = crt(q2_9[pos2], best_val2); }

                            improved = 1;
                            printf("  [2-var] Pair (%d, %d) -> (%d, %d) | New Score = %.4f\n",
                                   v1, v2, best_val1, best_val2, cur_sc);
                            fflush(stdout);
                        }
                    }
                }
            }
        }
    }

    printf("\n=== Optimization Complete ===\n");
    printf("Final Score = %.4f\n", cur_sc);
    printf("q7: ["); for (int i = 0; i < 7; i++) printf("%d%s", q7[i], i==6?"]\n":", ");
    printf("q8: ["); for (int i = 0; i < 8; i++) printf("%d%s", q8[i], i==7?"]\n":", ");
    printf("q9: ["); for (int i = 0; i < 9; i++) printf("%d%s", q9[i], i==8?"]\n":", ");

    char final_pt[N + 1];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        final_pt[i] = 'A' + alpha_to_std[(c_idx[i] - k + 26) % 26];
    }
    final_pt[N] = '\0';
    printf("\nDecrypted Plaintext:\n%s\n", final_pt);

    FILE *fout = fopen("pk10_optimized_pt.txt", "w");
    fprintf(fout, "Score: %.4f\n%s\n", cur_sc, final_pt);
    fclose(fout);

    return 0;
}
