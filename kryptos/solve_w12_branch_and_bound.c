#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

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

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int shifts[28] = {
    5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3
};

static char grid[W][H];

void init() {
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
}

float global_best_score = -6.5f;

void search(int depth, int mask, int *perm, float cur_score) {
    if (depth >= 4) {
        int c0 = perm[depth-4];
        int c1 = perm[depth-3];
        int c2 = perm[depth-2];
        int c3 = perm[depth-1];
        float step_score = 0.0f;
        for (int r=0; r<H; r++) {
            int q0 = grid[c0][r] - 'A';
            int q1 = grid[c1][r] - 'A';
            int q2 = grid[c2][r] - 'A';
            int q3 = grid[c3][r] - 'A';
            step_score += quad[q0][q1][q2][q3];
        }
        cur_score += step_score;
        
        int quads_per_row = depth - 3;
        float avg_per_row_quad = cur_score / (H * quads_per_row);
        if (depth == 4 && avg_per_row_quad < -7.0f) return;
        if (depth == 6 && avg_per_row_quad < -6.5f) return;
        if (depth == 8 && avg_per_row_quad < -6.2f) return;
        if (depth == 10 && avg_per_row_quad < -5.9f) return;
    }
    
    if (depth == W) {
        float avg = cur_score / (H * (W - 3));
        #pragma omp critical
        {
            if (avg > global_best_score) {
                global_best_score = avg;
                printf("New Best! Avg Quad: %.3f | Perm: [", avg);
                for (int i=0; i<W; i++) printf("%d%s", perm[i], i==W-1?"":", ");
                printf("]\n");
                
                for (int r=0; r<H; r++) {
                    char row[W+1];
                    for (int c=0; c<W; c++) row[c] = grid[perm[c]][r];
                    row[W] = '\0';
                    printf("  Row %2d: %s\n", r, row);
                }
            }
        }
        return;
    }
    
    for (int next_col = 0; next_col < W; next_col++) {
        if (!(mask & (1 << next_col))) {
            perm[depth] = next_col;
            search(depth + 1, mask | (1 << next_col), perm, cur_score);
        }
    }
}

int main() {
    load_quads();
    init();
    printf("Models loaded. Starting Branch & Bound on 12! permutations...\n");
    
    double t0 = omp_get_wtime();
    
    #pragma omp parallel for schedule(dynamic, 1)
    for (int first_col = 0; first_col < W; first_col++) {
        int perm[W];
        perm[0] = first_col;
        search(1, 1 << first_col, perm, 0.0f);
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nSearch completed in %.2f seconds.\n", elapsed);
    printf("Global Best Avg Quad: %.3f\n", global_best_score);
    return 0;
}
