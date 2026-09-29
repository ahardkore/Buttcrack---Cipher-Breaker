#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static float quad[26][26][26][26];
static float bi[26][26];

void load_models() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++) {
            bi[a][b] = -6.0f;
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
        }
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
    char q[16]; float cnt;
    double total = 0;
    // temporary store
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    double bi_tot = 0;
    double bi_cnt[26][26] = {{0}};
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
                bi_cnt[a][b] += cnt; bi_cnt[b][c] += cnt; bi_cnt[c][d] += cnt;
                bi_tot += 3 * cnt;
            }
        }
    }
    fclose(f);
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            bi[a][b] = (float)log10((bi_cnt[a][b] + 0.01) / bi_tot);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQGZGSMMJHJQNHSVHAWFLHXLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIFLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJK";
static int k_pos[256];
static int k_to_std[26];

void init_alpha() {
    for (int i=0; i<26; i++) {
        k_pos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
}

void get_col_map(int w, const int *o, int *map) {
    int h = N / w;
    for (int c = 0; c < w; c++) {
        int col = o[c];
        for (int r = 0; r < h; r++) {
            map[r * w + col] = c * h + r;
        }
    }
}

float col_ioc(const char *txt, int p) {
    int counts[26];
    float total_ioc = 0.0f;
    for (int rem = 0; rem < p; rem++) {
        memset(counts, 0, sizeof(counts));
        int n_letters = 0;
        for (int i = rem; i < N; i += p) {
            counts[txt[i] - 'A']++;
            n_letters++;
        }
        if (n_letters > 1) {
            int num = 0;
            for (int k = 0; k < 26; k++) num += counts[k] * (counts[k] - 1);
            total_ioc += (float)num / (float)(n_letters * (n_letters - 1));
        }
    }
    return total_ioc / (float)p;
}

// Fast Viterbi DP over period 7 shifts
float viterbi_p7(const char *txt, int *best_shifts, char *out_pt) {
    // txt indices in KRYPTOS
    int c_idx[N];
    for (int i=0; i<N; i++) c_idx[i] = k_pos[(unsigned char)txt[i]];
    
    // cols[rem][r]
    int cols[7][21];
    int col_len[7];
    for (int c=0; c<7; c++) {
        col_len[c] = 0;
        for (int i=c; i<N; i+=7) {
            cols[c][col_len[c]++] = c_idx[i];
        }
    }
    
    // Transition matrices between consecutive columns
    float trans[6][26][26];
    for (int c=0; c<6; c++) {
        int L = col_len[c+1];
        for (int s1=0; s1<26; s1++) {
            for (int s2=0; s2<26; s2++) {
                float sc = 0.0f;
                for (int r=0; r<L; r++) {
                    int p1 = k_to_std[(cols[c][r] - s1 + 26) % 26];
                    int p2 = k_to_std[(cols[c+1][r] - s2 + 26) % 26];
                    sc += bi[p1][p2];
                }
                trans[c][s1][s2] = sc;
            }
        }
    }
    
    // Wrap around from col 6 to col 0
    float wrap[26][26];
    int L_wrap = col_len[0] - 1;
    for (int s6=0; s6<26; s6++) {
        for (int s0=0; s0<26; s0++) {
            float sc = 0.0f;
            for (int r=0; r<L_wrap; r++) {
                int p6 = k_to_std[(cols[6][r] - s6 + 26) % 26];
                int p0 = k_to_std[(cols[0][r+1] - s0 + 26) % 26];
                sc += bi[p6][p0];
            }
            wrap[s6][s0] = sc;
        }
    }
    
    float best_total = -1e9f;
    int opt_shifts[7];
    
    for (int s0_start=0; s0_start<26; s0_start++) {
        float dp[26];
        for (int s=0; s<26; s++) dp[s] = -1e9f;
        dp[s0_start] = 0.0f;
        int bp[6][26];
        
        for (int step=0; step<6; step++) {
            float next_dp[26];
            for (int s=0; s<26; s++) next_dp[s] = -1e9f;
            for (int curr_s=0; curr_s<26; curr_s++) {
                if (dp[curr_s] <= -1e8f) continue;
                for (int next_s=0; next_s<26; next_s++) {
                    float v = dp[curr_s] + trans[step][curr_s][next_s];
                    if (v > next_dp[next_s]) {
                        next_dp[next_s] = v;
                        bp[step][next_s] = curr_s;
                    }
                }
            }
            memcpy(dp, next_dp, sizeof(dp));
        }
        
        for (int s6=0; s6<26; s6++) {
            if (dp[s6] <= -1e8f) continue;
            float tot = dp[s6] + wrap[s6][s0_start];
            if (tot > best_total) {
                best_total = tot;
                int curr = s6;
                opt_shifts[6] = curr;
                for (int step=5; step>=0; step--) {
                    curr = bp[step][curr];
                    opt_shifts[step] = curr;
                }
            }
        }
    }
    
    if (best_shifts) memcpy(best_shifts, opt_shifts, sizeof(int)*7);
    
    // Decrypt and score with quadgrams
    int pt_std[N];
    for (int i=0; i<N; i++) {
        int p = (c_idx[i] - opt_shifts[i % 7] + 26) % 26;
        pt_std[i] = k_to_std[p];
        if (out_pt) out_pt[i] = 'A' + pt_std[i];
    }
    if (out_pt) out_pt[N] = '\0';
    
    float qsc = 0.0f;
    for (int i=0; i<N-3; i++) {
        qsc += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return qsc / (N - 3);
}

typedef struct {
    char word[32];
    int order[32];
} KeyOrder;

int load_orders(const char *fn, int w, KeyOrder *out, int max_n) {
    FILE *f = fopen(fn, "r");
    if (!f) return 0;
    char line[128];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_n) {
        char word[32];
        if (sscanf(line, "%s", word) != 1) continue;
        if (strlen(word) != w) continue;
        int ok = 1;
        for (int i = 0; i < w; i++) {
            if (word[i] < 'A' || word[i] > 'Z') { ok = 0; break; }
        }
        if (!ok) continue;
        
        int ord[32];
        for (int i = 0; i < w; i++) ord[i] = i;
        for (int i = 0; i < w - 1; i++) {
            for (int j = i + 1; j < w; j++) {
                if (word[ord[i]] > word[ord[j]]) {
                    int tmp = ord[i]; ord[i] = ord[j]; ord[j] = tmp;
                }
            }
        }
        
        int duplicate = 0;
        for (int i = 0; i < count; i++) {
            int same = 1;
            for (int k = 0; k < w; k++) {
                if (out[i].order[k] != ord[k]) { same = 0; break; }
            }
            if (same) { duplicate = 1; break; }
        }
        if (!duplicate) {
            strcpy(out[count].word, word);
            for (int k = 0; k < w; k++) out[count].order[k] = ord[k];
            count++;
        }
    }
    fclose(f);
    return count;
}

int main() {
    load_models();
    init_alpha();
    printf("Models loaded.\n");
    
    int widths[] = {8, 9, 12};
    for (int wi=0; wi<3; wi++) {
        int w = widths[wi];
        char fn[64];
        KeyOrder keys[1000];
        sprintf(fn, "theophilus_w%d.txt", w);
        int n_keys = load_orders(fn, w, keys, 1000);
        sprintf(fn, "curated_w%d.txt", w);
        int n2 = load_orders(fn, w, keys + n_keys, 1000 - n_keys);
        n_keys += n2;
        sprintf(fn, "words_%d.txt", w);
        int n3 = load_orders(fn, w, keys + n_keys, 1000 - n_keys);
        n_keys += n3;
        printf("\n=== Evaluating Width %d (%d orders) ===\n", w, n_keys);
        
        float best_quad = -999.0f;
        
        #pragma omp parallel
        {
            float local_best_q = -999.0f;
            int map1[N], map2[N];
            char undone[N + 1];
            undone[N] = '\0';
            int shifts[7];
            char pt[N + 1];
            
            #pragma omp for schedule(dynamic)
            for (int i = 0; i < n_keys; i++) {
                get_col_map(w, keys[i].order, map1);
                for (int j = 0; j < n_keys; j++) {
                    get_col_map(w, keys[j].order, map2);
                    for (int k = 0; k < N; k++) {
                        undone[k] = PK9_CT[map1[map2[k]]];
                    }
                    float rv7 = col_ioc(undone, 7);
                    if (rv7 > 0.070f) {
                        float qsc = viterbi_p7(undone, shifts, pt);
                        if (qsc > -6.0f) {
                            #pragma omp critical
                            {
                                printf("\n*** SOLVE HIT! Quad=%.3f | rv7=%.5f | w=%d ***\n", qsc, rv7, w);
                                printf("  KW1: %s | KW2: %s\n", keys[i].word, keys[j].word);
                                printf("  Shifts: %d %d %d %d %d %d %d\n", shifts[0], shifts[1], shifts[2], shifts[3], shifts[4], shifts[5], shifts[6]);
                                printf("  PT: %s\n", pt);
                            }
                        }
                        if (qsc > local_best_q) local_best_q = qsc;
                    }
                }
            }
            #pragma omp critical
            {
                if (local_best_q > best_quad) best_quad = local_best_q;
            }
        }
        printf("Width %d scan finished. Best Quad: %.3f\n", w, best_quad);
    }
    return 0;
}
