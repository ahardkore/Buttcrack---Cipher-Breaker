#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 153
#define VARS 22

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];

static void load_quads(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) return;
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        char q[5]; float sc;
        if (sscanf(buf, "%4s %f", q, &sc) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qtable[a][b][c][d] = sc;
                valid_q[a][b][c][d] = 1;
            }
        }
    }
    fclose(f);
}

static int solve_linear_mod_p(int p, int M, const int A_in[][VARS], const int b_in[], int x_out[VARS]) {
    int A[M][VARS];
    int b[M];
    for (int i = 0; i < M; i++) {
        b[i] = (b_in[i] % p + p) % p;
        for (int j = 0; j < VARS; j++) {
            A[i][j] = (A_in[i][j] % p + p) % p;
        }
    }

    int r = 0;
    int pivot_col[VARS];
    for (int j = 0; j < VARS; j++) pivot_col[j] = -1;

    for (int c = 0; c < VARS && r < M; c++) {
        int sel = -1;
        for (int i = r; i < M; i++) {
            if (A[i][c] % p != 0) { sel = i; break; }
        }
        if (sel == -1) continue;

        for (int j = 0; j < VARS; j++) { int t = A[r][j]; A[r][j] = A[sel][j]; A[sel][j] = t; }
        int tb = b[r]; b[r] = b[sel]; b[sel] = tb;

        int inv = 1;
        for (int k = 1; k < p; k++) {
            if ((A[r][c] * k) % p == 1) { inv = k; break; }
        }
        for (int j = 0; j < VARS; j++) A[r][j] = (A[r][j] * inv) % p;
        b[r] = (b[r] * inv) % p;

        pivot_col[c] = r;

        for (int i = 0; i < M; i++) {
            if (i != r && A[i][c] != 0) {
                int factor = A[i][c];
                for (int j = 0; j < VARS; j++) {
                    A[i][j] = (A[i][j] - factor * A[r][j]) % p;
                    if (A[i][j] < 0) A[i][j] += p;
                }
                b[i] = (b[i] - factor * b[r]) % p;
                if (b[i] < 0) b[i] += p;
            }
        }
        r++;
    }

    for (int i = r; i < M; i++) {
        if (b[i] != 0) return 0;
    }

    for (int j = 0; j < VARS; j++) x_out[j] = 0;
    for (int c = 0; c < VARS; c++) {
        int pr = pivot_col[c];
        if (pr != -1) {
            x_out[c] = b[pr];
        }
    }
    return 1;
}

static int solve_linear_mod_26(int M, const int A[][VARS], const int b[], int x_out[VARS]) {
    int x2[VARS], x13[VARS];
    if (!solve_linear_mod_p(2, M, A, b, x2)) return 0;
    if (!solve_linear_mod_p(13, M, A, b, x13)) return 0;

    for (int j = 0; j < VARS; j++) {
        int diff = (x2[j] - (x13[j] % 2) + 2) % 2;
        x_out[j] = (x13[j] + 13 * diff) % 26;
    }
    return 1;
}

static float eval_pt(const char *pt, int len, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    int n_q = len - 3;
    for (int i = 0; i < n_q; i++) {
        int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
        sc += qtable[a][b][c][d];
        if (!valid_q[a][b][c][d]) def++;
    }
    *out_def = def;
    return sc / (float)n_q;
}

int main(void) {
    load_quads();

    const char *narratives[] = {
        "AFTERNINEDAYSINTHEFLAMETHESTEELWASREADYHEDREWTHEGLOWINGMETALFROMTHEHEARTHANDPLACEDITUPONTHEANVILTOBEFORGEDINTOAFINENEEDLE",
        "FORNINEDAYSIPUMPEDTHEBELLOWSANDTENDEDTHECOALSUNTILTHEWHITEHEATPURIFIEDTHEIRONPIECEHETOOKUPHISHAMMERANDBEGANTOFORGETHENEEDLE",
        "ONTHETENTHDAYHEDREWTHESTEELFROMTHEWHITECOALSWITHHISLONGTONGSANDSTRUCKITWITHHISHAMMERDRAWINGITOUTINTOASLENDERWIRE",
        "HEDREWTHEPURIFIEDSTEELTHROUGHTHEDRAWPLATEHOLEBYHOLEUNTILITWASASFINEASAHAIRTHENFLATTENEDTHEHEADANDPUNCHEDTHEEYE",
        "WITHASLENDERPUNCHHEPIERCEDTHEEYEOFTHENEEDLEANDFILEDTHEEDGESSMOOTHBEFORETEMPERINGTHEPOINTINOILTOHARDENTHESTEEL",
        "HEQUENCHEDTHEREDHOTNEEDLEINWATERANDHELDITTOTHELIGHTANEEDLEOFMYOWNMAKINGFINEENOUGHTOREADANYKNOTINPELLEGRINSARCHIVE",
        "ATLASTIHELDTHENEEDLEOFMYOWNMAKINGINMYHANDTHERESIDUEOFTENYEARSOFSTUDYANDPRACTICEINTHEWHITESMITHSWORKSHOP",
        "HESMILEDANDHANDEDMETHEFINISHEDNEEDLESAYINGTHATNOWIWASREADYTOUNRAVELTHETWELVEKNOTSOFPELLEGRINANDFINDTHELOSTARCHIVE",
        "NOWHESAIDTAKEUPTHENEEDLEOFYOUROWNMAKINGANDGOTOTHEFOOTOFTHESWISSALPSWHERETHEARCHIVEOFPELLEGRINLIESCONCEALED",
        "THEWORKOFMAKINGTHENEEDLEWASCOMPLETEDAFTERNINEDAYSINTHEFLAMEANDTENYEARSATTHEANVILOFTHEOLDMASTERWHITESMITH",
        "ATLASTTHEFIREWASLITANDTHEBELLOWSSANGAS",
        "HEHELDTHESTEELINTOCOALSTHATGLOWEDWHITE",
        "ONEMOMENTOFTEMPERINGCANDESTROYYEARSOFLABOUR",
        "ONLYANIRONPIECEPURIFIEDNINEDAYSINTHEFLAME",
        "THEWHITESMITHTOOKUPHISHAMMERANDBEGANTOFORGE",
        "HEDREWTHEGLOWINGSTEELFROMTHEWHITECOALS",
        "THENINEDAYSOFPURIFICATIONBEINGACCOMPLISHED",
        "HEPLACEDTHEGLOWINGRODUPONTHEANVILANDSTRUCK"
    };

    int n_narr = sizeof(narratives) / sizeof(narratives[0]);
    int L_crib = 24; // test window length 24
    int tests_count = 0;

    printf("Scanning candidate narrative continuations across PK8 positions...\n");

    for (int n_idx = 0; n_idx < n_narr; n_idx++) {
        const char *narr = narratives[n_idx];
        int narr_len = strlen(narr);
        if (narr_len < L_crib) continue;

        for (int p_start = 0; p_start <= narr_len - L_crib; p_start += 2) {
            char crib[L_crib + 1];
            memcpy(crib, narr + p_start, L_crib);
            crib[L_crib] = '\0';

            // Test this crib at various start positions in PK8
            for (int pk_pos = 0; pk_pos <= N - L_crib; pk_pos += 2) {
                int A[L_crib][VARS];
                int b[L_crib];
                memset(A, 0, sizeof(A));

                for (int i = 0; i < L_crib; i++) {
                    int pos = pk_pos + i;
                    int ct_idx = strchr(KRYPTOS, PK8_CT[pos]) - KRYPTOS;
                    int pt_idx = strchr(KRYPTOS, crib[i]) - KRYPTOS;
                    b[i] = (ct_idx - pt_idx + 26) % 26;

                    A[i][pos % 4] = 1;
                    A[i][4 + (pos % 5)] = 1;
                    A[i][9 + (pos % 6)] = 1;
                    A[i][15 + (pos % 7)] = 1;
                }

                int x[VARS];
                tests_count++;
                if (solve_linear_mod_26(L_crib, A, b, x)) {
                    // Decrypt entire 153 chars
                    char pt[N + 1];
                    for (int i = 0; i < N; i++) {
                        int ct_idx = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;
                        int shift = (x[i % 4] + x[4 + (i % 5)] + x[9 + (i % 6)] + x[15 + (i % 7)]) % 26;
                        int p_idx = (ct_idx - shift + 26) % 26;
                        pt[i] = KRYPTOS[p_idx];
                    }
                    pt[N] = '\0';

                    int def; float sc = eval_pt(pt, N, &def);
                    if (def < 50) {
                        printf("\n>>> CANDIDATE HIT! <<<\n");
                        printf("Crib: %s at PK8 pos %d\n", crib, pk_pos);
                        printf("Score: %.4f | Defects: %d / 150 (%.1f%% valid)\n",
                               sc, def, (150 - def)/150.0f * 100.0f);
                        printf("Plaintext: %s\n", pt);
                    }
                }
            }
        }
    }

    printf("Total window alignments tested: %d\n", tests_count);
    return 0;
}
