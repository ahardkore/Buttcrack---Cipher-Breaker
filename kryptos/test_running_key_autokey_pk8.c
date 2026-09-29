#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int std_to_kr[26];
static int ct_kr[N];
static int ct_std[N];
static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK8_CT[i] - 'A'];
        ct_std[i] = PK8_CT[i] - 'A';
    }

    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) total += cnt;
    }
    fseek(f, 0, SEEK_SET);
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)cnt / total);
            }
        }
    }
    fclose(f);
}

static inline float score_text(const char *pt) {
    float sc = 0;
    for (int t = 0; t < N - 3; t++) {
        sc += quadgrams[pt[t]-'A'][pt[t+1]-'A'][pt[t+2]-'A'][pt[t+3]-'A'];
    }
    return sc / (N - 3);
}

void test_running_key(const char *filename) {
    FILE *f = fopen(filename, "r");
    if (!f) return;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *raw = malloc(sz + 1);
    fread(raw, 1, sz, f);
    raw[sz] = '\0';
    fclose(f);

    // Filter to letters only
    char *corpus = malloc(sz + 1);
    long len = 0;
    for (long i = 0; i < sz; i++) {
        if (isalpha(raw[i])) corpus[len++] = toupper(raw[i]);
    }
    corpus[len] = '\0';
    free(raw);

    printf("Testing running key against %s (%ld alpha chars)...\n", filename, len);
    if (len < N) { free(corpus); return; }

    float best_sc = -1e9f;
    char best_pt[N + 1];
    long best_pos = -1;
    int best_mode = 0; // 0=Vig Kr, 1=Beau Kr, 2=Vig Std, 3=Beau Std

    #pragma omp parallel
    {
        float local_sc = -1e9f;
        char local_pt[N + 1];
        long local_pos = -1;
        int local_mode = 0;

        #pragma omp for schedule(static, 1000)
        for (long pos = 0; pos <= len - N; pos++) {
            for (int mode = 0; mode < 4; mode++) {
                char pt[N + 1];
                int use_kr = (mode < 2);
                int is_beau = (mode % 2 == 1);
                const int *ct = use_kr ? ct_kr : ct_std;

                for (int t = 0; t < N; t++) {
                    int k = use_kr ? std_to_kr[corpus[pos + t] - 'A'] : (corpus[pos + t] - 'A');
                    int p = is_beau ? (k - ct[t] + 26) % 26 : (ct[t] - k + 26) % 26;
                    pt[t] = use_kr ? ALPH[p] : ('A' + p);
                }
                pt[N] = '\0';

                float sc = score_text(pt);
                if (sc > local_sc) {
                    local_sc = sc;
                    local_pos = pos;
                    local_mode = mode;
                    strcpy(local_pt, pt);
                }
            }
        }

        #pragma omp critical
        {
            if (local_sc > best_sc) {
                best_sc = local_sc;
                best_pos = local_pos;
                best_mode = local_mode;
                strcpy(best_pt, local_pt);
            }
        }
    }

    const char *modes[] = {"Kryptos Vigenere", "Kryptos Beaufort", "Standard Vigenere", "Standard Beaufort"};
    printf("Best Running Key Match in %s:\n", filename);
    printf("  Score: %.2f | Mode: %s | Pos: %ld\n", best_sc, modes[best_mode], best_pos);
    printf("  Key:   %.30s...\n", corpus + best_pos);
    printf("  PT:    %s\n\n", best_pt);

    free(corpus);
}

int main(void) {
    init_tables();

    test_running_key("candidate_running_keys.txt");
    test_running_key("theophilus_book3_english.txt");
    test_running_key("theophilus_hendrie.txt");

    return 0;
}
