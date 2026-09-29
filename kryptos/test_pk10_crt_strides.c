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

    // 1. Evaluate Stride 72 (multiples of 72: 72, 144, 216, 288, 360, 432)
    printf("--- Testing Stride 72 Multiples on PK10 (Isolating Clock 7) ---\n");
    int S = 72;
    int total_pairs_72 = 0;
    for (int m = 1; m * S < N; m++) total_pairs_72 += (N - m * S);
    printf("Total difference pairs: %d\n", total_pairs_72);

    // Let's test candidate q7 from PK8/PK9:
    int q7_pk8[7] = {0, 2, 9, 23, 23, 6, 20};
    for (int shift_offset = 0; shift_offset < 7; shift_offset++) {
        int q7[7];
        for (int r = 0; r < 7; r++) q7[r] = q7_pk8[(r + shift_offset) % 7];
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
        printf("Phase %d of PK8 q7: LL = %8.2f\n", shift_offset, ll);
    }

    // Zero key baseline:
    double ll_zero = 0;
    for (int m = 1; m * S < N; m++) {
        int stride = m * S;
        for (int i = 0; i < N - stride; i++) {
            int ct_diff = (ct_k[i + stride] - ct_k[i] + 26) % 26;
            ll_zero += log_diff_prob[ct_diff];
        }
    }
    printf("Zero key baseline:  LL = %8.2f\n", ll_zero);

    return 0;
}
