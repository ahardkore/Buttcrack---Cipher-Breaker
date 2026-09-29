#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

static float quad[26][26][26][26];

void load_quadgrams(const char *path) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -10.0f;

    FILE *f = fopen(path, "r");
    if (!f) { printf("Failed to open %s\n", path); exit(1); }
    char line[128];
    double total = 0;
    long long counts[26][26][26][26] = {0};

    while (fgets(line, sizeof(line), f)) {
        char q[5]; long long cnt;
        if (sscanf(line, "%4s %lld", q, &cnt) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = cnt;
                total += cnt;
            }
        }
    }
    fclose(f);

    float log_tot = log10(total);
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    if (counts[a][b][c][d] > 0)
                        quad[a][b][c][d] = log10((double)counts[a][b][c][d]) - log_tot;
                    else
                        quad[a][b][c][d] = -9.5f;
                }
}

static inline void decrypt_single(const int *ct, int n, int width, const int *order, int *out) {
    int h = n / width;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        int base_ct = m * h;
        for (int r = 0; r < h; r++) {
            out[r * width + col] = ct[base_ct + r];
        }
    }
}

static inline float score_text(const int *txt, int n) {
    float sc = 0.0f;
    for (int i = 0; i < n - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (n - 3);
}

int main() {
    load_quadgrams("/home/user/buttcrack/src/buttcrack/data/english_quadgrams.txt");

    const char *z6_str = "ONEEIHTEEIEKWSUAANCENOEOHGFIIHETIIRHTSUWQSFEEHYSIHTRERYRKINEFSTTOEHSHNIOOTIRKSEELKDTMHOESKILTFHEEHEIDENROTEUTTTTLREHETTDELOWWCEOSOEWYTTTIHHEAYMNAIWYERODTFMTTOEYEAFTEIHEWHWOSSHGHTOEFGSHSHHEOFRWREAEWEEEYADLSSSHLMSFHTEDTHNDNLRWAKLOHPRTTHNEOODRAIOAUNLSTTAOOUAMTYTRTETMTOETRCEWAKPMEGRLSHNTAESSEKCYAOPANLSIWIDTTTAEIEIRHNSIPFROEMLITW";
    int n = strlen(z6_str);
    int ct[400];
    for (int i = 0; i < n; i++) ct[i] = z6_str[i] - 'A';

    int known_o1[9] = {1,3,0,4,8,2,6,7,5};
    int known_o2[9] = {4,2,8,1,6,7,0,3,5};
    int inter[400], plain[400];
    decrypt_single(ct, n, 9, known_o2, inter);
    decrypt_single(inter, n, 9, known_o1, plain);
    printf("Ground truth score: %.4f\n", score_text(plain, n));
    char pt[400];
    for (int i = 0; i < n; i++) pt[i] = 'A' + plain[i]; pt[n] = 0;
    printf("Ground truth PT: %.60s...\n", pt);

    return 0;
}
