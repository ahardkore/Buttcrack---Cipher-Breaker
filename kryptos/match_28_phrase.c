#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const int shifts[28] = {
    5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3
};

int main() {
    FILE *f = fopen("theophilus_hendrie.txt", "r");
    if (!f) return 1;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *raw = (char*)malloc(sz + 1);
    fread(raw, 1, sz, f);
    fclose(f);
    raw[sz] = '\0';
    
    char *clean = (char*)malloc(sz + 1);
    int clen = 0;
    for (long i=0; i<sz; i++) {
        char c = raw[i];
        if (c >= 'a' && c <= 'z') c -= 32;
        if (c >= 'A' && c <= 'Z') clean[clen++] = c;
    }
    clean[clen] = '\0';
    free(raw);
    
    int hpos[256];
    for (int i=0; i<26; i++) hpos[(unsigned char)KRYPTOS[i]] = i;
    
    int best_matches = 0;
    int best_pos = -1;
    char best_str[29];
    
    #pragma omp parallel
    {
        int local_best = 0;
        int local_pos = -1;
        char local_str[29];
        
        #pragma omp for
        for (int i=0; i<clen-28; i++) {
            // Check KRYPTOS
            for (int c=0; c<26; c++) {
                int m = 0;
                for (int j=0; j<28; j++) {
                    int k_idx = hpos[(unsigned char)clean[i+j]];
                    if ((k_idx - c + 26) % 26 == shifts[j]) m++;
                }
                if (m > local_best) {
                    local_best = m;
                    local_pos = i;
                    strncpy(local_str, clean+i, 28);
                    local_str[28] = '\0';
                }
            }
            // Check Standard
            for (int c=0; c<26; c++) {
                int m = 0;
                for (int j=0; j<28; j++) {
                    int std_idx = clean[i+j] - 'A';
                    if ((std_idx - c + 26) % 26 == shifts[j]) m++;
                }
                if (m > local_best) {
                    local_best = m;
                    local_pos = i;
                    strncpy(local_str, clean+i, 28);
                    local_str[28] = '\0';
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best > best_matches) {
                best_matches = local_best;
                best_pos = local_pos;
                strcpy(best_str, local_str);
            }
        }
    }
    
    printf("Best matches in Theophilus: %d/28 at pos %d\n", best_matches, best_pos);
    printf("Text: %s\n", best_str);
    return 0;
}
