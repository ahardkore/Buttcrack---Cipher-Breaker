#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static double log_diff_prob[26];
static char words7[50000][8];
static char words8[60000][9];

void init_diff_probs() {
    int k2std[26];
    for (int i=0; i<26; i++) k2std[i] = ALPH[i] - 'A';
    double p_k[26] = {0};
    for (int i=0; i<26; i++) p_k[i] = eng_freq[k2std[i]];
    double diff_dist[26] = {0};
    for (int a=0; a<26; a++) {
        for (int b=0; b<26; b++) {
            int d = (a - b + 26) % 26;
            diff_dist[d] += p_k[a] * p_k[b];
        }
    }
    for (int d=0; d<26; d++) log_diff_prob[d] = log(diff_dist[d]);
}

int main() {
    init_diff_probs();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)PK10_CT[i]];

    // 1. Sweep words_7.txt on Stride 72 (Clock 7)
    printf("=== Sweeping words_7.txt on PK10 Stride 72 (Clock 7) ===\n");
    FILE *f7 = fopen("words_7.txt", "r");
    char line[64];
    int n7 = 0;
    while (f7 && fgets(line, sizeof(line), f7) && n7 < 50000) {
        char w[16];
        if (sscanf(line, "%7s", w) == 1 && strlen(w) == 7) {
            strcpy(words7[n7++], w);
        }
    }
    if (f7) fclose(f7);
    printf("Loaded %d 7-letter words\n", n7);

    int S = 72;
    double best_ll_7 = -1e9;
    char best_w7[8] = "";

    #pragma omp parallel for schedule(dynamic, 100)
    for (int idx = 0; idx < n7; idx++) {
        char *w = words7[idx];
        int q7[7];
        int valid = 1;
        for (int r=0; r<7; r++) {
            q7[r] = k2i[(int)w[r]];
            if (q7[r] < 0) { valid = 0; break; }
        }
        if (!valid) continue;

        double ll = 0;
        for (int m = 1; m * S < N; m++) {
            int stride = m * S;
            for (int i = 0; i < N - stride; i++) {
                int ct_diff = (ct_k[i + stride] - ct_k[i] + 26) % 26;
                int sh_diff = (q7[(i + stride) % 7] - q7[i % 7] + 26) % 26;
                int pt_diff = (ct_diff - sh_diff + 26) % 26;
                ll += log_diff_prob[pt_diff];
            }
        }

        #pragma omp critical
        {
            if (ll > best_ll_7) {
                best_ll_7 = ll;
                strcpy(best_w7, w);
            }
        }
    }
    printf("Best 7-letter word for Clock 7: %s (LL = %.2f)\n", best_w7, best_ll_7);

    // 2. Sweep words_8.txt on Stride 63 (Clock 8)
    printf("\n=== Sweeping words_8.txt on PK10 Stride 63 (Clock 8) ===\n");
    FILE *f8 = fopen("words_8.txt", "r");
    int n8 = 0;
    while (f8 && fgets(line, sizeof(line), f8) && n8 < 60000) {
        char w[16];
        if (sscanf(line, "%8s", w) == 1 && strlen(w) == 8) {
            strcpy(words8[n8++], w);
        }
    }
    if (f8) fclose(f8);
    printf("Loaded %d 8-letter words\n", n8);

    int S8 = 63;
    double best_ll_8 = -1e9;
    char best_w8[9] = "";

    #pragma omp parallel for schedule(dynamic, 100)
    for (int idx = 0; idx < n8; idx++) {
        char *w = words8[idx];
        int q8[8];
        int valid = 1;
        for (int r=0; r<8; r++) {
            q8[r] = k2i[(int)w[r]];
            if (q8[r] < 0) { valid = 0; break; }
        }
        if (!valid) continue;

        double ll = 0;
        for (int m = 1; m * S8 < N; m++) {
            int stride = m * S8;
            for (int i = 0; i < N - stride; i++) {
                int ct_diff = (ct_k[i + stride] - ct_k[i] + 26) % 26;
                int sh_diff = (q8[(i + stride) % 8] - q8[i % 8] + 26) % 26;
                int pt_diff = (ct_diff - sh_diff + 26) % 26;
                ll += log_diff_prob[pt_diff];
            }
        }

        #pragma omp critical
        {
            if (ll > best_ll_8) {
                best_ll_8 = ll;
                strcpy(best_w8, w);
            }
        }
    }
    printf("Best 8-letter word for Clock 8: %s (LL = %.2f)\n", best_w8, best_ll_8);

    return 0;
}
