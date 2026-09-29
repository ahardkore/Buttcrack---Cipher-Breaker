#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <omp.h>

#define N 504
#define CRIB_LEN 22
#define NUM_POS (N - CRIB_LEN)

static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int hpos[256];
static int k_to_std[26];
static unsigned char A_inv_all[NUM_POS][22][22];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = hpos[(unsigned char)PK10_CT[i]];
    }
    FILE *f = fopen("a_inv_all.bin", "rb");
    if (!f) { printf("Cannot open a_inv_all.bin\n"); exit(1); }
    fread(A_inv_all, 1, sizeof(A_inv_all), f);
    fclose(f);
}

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

float test_crib_at_pos(int pos, const char *crib, char *full_pt_out) {
    int diff[CRIB_LEN];
    for (int i = 0; i < CRIB_LEN; i++) {
        int p_idx = hpos[(unsigned char)crib[i]];
        diff[i] = (c_idx[pos + i] - p_idx + 26) % 26;
    }

    int vars[22];
    for (int r = 0; r < 22; r++) {
        int sum = 0;
        for (int c = 0; c < 22; c++) {
            sum += A_inv_all[pos][r][c] * diff[c];
        }
        vars[r] = sum % 26;
    }

    int q7[7], q8[8], q9[9];
    for (int i = 0; i < 7; i++) q7[i] = vars[i];
    for (int i = 0; i < 7; i++) q8[i] = vars[7 + i];
    q8[7] = 0;
    for (int i = 0; i < 8; i++) q9[i] = vars[14 + i];
    q9[8] = 0;

    // Fast check: score 20 characters before or after the crib
    int check_start = (pos + 22 + 20 <= N) ? (pos + 22) : (pos >= 20 ? pos - 20 : 0);
    int test_pt[20];
    for (int i = 0; i < 20; i++) {
        int idx = check_start + i;
        int k = (q7[idx % 7] + q8[idx % 8] + q9[idx % 9]) % 26;
        int p = (c_idx[idx] - k + 26) % 26;
        test_pt[i] = k_to_std[p];
    }
    float sc_early = score_text(test_pt, 20);
    if (sc_early < -6.5f) return sc_early;

    // Full decrypt if early check passes
    int pt[N];
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        pt[i] = k_to_std[p];
    }
    float sc_full = score_text(pt, N);
    if (full_pt_out) {
        for (int i = 0; i < N; i++) full_pt_out[i] = 'A' + pt[i];
        full_pt_out[N] = '\0';
    }
    return sc_full;
}

int main() {
    load_quadgrams();
    init_tables();

    // Load narrative cribs
    FILE *f = fopen("pk10_narrative_cribs.txt", "r");
    if (!f) { printf("Cannot open pk10_narrative_cribs.txt\n"); return 1; }
    char cribs[5000][32];
    int num_cribs = 0;
    char line[64];
    while (fgets(line, sizeof(line), f) && num_cribs < 5000) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 22) {
            strcpy(cribs[num_cribs++], w);
        }
    }
    fclose(f);
    printf("Loaded %d narrative cribs.\n", num_cribs);

    printf("Dragging all %d cribs across all %d positions on PK10 (%d total evaluations)...\n",
           num_cribs, NUM_POS, num_cribs * NUM_POS);

    float global_best_sc = -999.0f;
    int global_best_pos = 0;
    char global_best_crib[32] = "";
    char global_best_pt[N+1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        int local_best_pos = 0;
        char local_best_crib[32] = "";
        char local_best_pt[N+1] = "";

        #pragma omp for schedule(dynamic, 10)
        for (int c_idx_iter = 0; c_idx_iter < num_cribs; c_idx_iter++) {
            const char *crib = cribs[c_idx_iter];
            for (int pos = 0; pos < NUM_POS; pos++) {
                char pt[N+1];
                float sc = test_crib_at_pos(pos, crib, pt);
                if (sc > -6.0f) {
                    #pragma omp critical
                    {
                        printf("HIT! Pos %d | Score %.4f | Crib: %s\n", pos, sc, crib);
                        printf("PT: %.80s\n", pt);
                    }
                }
                if (sc > local_best_sc) {
                    local_best_sc = sc;
                    local_best_pos = pos;
                    strcpy(local_best_crib, crib);
                    strcpy(local_best_pt, pt);
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                global_best_pos = local_best_pos;
                strcpy(global_best_crib, local_best_crib);
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s (%.1f checks/sec)\n", elapsed, (num_cribs * NUM_POS) / elapsed);
    printf("Best Score: %.4f at Pos %d | Crib: %s\n", global_best_sc, global_best_pos, global_best_crib);
    printf("PT (first 100): %.100s...\n", global_best_pt);

    return 0;
}
