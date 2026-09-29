#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float qgram[26][26][26][26];

void load_qgrams() {
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open english_quadgrams.txt\n"); exit(1); }
    char line[128];
    double total = 0;
    static double counts[26][26][26][26];
    memset(counts, 0, sizeof(counts));
    while (fgets(line, sizeof(line), f)) {
        char gram[5]; double count;
        if (sscanf(line, "%4s %lf", gram, &count) == 2) {
            int a = gram[0] - 'A', b = gram[1] - 'A', c = gram[2] - 'A', d = gram[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = count;
                total += count;
            }
        }
    }
    fclose(f);
    float floor_val = log10f(0.01f / total);
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    qgram[a][b][c][d] = counts[a][b][c][d] > 0 ? log10f(counts[a][b][c][d] / total) : floor_val;
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

float score_text(const int *pt, int len) {
    float sc = 0;
    for (int i = 0; i < len - 3; i++) {
        sc += qgram[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc;
}

void solve_3clock(int use_kryptos, int restarts) {
    int N = strlen(PK10_CT);
    const char *alpha = use_kryptos ? KRYPTOS : STD;
    int c_idx[600];
    int alpha_to_std[26];
    for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK10_CT[i]) - alpha;

    float global_best_sc = -99999.0f;
    char global_best_pt[600];

    printf("Starting 3-clock {7, 8, 9} on PK10 under %s (%d restarts)...\n",
           use_kryptos ? "KRYPTOS" : "STD", restarts);

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 7777 + use_kryptos * 31;
        int q7[7], q8[8], q9[9];
        int pt_std[600];

        #pragma omp for
        for (int r = 0; r < restarts; r++) {
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 8; i++) q8[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;

            for (int i = 0; i < N; i++) {
                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                pt_std[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
            }
            float cur_sc = score_text(pt_std, N);

            // Coordinate descent
            int improved = 1, iter = 0;
            while (improved && iter < 20) {
                improved = 0; iter++;
                for (int clock_id = 0; clock_id < 3; clock_id++) {
                    int mod = (clock_id == 0) ? 7 : (clock_id == 1 ? 8 : 9);
                    int *q = (clock_id == 0) ? q7 : (clock_id == 1 ? q8 : q9);

                    for (int j = 0; j < mod; j++) {
                        int best_val = q[j];
                        float best_val_sc = cur_sc;
                        int orig_val = q[j];

                        for (int cand = 0; cand < 26; cand++) {
                            if (cand == orig_val) continue;
                            q[j] = cand;
                            for (int i = j; i < N; i += mod) {
                                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                                pt_std[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                            }
                            float sc = score_text(pt_std, N);
                            if (sc > best_val_sc) {
                                best_val_sc = sc;
                                best_val = cand;
                            }
                        }
                        if (best_val != orig_val) {
                            q[j] = best_val;
                            cur_sc = best_val_sc;
                            improved = 1;
                        }
                        q[j] = best_val;
                        for (int i = j; i < N; i += mod) {
                            int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                            pt_std[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (cur_sc > global_best_sc) {
                    global_best_sc = cur_sc;
                    for (int i = 0; i < N; i++) {
                        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                        global_best_pt[i] = 'A' + alpha_to_std[(c_idx[i] - k + 26) % 26];
                    }
                    global_best_pt[N] = '\0';
                    printf("Restart %5d: Score = %8.2f (avg %6.4f) | %s\n",
                           r, cur_sc, cur_sc / (N - 3), global_best_pt);
                    fflush(stdout);
                }
            }
        }
    }
    printf("Finished! Best avg = %6.4f\n", global_best_sc / (N - 3));
}

int main() {
    load_qgrams();
    solve_3clock(1, 2000); // KRYPTOS
    solve_3clock(0, 2000); // STD
    return 0;
}
