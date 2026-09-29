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

static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int ct_kr[N];
static int ct_std[N];
static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];
static int8_t M_inv[483][22][22];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_std[i] = PK10_CT[i] - 'A';
        ct_kr[i] = std_to_k[PK10_CT[i] - 'A'];
    }
    FILE *f = fopen("pk10_inv_matrices.bin", "rb");
    if (f) {
        fread(M_inv, sizeof(int8_t), 483 * 22 * 22, f);
        fclose(f);
    }
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
    init();
    
    // Load top 10,000 cribs from cribs_len22.txt
    FILE *f = fopen("cribs_len22.txt", "r");
    if (!f) return 1;
    int max_cribs = 10000;
    char (*cribs)[24] = malloc(max_cribs * 24);
    int n_cribs = 0;
    while (fscanf(f, "%23s", cribs[n_cribs]) == 1 && n_cribs < max_cribs) {
        if (strlen(cribs[n_cribs]) == 22) n_cribs++;
    }
    fclose(f);
    printf("Loaded %d candidate cribs. Testing across all 483 start positions...\n", n_cribs);
    
    double t0 = omp_get_wtime();
    int hits = 0;
    
    #pragma omp parallel reduction(+:hits)
    {
        int pt_std[N];
        int A[7], B[8], C[9];
        A[0] = 0; B[0] = 0;
        
        #pragma omp for schedule(dynamic, 100)
        for (int i = 0; i < n_cribs; i++) {
            const char *cr = cribs[i];
            
            for (int pos = 0; pos <= N - L; pos++) {
                // Mode 1: Quagmire III
                int y[22];
                for (int j = 0; j < 22; j++) {
                    int c_val = ct_kr[pos + j];
                    int p_val = std_to_k[cr[j] - 'A'];
                    y[j] = (c_val - p_val + 26) % 26;
                }
                int x[22];
                for (int r = 0; r < 22; r++) {
                    int sum = 0;
                    const int8_t *row = M_inv[pos][r];
                    for (int c = 0; c < 22; c++) sum += row[c] * y[c];
                    x[r] = (sum % 26 + 26) % 26;
                }
                for (int j = 0; j < 6; j++) A[j+1] = x[j];
                for (int j = 0; j < 7; j++) B[j+1] = x[6 + j];
                for (int j = 0; j < 9; j++) C[j] = x[13 + j];
                
                // Quick validation: check 4 characters immediately outside the crib window
                int check_pos = (pos + 22 < N - 4) ? (pos + 22) : (pos - 4);
                if (check_pos >= 0 && check_pos + 3 < N) {
                    int q0 = k_to_std[(ct_kr[check_pos] - (A[check_pos % 7] + B[check_pos % 8] + C[check_pos % 9]) + 52) % 26];
                    int q1 = k_to_std[(ct_kr[check_pos+1] - (A[(check_pos+1) % 7] + B[(check_pos+1) % 8] + C[(check_pos+1) % 9]) + 52) % 26];
                    int q2 = k_to_std[(ct_kr[check_pos+2] - (A[(check_pos+2) % 7] + B[(check_pos+2) % 8] + C[(check_pos+2) % 9]) + 52) % 26];
                    int q3 = k_to_std[(ct_kr[check_pos+3] - (A[(check_pos+3) % 7] + B[(check_pos+3) % 8] + C[(check_pos+3) % 9]) + 52) % 26];
                    
                    if (quad[q0][q1][q2][q3] > -6.0f) {
                        // Candidate passed quick check, score full text
                        for (int k = 0; k < N; k++) {
                            int keystream = (A[k % 7] + B[k % 8] + C[k % 9]) % 26;
                            pt_std[k] = k_to_std[(ct_kr[k] - keystream + 26) % 26];
                        }
                        float full_sc = score_pt(pt_std, N);
                        if (full_sc > -5.2f) {
                            hits++;
                            #pragma omp critical
                            {
                                printf("\n*** HIT! Pos=%d | Crib=%s | Quad=%.3f ***\n", pos, cr, full_sc);
                                char full_txt[N+1];
                                for (int k=0; k<N; k++) full_txt[k] = pt_std[k] + 'A';
                                full_txt[N] = '\0';
                                printf("PT: %.100s...\n", full_txt);
                            }
                        }
                    }
                }
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Evaluated %d cribs x 483 positions = %lld checks in %.2f s (%.0f checks/sec)\n",
           n_cribs, (long long)n_cribs * 483, elapsed, ((double)n_cribs * 483) / elapsed);
    
    free(cribs);
    return 0;
}
