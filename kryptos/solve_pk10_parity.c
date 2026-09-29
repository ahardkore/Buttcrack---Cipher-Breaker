#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int q2_7_pk8[7] = {0, 1, 1, 1, 0, 0, 0};

int main() {
    int N = strlen(PK10_CT);
    int c_kryptos[600], c_std[600];
    for (int i = 0; i < N; i++) {
        c_kryptos[i] = (strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS) % 2;
        c_std[i] = (PK10_CT[i] - 'A') % 2;
    }

    printf("Evaluating binary parity of {7, 8, 9} on PK10 (N=%d)...\n", N);

    for (int model = 0; model < 4; model++) {
        const char *mname = (model < 2) ? "KRYPTOS" : "STD";
        int is_beau = (model % 2 == 1);
        int *c_bit = (model < 2) ? c_kryptos : c_std;
        int target_bit = (model < 2) ? 1 : 0; // 64% 1 for KRYPTOS, 57% 0 for STD

        // Test with PK8's q7
        int max_m = 0, best_q8[8], best_q9[9], cnt = 0;

        for (int b8 = 0; b8 < 256; b8++) {
            int q8[8];
            for (int k = 0; k < 8; k++) q8[k] = (b8 >> k) & 1;

            for (int b9 = 0; b9 < 256; b9++) {
                int q9[9];
                for (int k = 0; k < 8; k++) q9[k] = (b9 >> k) & 1;
                q9[8] = 0; // gauge fix

                int m = 0;
                for (int i = 0; i < N; i++) {
                    int k = q2_7_pk8[i % 7] ^ q8[i % 8] ^ q9[i % 9];
                    int p = is_beau ? (k ^ c_bit[i]) : (c_bit[i] ^ k);
                    if (p == target_bit) m++;
                }

                if (m > max_m) {
                    max_m = m;
                    for (int k = 0; k < 8; k++) best_q8[k] = q8[k];
                    for (int k = 0; k < 9; k++) best_q9[k] = q9[k];
                    cnt = 1;
                } else if (m == max_m) {
                    cnt++;
                }
            }
        }

        printf("[%s %s] With PK8 q7: Max matches = %d / %d (%.2f%%, exp 50%%), count = %d\n",
               mname, is_beau ? "Beaufort" : "Vigenere", max_m, N, (float)max_m / N * 100.0f, cnt);
        printf("  q8: [%d, %d, %d, %d, %d, %d, %d, %d]\n",
               best_q8[0], best_q8[1], best_q8[2], best_q8[3],
               best_q8[4], best_q8[5], best_q8[6], best_q8[7]);
        printf("  q9: [%d, %d, %d, %d, %d, %d, %d, %d, %d]\n\n",
               best_q9[0], best_q9[1], best_q9[2], best_q9[3],
               best_q9[4], best_q9[5], best_q9[6], best_q9[7], best_q9[8]);
    }

    return 0;
}
