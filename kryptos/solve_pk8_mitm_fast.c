#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

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
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

int load_words(const char *filename, char words[][16], int max_w, int expected_len) {
    FILE *f = fopen(filename, "r");
    if (!f) return 0;
    char line[64];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_w) {
        line[strcspn(line, "\r\n")] = 0;
        if ((int)strlen(line) == expected_len) {
            strcpy(words[count++], line);
        }
    }
    fclose(f);
    return count;
}

static char w4[1000][16], w5[1000][16], w6[1000][16], w7[1000][16];
static unsigned char k45_arr[305000][20];
static int k45_src[305000][2]; // indices of w4, w5

int main() {
    load_quadgrams();
    int n4 = load_words("curated_w4.txt", w4, 1000, 4);
    int n5 = load_words("curated_w5.txt", w5, 1000, 5);
    int n6 = load_words("curated_w6.txt", w6, 1000, 6);
    int n7 = load_words("curated_w7.txt", w7, 1000, 7);
    int N = strlen(PK8_CT);

    printf("Loaded curated: w4=%d, w5=%d, w6=%d, w7=%d\n", n4, n5, n6, n7);

    for (int model = 0; model < 4; model++) {
        const char *alpha = (model < 2) ? KRYPTOS : STD;
        int is_beau = (model % 2 == 1);
        const char *mname = (model < 2) ? "KRYPTOS" : "STD";
        const char *mode = is_beau ? "Beaufort" : "Vigenere";

        int c_idx[200];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK8_CT[i]) - alpha;

        int i4[1000][4], i5[1000][5], i6[1000][6], i7[1000][7];
        for (int i = 0; i < n4; i++) for (int j = 0; j < 4; j++) i4[i][j] = strchr(alpha, w4[i][j]) - alpha;
        for (int i = 0; i < n5; i++) for (int j = 0; j < 5; j++) i5[i][j] = strchr(alpha, w5[i][j]) - alpha;
        for (int i = 0; i < n6; i++) for (int j = 0; j < 6; j++) i6[i][j] = strchr(alpha, w6[i][j]) - alpha;
        for (int i = 0; i < n7; i++) for (int j = 0; j < 7; j++) i7[i][j] = strchr(alpha, w7[i][j]) - alpha;

        // Precompute K45 table
        int n45 = 0;
        for (int x = 0; x < n4; x++) {
            for (int y = 0; y < n5; y++) {
                for (int j = 0; j < 20; j++) {
                    k45_arr[n45][j] = (i4[x][j % 4] + i5[y][j % 5]) % 26;
                }
                k45_src[n45][0] = x;
                k45_src[n45][1] = y;
                n45++;
            }
        }

        printf("[%s %s] Precomputed %d K45 vectors. Scanning %d (w6, w7) pairs...\n",
               mname, mode, n45, n6 * n7);

        #pragma omp parallel for schedule(dynamic)
        for (int a = 0; a < n6; a++) {
            for (int b = 0; b < n7; b++) {
                int k67[42];
                for (int j = 0; j < 42; j++) k67[j] = (i6[a][j % 6] + i7[b][j % 7]) % 26;

                // Coincidence test mod 20
                int counts[20][26] = {0};
                int c_prime[200];
                for (int j = 0; j < N; j++) {
                    int cp = is_beau ? ((k67[j % 42] - c_idx[j] + 26) % 26) : ((c_idx[j] - k67[j % 42] + 26) % 26);
                    c_prime[j] = cp;
                    counts[j % 20][cp]++;
                }

                int coinc = 0;
                for (int r = 0; r < 20; r++)
                    for (int c = 0; c < 26; c++)
                        coinc += counts[r][c] * (counts[r][c] - 1) / 2;

                if (coinc < 30) continue;

                // Test all K45 vectors
                for (int idx45 = 0; idx45 < n45; idx45++) {
                    const unsigned char *k45 = k45_arr[idx45];

                    // Quick test: first 8 chars (5 quadgrams)
                    int p0 = alpha_to_std[is_beau ? ((k45[0] - c_prime[0] + 26) % 26) : ((c_prime[0] - k45[0] + 26) % 26)];
                    int p1 = alpha_to_std[is_beau ? ((k45[1] - c_prime[1] + 26) % 26) : ((c_prime[1] - k45[1] + 26) % 26)];
                    int p2 = alpha_to_std[is_beau ? ((k45[2] - c_prime[2] + 26) % 26) : ((c_prime[2] - k45[2] + 26) % 26)];
                    int p3 = alpha_to_std[is_beau ? ((k45[3] - c_prime[3] + 26) % 26) : ((c_prime[3] - k45[3] + 26) % 26)];
                    
                    float sc5 = quad[p0][p1][p2][p3];
                    if (sc5 < -6.5f) continue;

                    int p4 = alpha_to_std[is_beau ? ((k45[4] - c_prime[4] + 26) % 26) : ((c_prime[4] - k45[4] + 26) % 26)];
                    sc5 += quad[p1][p2][p3][p4];
                    int p5 = alpha_to_std[is_beau ? ((k45[5] - c_prime[5] + 26) % 26) : ((c_prime[5] - k45[5] + 26) % 26)];
                    sc5 += quad[p2][p3][p4][p5];
                    int p6 = alpha_to_std[is_beau ? ((k45[6] - c_prime[6] + 26) % 26) : ((c_prime[6] - k45[6] + 26) % 26)];
                    sc5 += quad[p3][p4][p5][p6];
                    int p7 = alpha_to_std[is_beau ? ((k45[7] - c_prime[7] + 26) % 26) : ((c_prime[7] - k45[7] + 26) % 26)];
                    sc5 += quad[p4][p5][p6][p7];

                    if (sc5 < -28.0f) continue;

                    // Decrypt 16 chars
                    int pt[16];
                    pt[0]=p0; pt[1]=p1; pt[2]=p2; pt[3]=p3; pt[4]=p4; pt[5]=p5; pt[6]=p6; pt[7]=p7;
                    for (int j = 8; j < 16; j++) {
                        pt[j] = alpha_to_std[is_beau ? ((k45[j] - c_prime[j] + 26) % 26) : ((c_prime[j] - k45[j] + 26) % 26)];
                    }
                    float sc16 = sc5;
                    for (int j = 5; j < 13; j++) {
                        sc16 += quad[pt[j]][pt[j+1]][pt[j+2]][pt[j+3]];
                    }
                    if (sc16 < -68.0f) continue;

                    // Full decrypt of all N chars
                    int pt_full[200];
                    for (int j = 0; j < 16; j++) pt_full[j] = pt[j];
                    for (int j = 16; j < N; j++) {
                        pt_full[j] = alpha_to_std[is_beau ? ((k45[j % 20] - c_prime[j] + 26) % 26) : ((c_prime[j] - k45[j % 20] + 26) % 26)];
                    }
                    float full_sc = 0;
                    for (int j = 0; j < N - 3; j++) {
                        full_sc += quad[pt_full[j]][pt_full[j+1]][pt_full[j+2]][pt_full[j+3]];
                    }
                    full_sc /= (N - 3);

                    if (full_sc > -5.5f) {
                        int x = k45_src[idx45][0];
                        int y = k45_src[idx45][1];
                        printf("\n*** MATCH FOUND! [%s %s] sc=%6.4f ***\n", mname, mode, full_sc);
                        printf("Keys: w4=%s w5=%s w6=%s w7=%s\nPlaintext: ", w4[x], w5[y], w6[a], w7[b]);
                        for (int j = 0; j < N; j++) printf("%c", 'A' + pt_full[j]);
                        printf("\n\n");
                    }
                }
            }
        }
    }
    printf("Scan complete.\n");
    return 0;
}
