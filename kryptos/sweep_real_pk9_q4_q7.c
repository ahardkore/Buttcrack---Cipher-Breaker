#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int k_to_std[26];
static int std_to_k[26];

static const float eng_freq[26] = {
    82, 15, 28, 43, 127, 22, 20, 61, 70, 2, 8, 40, 24, 67, 75, 19, 1, 60, 63, 91, 28, 10, 24, 2, 20, 1
};

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_std[i] = PK9_REAL[i] - 'A';
        ct_kr[i] = std_to_k[PK9_REAL[i] - 'A'];
    }
}

float eval_ioc(const int *cnt) {
    int num = 0;
    for (int i=0; i<26; i++) num += cnt[i] * (cnt[i] - 1);
    return (float)num / (float)(N * (N - 1));
}

float eval_chi2(const int *cnt) {
    float chi2 = 0.0f;
    for (int i=0; i<26; i++) {
        float expected = (float)N * (eng_freq[i] / 1000.0f);
        float diff = (float)cnt[i] - expected;
        chi2 += (diff * diff) / (expected + 0.001f);
    }
    return chi2;
}

int main() {
    init();
    printf("Real PK9 loaded. Sweeping 128 masks of Q7 x 26^3 Q4 states on REAL PK9...\n");
    
    // Q7 mod 13 anchor:
    const int q7_base[7] = {0, 2, 9, 10, 10, 6, 7};
    
    // 128 masks of Q7
    int q7_candidates[128][7];
    for (int m = 0; m < 128; m++) {
        for (int j = 0; j < 7; j++) {
            q7_candidates[m][j] = (q7_base[j] + ((m >> j) & 1) * 13) % 26;
        }
    }
    
    double t0 = omp_get_wtime();
    float best_chi2_kr = 1e9f;
    float best_chi2_std = 1e9f;
    int best_m_kr = 0, best_q4_kr[4] = {0};
    int best_m_std = 0, best_q4_std[4] = {0};
    
    #pragma omp parallel
    {
        float local_best_chi2_kr = 1e9f;
        int local_best_m_kr = 0, local_best_q4_kr[4] = {0};
        int cnt[26];
        
        #pragma omp for schedule(dynamic)
        for (int m = 0; m < 128; m++) {
            const int *q7 = q7_candidates[m];
            
            // Sweep Q4 with Q4[0] = 0
            int q4[4];
            q4[0] = 0;
            
            for (int q4_1 = 0; q4_1 < 26; q4_1++) {
                q4[1] = q4_1;
                for (int q4_2 = 0; q4_2 < 26; q4_2++) {
                    q4[2] = q4_2;
                    for (int q4_3 = 0; q4_3 < 26; q4_3++) {
                        q4[3] = q4_3;
                        
                        // Decrypt QIII (KRYPTOS alphabet)
                        memset(cnt, 0, sizeof(cnt));
                        for (int i = 0; i < N; i++) {
                            int shift = (q4[i % 4] + q7[i % 7]) % 26;
                            int p_kr = (ct_kr[i] - shift + 26) % 26;
                            cnt[k_to_std[p_kr]]++;
                        }
                        
                        float chi2 = eval_chi2(cnt);
                        if (chi2 < local_best_chi2_kr) {
                            local_best_chi2_kr = chi2;
                            local_best_m_kr = m;
                            local_best_q4_kr[1] = q4_1;
                            local_best_q4_kr[2] = q4_2;
                            local_best_q4_kr[3] = q4_3;
                            if (chi2 < 45.0f) {
                                #pragma omp critical
                                {
                                    float ioc = eval_ioc(cnt);
                                    printf("[QIII HIT] Mask %d | Q4=[0,%d,%d,%d] | Chi2=%.2f | IoC=%.5f\n",
                                           m, q4_1, q4_2, q4_3, chi2, ioc);
                                }
                            }
                        }
                    }
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best_chi2_kr < best_chi2_kr) {
                best_chi2_kr = local_best_chi2_kr;
                best_m_kr = local_best_m_kr;
                memcpy(best_q4_kr, local_best_q4_kr, sizeof(best_q4_kr));
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f s (%.0f states/sec)\n", elapsed, 2249728.0 / elapsed);
    printf("Best QIII Chi2: %.2f | Mask: %d | Q4: [0, %d, %d, %d]\n",
           best_chi2_kr, best_m_kr, best_q4_kr[1], best_q4_kr[2], best_q4_kr[3]);
    
    // Print the decrypted text Z under best QIII key
    const int *best_q7 = q7_candidates[best_m_kr];
    char z_txt[N + 1];
    int cnt[26] = {0};
    for (int i = 0; i < N; i++) {
        int shift = (best_q4_kr[i % 4] + best_q7[i % 7]) % 26;
        int p_kr = (ct_kr[i] - shift + 26) % 26;
        z_txt[i] = k_to_std[p_kr] + 'A';
        cnt[k_to_std[p_kr]]++;
    }
    z_txt[N] = '\0';
    printf("Decrypted Z (len %d, IoC %.5f):\n%s\n", (int)strlen(z_txt), eval_ioc(cnt), z_txt);
    
    return 0;
}
