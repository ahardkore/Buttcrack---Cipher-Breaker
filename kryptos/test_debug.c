#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define W 12
#define H 12
#define N 144

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("File not found!\n"); return; }
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
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int shifts[28] = {
    5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3
};

static char grid[W][H];

int main() {
    load_quads();
    int hpos[256];
    for (int i=0; i<26; i++) hpos[(unsigned char)KRYPTOS[i]] = i;
    
    char z[N];
    for (int i=0; i<N; i++) {
        int c_idx = hpos[(unsigned char)PK9_REAL[i]];
        int p_kr = (c_idx - shifts[i % 28] + 26) % 26;
        z[i] = KRYPTOS[p_kr];
    }
    for (int c=0; c<W; c++) {
        for (int r=0; r<H; r++) {
            grid[c][r] = z[c * H + r];
        }
    }
    
    int perm[12] = {3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10};
    float cur_score = 0;
    for (int d = 4; d <= 12; d++) {
        int c0 = perm[d-4];
        int c1 = perm[d-3];
        int c2 = perm[d-2];
        int c3 = perm[d-1];
        float step_score = 0.0f;
        for (int r=0; r<H; r++) {
            int q0 = grid[c0][r] - 'A';
            int q1 = grid[c1][r] - 'A';
            int q2 = grid[c2][r] - 'A';
            int q3 = grid[c3][r] - 'A';
            step_score += quad[q0][q1][q2][q3];
        }
        cur_score += step_score;
        printf("Depth %2d: avg = %.3f\n", d, cur_score / (H * (d - 3)));
    }
    return 0;
}
