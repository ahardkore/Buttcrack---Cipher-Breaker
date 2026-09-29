#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char q[16]; float cnt;
    double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int ct_kr[N];
static int k_to_std[26];
static int std_to_k[26];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_kr[i] = std_to_k[PK10_CT[i] - 'A'];
    }
}

float score_text(const char *t) {
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    return sc / (N - 3);
}

void test_grid_sa(int W, int H) {
    printf("\nTesting %d x %d grid on PK10 with Simulated Annealing (10,000 restarts)...\n", W, H);
    
    // Sub-clock Q7 from PK9
    const int q7[7] = {5, 5, 8, 7, 16, 10, 22};
    
    // Decrypt ct with Q7 first
    char z[N];
    for (int i=0; i<N; i++) {
        int p_kr = (ct_kr[i] - q7[i % 7] + 26) % 26;
        z[i] = k_to_std[p_kr] + 'A';
    }
    
    double t0 = omp_get_wtime();
    float global_best_sc = -999.0f;
    char global_best_pt[N+1];
    int global_best_perm[W];
    
    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 777;
        float local_best_sc = -999.0f;
        char local_best_pt[N+1];
        int local_perm[W];
        
        char cur_pt[N+1];
        int cur_perm[W];
        
        #pragma omp for schedule(dynamic)
        for (int restart = 0; restart < 10000; restart++) {
            for (int i=0; i<W; i++) cur_perm[i] = i;
            for (int i=W-1; i>0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int t = cur_perm[i]; cur_perm[i] = cur_perm[j]; cur_perm[j] = t;
            }
            
            // Build text: matrix of W columns, H rows
            int idx = 0;
            for (int r=0; r<H; r++) {
                for (int c=0; c<W; c++) {
                    cur_pt[idx++] = z[cur_perm[c] * H + r];
                }
            }
            cur_pt[N] = '\0';
            float cur_sc = score_text(cur_pt);
            
            float temp = 0.4f;
            float cooling = 0.98f;
            
            for (int step = 0; step < 400; step++) {
                temp *= cooling;
                int next_perm[W];
                memcpy(next_perm, cur_perm, sizeof(next_perm));
                
                int a = rand_r(&seed) % W;
                int b = rand_r(&seed) % W;
                int t = next_perm[a]; next_perm[a] = next_perm[b]; next_perm[b] = t;
                
                char next_pt[N+1];
                idx = 0;
                for (int r=0; r<H; r++) {
                    for (int c=0; c<W; c++) {
                        next_pt[idx++] = z[next_perm[c] * H + r];
                    }
                }
                next_pt[N] = '\0';
                float next_sc = score_text(next_pt);
                float delta = next_sc - cur_sc;
                
                if (delta > 0 || (temp > 1e-4f && expf(delta / temp) > ((float)rand_r(&seed) / (float)RAND_MAX))) {
                    cur_sc = next_sc;
                    memcpy(cur_perm, next_perm, sizeof(cur_perm));
                    strcpy(cur_pt, next_pt);
                    
                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        strcpy(local_best_pt, cur_pt);
                        memcpy(local_perm, cur_perm, sizeof(local_perm));
                    }
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_pt, local_best_pt);
                memcpy(global_best_perm, local_perm, sizeof(global_best_perm));
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s. Global Best Quad: %.4f\n", elapsed, global_best_sc);
    printf("Perm: [");
    for (int i=0; i<W; i++) printf("%d%s", global_best_perm[i], i==W-1?"":", ");
    printf("]\n");
    printf("Sample PT: %.60s...\n", global_best_pt);
}

int main() {
    load_quads();
    init();
    test_grid_sa(21, 24);
    test_grid_sa(24, 21);
    test_grid_sa(14, 36);
    return 0;
}
