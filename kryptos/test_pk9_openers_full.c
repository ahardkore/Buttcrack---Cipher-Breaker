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
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

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

static const char *test_hits[] = {
    "MYMASTERPOUREDTHEM",
    "THEOLDMANCASTTHEIR",
    "HETOLDMETOTAKETHEC",
    "GENTLYHEPUTTHEWORK",
    "HETOLDMETOFETCHEDA",
    "FIRSTHEHEATEDTHELO"
};

int main() {
    load_quadgrams();
    int N = strlen(PK9_CT);

    for (int h = 0; h < 6; h++) {
        const char *line = test_hits[h];
        for (int model = 0; model < 4; model++) {
            const char *alpha = (model < 2) ? KRYPTOS : STD;
            int is_beau = (model % 2 == 1);

            int c_idx[144];
            int alpha_to_std[26];
            for (int i=0; i<26; i++) alpha_to_std[i] = alpha[i] - 'A';
            for (int i=0; i<N; i++) c_idx[i] = strchr(alpha, PK9_CT[i]) - alpha;

            int p_idx[18];
            for (int i=0; i<18; i++) p_idx[i] = strchr(alpha, line[i]) - alpha;

            int k_win[18];
            for (int i=0; i<18; i++) {
                k_win[i] = is_beau ? ((p_idx[i] + c_idx[i]) % 26) : ((c_idx[i] - p_idx[i] + 26) % 26);
            }

            int q[18];
            for (int r=0; r<18; r++) {
                int sum = 0;
                for (int c=0; c<18; c++) sum += A_inv[r][c] * k_win[c];
                q[r] = sum % 26;
            }

            int q4[4] = {q[0], q[1], q[2], q[3]};
            int q5[5] = {q[4], q[5], q[6], q[7], 0};
            int q6[6] = {q[8], q[9], q[10], q[11], 0, 0};
            int q7[7] = {q[12], q[13], q[14], q[15], q[16], q[17], 0};

            int pt[144];
            for (int i=0; i<N; i++) {
                int shift = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                int p = is_beau ? ((shift - c_idx[i] + 26) % 26) : ((c_idx[i] - shift + 26) % 26);
                pt[i] = alpha_to_std[p];
            }

            float full_sc = 0;
            for (int i=0; i<N-3; i++) {
                full_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
            }
            full_sc /= (N - 3);

            printf("[%s %s] sc=%6.4f | %s\nPlaintext: ",
                   (model < 2) ? "KRYPTOS" : "STD",
                   is_beau ? "Beaufort" : "Vigenere",
                   full_sc, line);
            for (int i=0; i<N; i++) printf("%c", 'A' + pt[i]);
            printf("\n\n");
        }
    }
    return 0;
}
