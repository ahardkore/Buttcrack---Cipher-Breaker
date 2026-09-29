#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) exit(1);
    char q[16]; float cnt; double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static inline float score_text(const int *txt, int len) {
    float sc = 0.0f;
    for (int i = 0; i < len - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (len - 3);
}

void col_decrypt(const int *in, const int *order, int *out, int w, int h) {
    int grid[h][w];
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < h; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) out[idx++] = grid[r][c];
}

int main() {
    load_quads();
    printf("Models loaded.\n");

    const char *Z_texts[4] = {
        "UUUHROFIAKPNIHOWBIGHBDCEITOBADMFTEEGLGSEGNIKAWDOWRRMUCIHCWDBPMYVGDYCDNKNDLBUIHUFTPGHXWECWGHELDGMIHEUROHUTMVOBLGICWIXLRGESCRCSHESCSCMLOYORVVISLTK",
        "BEMSYLUNYWKCRSHCFRJSYSWCRWLYVVUUWVVPNAHLTMNOGDMLDEHUFNRSTCDYANBASDBNWMLLDOOFROEBGATSYCCXTTSRNDTDRSREPLIFGJDSYETRTCYCEITRGEINHSRGEHNNOHASIUERDNNP",
        "FTNKGOBHKVBVMDWNPRAUTJOSRMOTSSEUMIACHLDSLIHGYVOONKREFTMDMNOHEPUPCOQTHINIOTPDEDTAEELDONSIXLDAHOMLMDATGABDPUYWHDLEMNCGDBCAMTNTCDAMTDTPWWUWNWEERHIP",
        "FNVVYLBDWNHNTSRTFUBRFBMCUWLFMLTRWACICXFCORDDGKDLWXVTDETSSTDBTNUUHDYEBROBDMFFOHNBETOSNTCALOSLCDTXTSLNYIAFGPUMBOOOSTSCOHALOEPEGSLOEFENNRYMPMEOWCKN"
    };

    int widths[5] = {6, 8, 9, 12, 16};

    for (int m = 0; m < 4; m++) {
        const char *z_str = Z_texts[m];
        int z[N];
        for (int i = 0; i < N; i++) z[i] = z_str[i] - 'A';

        printf("\n=== Evaluating Mode %d ===\n", m);

        for (int widx = 0; widx < 5; widx++) {
            int W = widths[widx];
            int H = N / W;

            float best_w_sc = -999.0f;
            int best_order[W];
            int best_pt[N];

            #pragma omp parallel
            {
                unsigned int seed = 1234 + omp_get_thread_num() * 777 + widx * 33;
                float loc_best = -999.0f;
                int loc_order[W], loc_pt[N];
                int cur_order[W], cur_pt[N];

                for (int restart = 0; restart < 100; restart++) {
                    for (int i = 0; i < W; i++) cur_order[i] = i;
                    for (int i = W - 1; i > 0; i--) {
                        int j = rand_r(&seed) % (i + 1);
                        int t = cur_order[i]; cur_order[i] = cur_order[j]; cur_order[j] = t;
                    }

                    col_decrypt(z, cur_order, cur_pt, W, H);
                    float cur_sc = score_text(cur_pt, N);

                    float T = 0.4f, alpha = 0.999f;
                    for (int step = 0; step < 3000; step++) {
                        int next_order[W];
                        memcpy(next_order, cur_order, sizeof(next_order));

                        int a = rand_r(&seed) % W, b = rand_r(&seed) % W;
                        int t = next_order[a]; next_order[a] = next_order[b]; next_order[b] = t;

                        int next_pt[N];
                        col_decrypt(z, next_order, next_pt, W, H);
                        float next_sc = score_text(next_pt, N);

                        float diff = next_sc - cur_sc;
                        if (diff > 0.0f || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                            cur_sc = next_sc;
                            memcpy(cur_order, next_order, sizeof(cur_order));
                            if (cur_sc > loc_best) {
                                loc_best = cur_sc;
                                memcpy(loc_order, cur_order, sizeof(loc_order));
                                memcpy(loc_pt, next_pt, sizeof(loc_pt));
                            }
                        }
                        T *= alpha;
                    }
                }

                #pragma omp critical
                {
                    if (loc_best > best_w_sc) {
                        best_w_sc = loc_best;
                        memcpy(best_order, loc_order, sizeof(best_order));
                        memcpy(best_pt, loc_pt, sizeof(loc_pt));
                    }
                }
            }

            char pt_str[N+1];
            for (int i = 0; i < N; i++) pt_str[i] = best_pt[i] + 'A';
            pt_str[N] = 0;

            printf("Width %2d (%2d x %2d): Best Score = %.4f | Order: [", W, H, W, best_w_sc);
            for (int i = 0; i < W; i++) printf("%d%s", best_order[i], i==W-1?"":", ");
            printf("]\n  PT: %.70s...\n", pt_str);
        }
    }

    return 0;
}
