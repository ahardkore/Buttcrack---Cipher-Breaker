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

void test_p(int P, int model_type, const char *model_name) {
    int N = strlen(PK10_CT);
    int c_idx[600];
    int alpha_to_std[26];
    const char *alpha = (model_type == 0) ? KRYPTOS : STD;
    for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK10_CT[i]) - alpha;

    float global_best_sc = -99999.0f;
    char global_best_pt[600];

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 999;
        int shifts[100];
        int pt_std[600];

        #pragma omp for
        for (int r = 0; r < 2000; r++) {
            for (int j = 0; j < P; j++) shifts[j] = rand_r(&seed) % 26;
            for (int i = 0; i < N; i++) {
                int p = (c_idx[i] - shifts[i % P] + 26) % 26;
                pt_std[i] = alpha_to_std[p];
            }
            float cur_sc = score_text(pt_std, N);

            int improved = 1, iter = 0;
            while (improved && iter < 20) {
                improved = 0; iter++;
                for (int j = 0; j < P; j++) {
                    int best_s = shifts[j];
                    float best_s_sc = cur_sc;
                    int old_s = shifts[j];

                    for (int cand_s = 0; cand_s < 26; cand_s++) {
                        if (cand_s == old_s) continue;
                        for (int i = j; i < N; i += P) {
                            pt_std[i] = alpha_to_std[(c_idx[i] - cand_s + 26) % 26];
                        }
                        float sc = score_text(pt_std, N);
                        if (sc > best_s_sc) {
                            best_s_sc = sc;
                            best_s = cand_s;
                        }
                    }
                    if (best_s != old_s) {
                        shifts[j] = best_s;
                        cur_sc = best_s_sc;
                        improved = 1;
                    }
                    for (int i = j; i < N; i += P) {
                        pt_std[i] = alpha_to_std[(c_idx[i] - shifts[j] + 26) % 26];
                    }
                }
            }

            #pragma omp critical
            {
                if (cur_sc > global_best_sc) {
                    global_best_sc = cur_sc;
                    for (int i = 0; i < N; i++) global_best_pt[i] = 'A' + pt_std[i];
                    global_best_pt[N] = '\0';
                }
            }
        }
    }
    printf("[%s P=%2d] Best score = %8.2f (avg %6.4f) | %s\n",
           model_name, P, global_best_sc, global_best_sc / (N - 3), global_best_pt);
}

int main() {
    load_qgrams();
    test_p(14, 0, "Quag3(KRYPTOS)");
    test_p(14, 1, "Vig(STD)");
    test_p(7, 0, "Quag3(KRYPTOS)");
    test_p(7, 1, "Vig(STD)");
    return 0;
}
