#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504
#define L 22

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
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

static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int ct_kr[N];
static int ct_std[N];

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

void init_ct() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_std[i] = PK10_CT[i] - 'A';
        ct_kr[i] = std_to_k[PK10_CT[i] - 'A'];
    }
}

static int8_t M0_inv[22][22];

void load_M0() {
    FILE *f = fopen("pk10_inv_matrices.bin", "rb");
    if (!f) { printf("Cannot open pk10_inv_matrices.bin\n"); exit(1); }
    fread(M0_inv, sizeof(int8_t), 22*22, f);
    fclose(f);
}

float score_pt(const int *pt_std, int len) {
    float sc = 0.0f;
    for (int i=0; i<len-3; i++) {
        sc += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return sc / (len - 3);
}

int main() {
    load_quads();
    init_ct();
    load_M0();
    printf("Models loaded. PK10 real length: %d\n", (int)strlen(PK10_CT));
    
    FILE *f = fopen("cribs_len22.txt", "r");
    if (!f) { printf("Cannot open cribs_len22.txt\n"); exit(1); }
    
    int max_cribs = 850000;
    char (*cribs)[24] = malloc(max_cribs * 24);
    int n_cribs = 0;
    while (fscanf(f, "%23s", cribs[n_cribs]) == 1) {
        if (strlen(cribs[n_cribs]) == 22) {
            n_cribs++;
            if (n_cribs >= max_cribs) break;
        }
    }
    fclose(f);
    printf("Loaded %d unique 22-char cribs.\n", n_cribs);
    
    double t0 = omp_get_wtime();
    
    #pragma omp parallel
    {
        int pt_std[N];
        int A[7], B[8], C[9];
        A[0] = 0; B[0] = 0;
        
        #pragma omp for schedule(dynamic, 1000)
        for (int i = 0; i < n_cribs; i++) {
            const char *cr = cribs[i];
            
            // Mode 1: Quagmire III (KRYPTOS alphabet, Vigenere)
            int y[22];
            for (int j = 0; j < 22; j++) {
                int c_val = ct_kr[j];
                int p_val = std_to_k[cr[j] - 'A'];
                y[j] = (c_val - p_val + 26) % 26;
            }
            int x[22];
            for (int r = 0; r < 22; r++) {
                int sum = 0;
                for (int c = 0; c < 22; c++) {
                    sum += M0_inv[r][c] * y[c];
                }
                x[r] = (sum % 26 + 26) % 26;
            }
            for (int j = 0; j < 6; j++) A[j+1] = x[j];
            for (int j = 0; j < 7; j++) B[j+1] = x[6 + j];
            for (int j = 0; j < 9; j++) C[j] = x[13 + j];
            
            for (int k = 22; k < 28; k++) {
                int keystream = (A[k % 7] + B[k % 8] + C[k % 9]) % 26;
                int p_kr = (ct_kr[k] - keystream + 26) % 26;
                pt_std[k] = k_to_std[p_kr];
            }
            for (int k = 0; k < 22; k++) pt_std[k] = cr[k] - 'A';
            float quick_sc = quad[pt_std[20]][pt_std[21]][pt_std[22]][pt_std[23]] +
                             quad[pt_std[21]][pt_std[22]][pt_std[23]][pt_std[24]] +
                             quad[pt_std[22]][pt_std[23]][pt_std[24]][pt_std[25]];
            if (quick_sc > -18.0f) {
                for (int k = 28; k < N; k++) {
                    int keystream = (A[k % 7] + B[k % 8] + C[k % 9]) % 26;
                    int p_kr = (ct_kr[k] - keystream + 26) % 26;
                    pt_std[k] = k_to_std[p_kr];
                }
                float full_sc = score_pt(pt_std, N);
                if (full_sc > -5.5f) {
                    #pragma omp critical
                    {
                        printf("\n*** HIGH SCORE PK10 (Quagmire III) Crib: %s | Quad=%.3f ***\n", cr, full_sc);
                        char full_txt[N+1];
                        for (int k=0; k<N; k++) full_txt[k] = pt_std[k] + 'A';
                        full_txt[N] = '\0';
                        printf("PT: %.100s...\n", full_txt);
                    }
                }
            }
            
            // Mode 2: Standard Alphabet Vigenere
            for (int j = 0; j < 22; j++) {
                int c_val = ct_std[j];
                int p_val = cr[j] - 'A';
                y[j] = (c_val - p_val + 26) % 26;
            }
            for (int r = 0; r < 22; r++) {
                int sum = 0;
                for (int c = 0; c < 22; c++) {
                    sum += M0_inv[r][c] * y[c];
                }
                x[r] = (sum % 26 + 26) % 26;
            }
            for (int j = 0; j < 6; j++) A[j+1] = x[j];
            for (int j = 0; j < 7; j++) B[j+1] = x[6 + j];
            for (int j = 0; j < 9; j++) C[j] = x[13 + j];
            
            for (int k = 22; k < 28; k++) {
                int keystream = (A[k % 7] + B[k % 8] + C[k % 9]) % 26;
                pt_std[k] = (ct_std[k] - keystream + 26) % 26;
            }
            quick_sc = quad[pt_std[20]][pt_std[21]][pt_std[22]][pt_std[23]] +
                       quad[pt_std[21]][pt_std[22]][pt_std[23]][pt_std[24]] +
                       quad[pt_std[22]][pt_std[23]][pt_std[24]][pt_std[25]];
            if (quick_sc > -18.0f) {
                for (int k = 28; k < N; k++) {
                    int keystream = (A[k % 7] + B[k % 8] + C[k % 9]) % 26;
                    pt_std[k] = (ct_std[k] - keystream + 26) % 26;
                }
                float full_sc = score_pt(pt_std, N);
                if (full_sc > -5.5f) {
                    #pragma omp critical
                    {
                        printf("\n*** HIGH SCORE PK10 (Standard Vig) Crib: %s | Quad=%.3f ***\n", cr, full_sc);
                        char full_txt[N+1];
                        for (int k=0; k<N; k++) full_txt[k] = pt_std[k] + 'A';
                        full_txt[N] = '\0';
                        printf("PT: %.100s...\n", full_txt);
                    }
                }
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Tested %d cribs at pos 0 on REAL PK10 in %.2f s (%.0f cribs/sec)\n", n_cribs, elapsed, n_cribs / elapsed);
    
    free(cribs);
    return 0;
}
