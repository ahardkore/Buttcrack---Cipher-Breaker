#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define CRIB_LEN 22

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

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

#include "a_inv_22.inc"

void init_tables() {
    for (int i=0; i<26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i=0; i<N; i++) {
        c_idx[i] = hpos[(unsigned char)PK10_CT[i]];
    }
}

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

int main() {
    load_quads();
    init_tables();
    printf("Models loaded. Tables initialized.\nReading cribs_len22.txt...\n");

    FILE *f = fopen("cribs_len22.txt", "r");
    if (!f) { printf("Cannot open cribs_len22.txt\n"); return 1; }

    char (*cribs)[24] = malloc(850000 * sizeof(*cribs));
    int num_cribs = 0;
    char line[64];
    while (fgets(line, sizeof(line), f)) {
        if (strlen(line) >= 22) {
            line[22] = '\0';
            int ok = 1;
            for (int k = 0; k < 22; k++) {
                if (line[k] < 'A' || line[k] > 'Z') { ok = 0; break; }
            }
            if (ok) {
                memcpy(cribs[num_cribs++], line, 23);
            }
        }
    }
    fclose(f);
    printf("Loaded %d valid 22-char cribs.\nTesting pure substitution at pos 0 on PK10...\n", num_cribs);

    float global_best_sc = -999.0f;
    char global_best_crib[24];
    int global_best_pt[N];

    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic, 1000)
    for (int idx = 0; idx < num_cribs; idx++) {
        const char *crib = cribs[idx];

        // Kryptos mode: c_idx[i] - p_idx
        int diff[CRIB_LEN];
        for (int i = 0; i < CRIB_LEN; i++) {
            int p_idx = hpos[(unsigned char)crib[i]];
            diff[i] = (c_idx[i] - p_idx + 26) % 26;
        }

        int vars[22];
        for (int r = 0; r < 22; r++) {
            int sum = 0;
            for (int c = 0; c < 22; c++) {
                sum += A_inv_22[r][c] * diff[c];
            }
            vars[r] = (sum % 26 + 26) % 26;
        }

        int q7[7], q8[8], q9[9];
        for (int i = 0; i < 7; i++) q7[i] = vars[i];
        for (int i = 0; i < 7; i++) q8[i] = vars[7 + i];
        q8[7] = 0;
        for (int i = 0; i < 8; i++) q9[i] = vars[14 + i];
        q9[8] = 0;

        // Early reject on next 24 chars
        int test_pt[24];
        for (int i = 0; i < 24; i++) {
            int pos = 22 + i;
            int k = (q7[pos % 7] + q8[pos % 8] + q9[pos % 9]) % 26;
            int p = (c_idx[pos] - k + 26) % 26;
            test_pt[i] = k_to_std[p];
        }
        float sc_early = score_text(test_pt, 24);
        if (sc_early < -6.0f) continue;

        // Full decrypt
        int pt[N];
        for (int i = 0; i < N; i++) {
            int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
            int p = (c_idx[i] - k + 26) % 26;
            pt[i] = k_to_std[p];
        }
        float sc_full = score_text(pt, N);

        #pragma omp critical
        {
            if (sc_full > global_best_sc) {
                global_best_sc = sc_full;
                strcpy(global_best_crib, crib);
                memcpy(global_best_pt, pt, sizeof(pt));

                char pt_str[N+1];
                for (int k = 0; k < N; k++) pt_str[k] = pt[k] + 'A';
                pt_str[N] = 0;

                printf(">>> HIT: Score %.4f | Crib: %s <<<\n", sc_full, crib);
                printf("  PT: %.100s...\n\n", pt_str);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Tested %d cribs in %.2f seconds.\n", num_cribs, elapsed);
    printf("Global Best Score: %.4f | Crib: %s\n", global_best_sc, global_best_crib);

    return 0;
}
