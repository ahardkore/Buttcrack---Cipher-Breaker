#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

float get_max_ioc(const char *alpha, int mode, int p1, int p2, int p3, int restarts) {
    int c_idx[N];
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(alpha, PK10_CT[i]) - alpha;
    }

    float max_ioc = 0.0f;

    #pragma omp parallel
    {
        unsigned int seed = 1234 + omp_get_thread_num() * 555;
        float loc_max_ioc = 0.0f;
        int q1[p1], q2[p2], q3[p3];
        int counts[26];

        #pragma omp for
        for (int r = 0; r < restarts; r++) {
            for (int i = 0; i < p1; i++) q1[i] = rand_r(&seed) % 26;
            for (int i = 0; i < p2; i++) q2[i] = rand_r(&seed) % 26;
            for (int i = 0; i < p3; i++) q3[i] = rand_r(&seed) % 26;

            // SA optimization of IoC
            float cur_ioc = 0.0f;
            // compute initial ioc
            memset(counts, 0, sizeof(counts));
            for (int i = 0; i < N; i++) {
                int k = (q1[i % p1] + q2[i % p2] + (p3 > 0 ? q3[i % p3] : 0)) % 26;
                int z;
                if (mode == 0) z = (c_idx[i] - k + 26) % 26; // C - K
                else if (mode == 1) z = (k - c_idx[i] + 26) % 26; // K - C (Beaufort)
                else z = (c_idx[i] + k) % 26; // C + K
                counts[z]++;
            }
            int sp = 0;
            for (int c = 0; c < 26; c++) sp += counts[c] * (counts[c] - 1);
            cur_ioc = (float)sp / (N * (N - 1));

            // local search
            for (int step = 0; step < 300; step++) {
                int which = rand_r(&seed) % (p1 + p2 + (p3 > 0 ? p3 : 0));
                int *target;
                int pos;
                if (which < p1) { target = q1; pos = which; }
                else if (which < p1 + p2) { target = q2; pos = which - p1; }
                else { target = q3; pos = which - p1 - p2; }

                int old_val = target[pos];
                target[pos] = rand_r(&seed) % 26;

                memset(counts, 0, sizeof(counts));
                for (int i = 0; i < N; i++) {
                    int k = (q1[i % p1] + q2[i % p2] + (p3 > 0 ? q3[i % p3] : 0)) % 26;
                    int z;
                    if (mode == 0) z = (c_idx[i] - k + 26) % 26;
                    else if (mode == 1) z = (k - c_idx[i] + 26) % 26;
                    else z = (c_idx[i] + k) % 26;
                    counts[z]++;
                }
                sp = 0;
                for (int c = 0; c < 26; c++) sp += counts[c] * (counts[c] - 1);
                float new_ioc = (float)sp / (N * (N - 1));

                if (new_ioc > cur_ioc) {
                    cur_ioc = new_ioc;
                } else {
                    target[pos] = old_val;
                }
            }

            if (cur_ioc > loc_max_ioc) loc_max_ioc = cur_ioc;
        }

        #pragma omp critical
        {
            if (loc_max_ioc > max_ioc) max_ioc = loc_max_ioc;
        }
    }

    return max_ioc;
}

int main() {
    printf("Testing theoretical maximum IoC under various substitution models on raw PK10:\n\n");
    
    // Test mode 0 (C - K), mode 1 (K - C), mode 2 (C + K)
    // with Kryptos vs Standard alphabet
    // with (7, 8, 9)
    printf("--- Clocks (7, 8, 9) ---\n");
    printf("Kryptos, C - K:    max IoC = %.5f\n", get_max_ioc(KRYPTOS, 0, 7, 8, 9, 200));
    printf("Kryptos, K - C:    max IoC = %.5f\n", get_max_ioc(KRYPTOS, 1, 7, 8, 9, 200));
    printf("Kryptos, C + K:    max IoC = %.5f\n", get_max_ioc(KRYPTOS, 2, 7, 8, 9, 200));
    printf("Standard, C - K:   max IoC = %.5f\n", get_max_ioc(STD, 0, 7, 8, 9, 200));
    printf("Standard, K - C:   max IoC = %.5f\n", get_max_ioc(STD, 1, 7, 8, 9, 200));

    // What if only 2 clocks? (e.g. 7, 8 or 7, 9 or 8, 9 or 42?)
    printf("\n--- Other Clock Configurations (Kryptos C - K) ---\n");
    printf("Clocks (7, 8):     max IoC = %.5f\n", get_max_ioc(KRYPTOS, 0, 7, 8, 0, 200));
    printf("Clocks (7, 9):     max IoC = %.5f\n", get_max_ioc(KRYPTOS, 0, 7, 9, 0, 200));
    printf("Clocks (8, 9):     max IoC = %.5f\n", get_max_ioc(KRYPTOS, 0, 8, 9, 0, 200));
    printf("Clocks (6, 7):     max IoC = %.5f\n", get_max_ioc(KRYPTOS, 0, 6, 7, 0, 200));

    return 0;
}
