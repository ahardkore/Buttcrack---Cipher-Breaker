#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float quad[26][26][26][26];

void load_quadgrams() {
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Failed to open english_quadgrams.txt\n"); exit(1); }
    char line[128];
    double total = 0;
    static double counts[26][26][26][26];
    memset(counts, 0, sizeof(counts));
    while (fgets(line, sizeof(line), f)) {
        char gram[5]; double count;
        if (sscanf(line, "%4s %lf", gram, &count) == 2) {
            int a = gram[0] - 'A', b = gram[1] - 'A', c = gram[2] - 'A', d = gram[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = count;
                total += count;
            }
        }
    }
    fclose(f);
    float floor_val = log10f(0.01f / total);
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = counts[a][b][c][d] > 0 ? log10f(counts[a][b][c][d] / total) : floor_val;
}

float score_text(const char *pt, int len) {
    float sc = 0;
    for (int i = 0; i < len - 3; i++) {
        int a = pt[i] - 'A', b = pt[i+1] - 'A', c = pt[i+2] - 'A', d = pt[i+3] - 'A';
        sc += quad[a][b][c][d];
    }
    return sc / (len - 3);
}

void solve_columnar(const char *Z, int W, int num_restarts, int steps_per_restart) {
    int N = strlen(Z);
    int H = N / W;

    // Read by rows, write by cols: Z[r * W + c]
    // Decryption with col perm P: pt[r * W + c] = Z[r * W + P[c]] or col read
    // Mode 1: Written by cols, read by rows
    // Mode 2: Written by rows, read by cols

    float global_best_sc = -999.0f;
    char global_best_pt[200] = "";
    int global_best_p[64];

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 777;
        float local_best_sc = -999.0f;
        char local_best_pt[200] = "";
        int local_best_p[64];

        #pragma omp for schedule(dynamic)
        for (int r = 0; r < num_restarts; r++) {
            int p[64];
            for (int i = 0; i < W; i++) p[i] = i;

            // Shuffle
            for (int i = W - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
            }

            char pt[200];
            // Mode 1: text in columns, read out by rows with col perm p
            for (int row = 0; row < H; row++) {
                for (int col = 0; col < W; col++) {
                    pt[row * W + col] = Z[p[col] * H + row];
                }
            }
            pt[N] = '\0';
            float cur_sc = score_text(pt, N);
            float best_sc = cur_sc;
            int best_p[64];
            memcpy(best_p, p, sizeof(int) * W);

            float temp = 10.0f;
            float step = temp / steps_per_restart;

            for (int s = 0; s < steps_per_restart; s++) {
                int i = rand_r(&seed) % W;
                int j = rand_r(&seed) % W;
                while (i == j) j = rand_r(&seed) % W;

                // Swap
                int tmp = p[i]; p[i] = p[j]; p[j] = tmp;

                for (int row = 0; row < H; row++) {
                    for (int col = 0; col < W; col++) {
                        pt[row * W + col] = Z[p[col] * H + row];
                    }
                }
                float new_sc = score_text(pt, N);
                float delta = new_sc - cur_sc;

                if (delta > 0 || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_sc) {
                        best_sc = cur_sc;
                        memcpy(best_p, p, sizeof(int) * W);
                    }
                } else {
                    // Undo
                    tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                }
                temp -= step;
            }

            if (best_sc > local_best_sc) {
                local_best_sc = best_sc;
                memcpy(local_best_p, best_p, sizeof(int) * W);
                for (int row = 0; row < H; row++) {
                    for (int col = 0; col < W; col++) {
                        local_best_pt[row * W + col] = Z[best_p[col] * H + row];
                    }
                }
                local_best_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_pt, local_best_pt);
                memcpy(global_best_p, local_best_p, sizeof(int) * W);
            }
        }
    }

    if (global_best_sc > -4.8f) {
        printf("  HIT! W=%d sc=%6.4f | %s\n", W, global_best_sc, global_best_pt);
    }
}

int main() {
    load_quadgrams();

    FILE *f = fopen("top_Z_candidates.txt", "r");
    if (!f) { printf("Cannot open top_Z_candidates.txt\n"); return 1; }

    char line[512];
    int candidate_idx = 0;
    while (fgets(line, sizeof(line), f)) {
        candidate_idx++;
        float dot;
        int q4[4], q7[7];
        char Z[200];
        if (sscanf(line, "%f %d %d %d %d %d %d %d %d %d %d %d %s",
                   &dot, &q4[0], &q4[1], &q4[2], &q4[3],
                   &q7[0], &q7[1], &q7[2], &q7[3], &q7[4], &q7[5], &q7[6], Z) == 13) {
            printf("\nTesting Candidate #%d (dot=%.4f):\n", candidate_idx, dot);
            int test_widths[] = {6, 8, 9, 12, 16, 18, 24};
            for (int w = 0; w < 7; w++) {
                solve_columnar(Z, test_widths[w], 200, 3000);
            }
        }
    }
    fclose(f);
    return 0;
}
