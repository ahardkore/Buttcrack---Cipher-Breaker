#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

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
static const char *undone = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int u_kr[N];
static int u_std[N];
static int k_to_std[26];
static int std_to_k[26];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        u_std[i] = undone[i] - 'A';
        u_kr[i] = std_to_k[undone[i] - 'A'];
    }
}

float score_txt(const int *pt_std) {
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return sc / (N - 3);
}

int main() {
    load_quads();
    init();
    printf("Loaded models. Testing all 7-letter words on undone...\n");
    
    FILE *f = fopen("words_7.txt", "r");
    if (!f) return 1;
    
    char word[32];
    float best_sc_kr = -999.0f;
    float best_sc_std = -999.0f;
    char best_w_kr[32] = "";
    char best_w_std[32] = "";
    int pt_std[N];
    int count = 0;
    
    while (fscanf(f, "%31s", word) == 1) {
        if (strlen(word) != 7) continue;
        count++;
        
        // Mode 1: QIII (KRYPTOS alphabet)
        int key_kr[7];
        for (int j=0; j<7; j++) key_kr[j] = std_to_k[word[j] - 'A'];
        for (int i=0; i<N; i++) {
            int p_kr = (u_kr[i] - key_kr[i % 7] + 26) % 26;
            pt_std[i] = k_to_std[p_kr];
        }
        float sc_kr = score_txt(pt_std);
        if (sc_kr > best_sc_kr) {
            best_sc_kr = sc_kr;
            strcpy(best_w_kr, word);
            if (sc_kr > -6.0f) {
                printf("[QIII HIT] Word: %s | Quad: %.3f\n", word, sc_kr);
                char txt[N+1];
                for (int i=0; i<N; i++) txt[i] = pt_std[i] + 'A';
                txt[N] = '\0';
                printf("  PT: %s\n", txt);
            }
        }
        
        // Mode 2: Standard Vig
        int key_std[7];
        for (int j=0; j<7; j++) key_std[j] = word[j] - 'A';
        for (int i=0; i<N; i++) {
            pt_std[i] = (u_std[i] - key_std[i % 7] + 26) % 26;
        }
        float sc_std = score_txt(pt_std);
        if (sc_std > best_sc_std) {
            best_sc_std = sc_std;
            strcpy(best_w_std, word);
            if (sc_std > -6.0f) {
                printf("[Std Vig HIT] Word: %s | Quad: %.3f\n", word, sc_std);
                char txt[N+1];
                for (int i=0; i<N; i++) txt[i] = pt_std[i] + 'A';
                txt[N] = '\0';
                printf("  PT: %s\n", txt);
            }
        }
    }
    fclose(f);
    printf("Evaluated %d 7-letter words on undone.\n", count);
    printf("Best QIII: %s (Quad: %.3f)\n", best_w_kr, best_sc_kr);
    printf("Best Std Vig: %s (Quad: %.3f)\n", best_w_std, best_sc_std);
    return 0;
}
