#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

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

static const int A_inv[18][18] = {
    {25, 24, 23, 22, 22, 21, 22, 23, 25, 1, 3, 4, 5, 5, 4, 3, 2, 1},
    {25, 24, 23, 22, 22, 22, 23, 24, 0, 2, 3, 4, 4, 4, 3, 2, 1, 1},
    {25, 25, 25, 25, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
    {24, 22, 20, 18, 17, 17, 19, 22, 0, 4, 7, 9, 9, 8, 6, 4, 2, 1},
    {1, 1, 2, 2, 2, 2, 1, 0, 25, 24, 24, 24, 24, 25, 25, 0, 0, 0},
    {1, 2, 3, 4, 4, 4, 3, 1, 25, 23, 22, 22, 22, 23, 24, 25, 0, 0},
    {1, 2, 4, 5, 6, 6, 5, 3, 0, 23, 21, 20, 20, 21, 22, 24, 25, 0},
    {1, 2, 4, 6, 7, 8, 7, 5, 2, 24, 21, 19, 18, 19, 20, 22, 24, 25},
    {0, 25, 24, 23, 22, 22, 23, 24, 0, 2, 3, 4, 4, 3, 2, 1, 0, 0},
    {0, 0, 25, 24, 23, 22, 22, 23, 24, 0, 2, 3, 4, 4, 3, 2, 1, 0},
    {0, 25, 24, 22, 20, 19, 19, 20, 23, 0, 3, 6, 7, 7, 6, 4, 2, 1},
    {1, 2, 3, 4, 4, 3, 2, 0, 24, 23, 22, 22, 23, 24, 25, 0, 0, 0},
    {1, 2, 3, 5, 6, 7, 6, 5, 2, 25, 22, 20, 19, 19, 21, 22, 24, 25},
    {0, 1, 1, 2, 3, 4, 4, 4, 3, 1, 25, 23, 22, 21, 22, 23, 24, 25},
    {0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 1, 0, 25, 24, 24, 24, 25, 25},
    {0, 0, 25, 25, 24, 24, 24, 25, 0, 1, 2, 2, 2, 1, 1, 0, 0, 0},
    {1, 2, 3, 4, 5, 5, 4, 3, 1, 25, 23, 22, 21, 21, 22, 23, 24, 25},
    {0, 1, 1, 2, 2, 3, 2, 2, 1, 0, 25, 24, 24, 23, 24, 24, 25, 25}
};

static const char *cribs[] = {
    "PUNCHEDBEFORETEMPERING", "BEFORETEMPERINGHEWILL", "THEEYEOFANEEDLEMUSTBE",
    "EYEOFANEEDLEMUSTBEPUNCHED", "ADIEFORDRAWINGWIRE", "DRAWINGWIRETHROUGHTHEDIE",
    "THROUGHTHEOPENINGSOF", "INWHICHWIRESAREDRAWN", "SOTHATITMAYHAVEALONG",
    "THREADINSCRIBEDWITH", "INSCRIBEDWITHLETTERS", "FORMTHELETTERSWITHTHE",
    "SLENDERFORCEPSANDLAY", "ANDLAYTHEMINTHEHOLLOWS", "BEATINGABOVETHEMWITH",
    "WITHTHEHAMMERFILLTHEM", "THICKSILVERWIREBEING", "WHENITHASBEGUNTOGLOW",
    "ITISQUENCHEDINWATER", "EXTINGUISHITEQUALLY", "EQUALLYINWATERANDTAKING",
    "DRYITSLIGHTLYOVERTHE", "OVERTHEFIREYOUWILLIN", "TEMPERALLTHINGSWHICH",
    "WHICHAREMADEOFSTEEL", "PUTTHESILVERINTOONE", "OFTHESMALLCRUCIBLES",
    "WHENITISLIQUEFIEDTHROW", "ALITTLESALTUPONITAND", "POURITINTOTHEROUNDMOULD",
    "ROUNDMOULDWHICHISMADE", "WARMOVERTHEFIREANDIN", "WHICHTHEREISMELTEDWAX",
    "ROGEROFHELMARSHAUSEN", "STUDYUNDERHIMFORTENYEARS", "HEWILLLETMETAKEONEOF",
    "TAKEONEOFMYOWNMAKING", "WORKCOULDONLYBEGINWHEN", "FIREACHEDITSPROPERHEAT",
    "BLOWUPONTHECOALSUNTIL", "UNTILTHEYGLOWEDWHITE", "THEBELLOWSSANGASCOALS",
    "THECOALSTURNEDWHITE", "BEATINGITUPONTHEANVIL", "WITHTHESHORTMALLET",
    "WITHTHESLENDERFORCEPS", "HEPLACEDTHECRUCIBLE", "HETOOKUPTHETONGSAND"
};
static int num_cribs = sizeof(cribs) / sizeof(cribs[0]);

int main() {
    load_quadgrams();
    int N = strlen(PK8_CT);
    printf("Dragging %d technical artisan cribs across all positions of PK8...\n", num_cribs);

    for (int c_idx_crib = 0; c_idx_crib < num_cribs; c_idx_crib++) {
        const char *crib = cribs[c_idx_crib];
        int crib_len = strlen(crib);
        if (crib_len < 18) continue;

        for (int model = 0; model < 4; model++) {
            const char *alpha = (model < 2) ? KRYPTOS : STD;
            int is_beau = (model % 2 == 1);
            const char *mname = (model < 2) ? "KRYPTOS" : "STD";
            const char *mode = is_beau ? "Beaufort" : "Vigenere";

            int c_idx[160];
            int alpha_to_std[26];
            for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
            for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK8_CT[i]) - alpha;

            int p_idx[64];
            for (int i = 0; i < crib_len; i++) p_idx[i] = strchr(alpha, crib[i]) - alpha;

            for (int j = 0; j <= N - 18; j++) {
                int k_window[18];
                for (int i = 0; i < 18; i++) {
                    k_window[i] = is_beau ? ((p_idx[i] + c_idx[j + i]) % 26) : ((c_idx[j + i] - p_idx[i] + 26) % 26);
                }

                int q_prime[18];
                for (int r = 0; r < 18; r++) {
                    int sum = 0;
                    for (int c = 0; c < 18; c++) sum += A_inv[r][c] * k_window[c];
                    q_prime[r] = sum % 26;
                }

                int qp4[4] = {q_prime[0], q_prime[1], q_prime[2], q_prime[3]};
                int qp5[5] = {q_prime[4], q_prime[5], q_prime[6], q_prime[7], 0};
                int qp6[6] = {q_prime[8], q_prime[9], q_prime[10], q_prime[11], 0, 0};
                int qp7[7] = {q_prime[12], q_prime[13], q_prime[14], q_prime[15], q_prime[16], q_prime[17], 0};

                // Decrypt all 153 characters
                int pt_full[160];
                for (int k = 0; k < N; k++) {
                    int d = k - j;
                    int shift = (qp4[((d % 4) + 4) % 4] +
                                 qp5[((d % 5) + 5) % 5] +
                                 qp6[((d % 6) + 6) % 6] +
                                 qp7[((d % 7) + 7) % 7]) % 26;
                    int p = is_beau ? ((shift - c_idx[k] + 26) % 26) : ((c_idx[k] - shift + 26) % 26);
                    pt_full[k] = alpha_to_std[p];
                }

                float sc = 0;
                for (int k = 0; k < N - 3; k++) {
                    sc += quad[pt_full[k]][pt_full[k+1]][pt_full[k+2]][pt_full[k+3]];
                }
                sc /= (N - 3);

                if (sc > -5.2f) {
                    printf("  HIT! [%s %s pos %d] sc=%6.4f | %s | ",
                           mname, mode, j, sc, crib);
                    for (int k = 0; k < 60; k++) printf("%c", 'A' + pt_full[k]);
                    printf("\n");
                }
            }
        }
    }
    printf("Drag test complete.\n");
    return 0;
}
