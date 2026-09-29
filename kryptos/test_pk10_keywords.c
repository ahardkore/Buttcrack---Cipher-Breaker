#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define N 504

static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

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

void get_col_map(int w, const int *o, int *map) {
    int h = N / w;
    for (int c = 0; c < w; c++) {
        int col = o[c];
        for (int r = 0; r < h; r++) {
            map[r * w + col] = c * h + r;
        }
    }
}

void argsort(const char *w, int len, int *out) {
    for (int i=0; i<len; i++) out[i] = i;
    for (int i=0; i<len-1; i++) {
        for (int j=i+1; j<len; j++) {
            if (w[out[i]] > w[out[j]]) {
                int t = out[i]; out[i] = out[j]; out[j] = t;
            }
        }
    }
}

int main() {
    const char *keys21[] = {
        "OFTHESECONDROSECOLOUR",
        "OFATRANSPARENTPICTURE",
        "OFFLASKSWITHALONGNECK",
        "THESAMEASTHEPRECEDING",
        "OFSCULPINGINSTRUMENTS",
        "OFSCRAPINGINSTRUMENTS",
        "OFIRONSFORMAKINGNAILS",
        "OFPOLISHINGTHEGILDING",
        "OFTHEFOOTOFTHECHALICE",
        "HOWFINEBRASSCANBEGILT",
        "OFTHEMEASUREOFCYMBALS",
        "ITWASTOTALLYINVISIBLE",
        "EASTNORTHEASTBERLINCL",
        "CENTRALINTELLIGENCEAG"
    };
    int n21 = sizeof(keys21) / sizeof(keys21[0]);
    
    printf("Testing Width 21 on PK10 across %d candidate keywords...\n", n21);
    for (int i=0; i<n21; i++) {
        int ord[21];
        argsort(keys21[i], 21, ord);
        int map[N];
        get_col_map(21, ord, map);
        char undone[N+1];
        for (int k=0; k<N; k++) undone[k] = PK10_CT[map[k]];
        undone[N] = '\0';
        
        float ioc7 = col_ioc(undone, 7);
        float ioc8 = col_ioc(undone, 8);
        float ioc9 = col_ioc(undone, 9);
        float ioc72 = col_ioc(undone, 72);
        printf("Key 21 '%s': IoC(7)=%.4f, IoC(8)=%.4f, IoC(9)=%.4f, IoC(72)=%.4f\n",
               keys21[i], ioc7, ioc8, ioc9, ioc72);
    }
    
    const char *keys24[] = {
        "OFTHEWHITEGROUNDOFGYPSUM",
        "HOWVASESAREMADEFROMGLASS",
        "OFMAKINGTHEGOLDENCHALICE",
        "OFCLEANSINGGOLDANDSILVER"
    };
    int n24 = sizeof(keys24) / sizeof(keys24[0]);
    printf("\nTesting Width 24 on PK10 across %d candidate keywords...\n", n24);
    for (int i=0; i<n24; i++) {
        int ord[24];
        argsort(keys24[i], 24, ord);
        int map[N];
        get_col_map(24, ord, map);
        char undone[N+1];
        for (int k=0; k<N; k++) undone[k] = PK10_CT[map[k]];
        undone[N] = '\0';
        
        float ioc7 = col_ioc(undone, 7);
        float ioc8 = col_ioc(undone, 8);
        float ioc9 = col_ioc(undone, 9);
        float ioc72 = col_ioc(undone, 72);
        printf("Key 24 '%s': IoC(7)=%.4f, IoC(8)=%.4f, IoC(9)=%.4f, IoC(72)=%.4f\n",
               keys24[i], ioc7, ioc8, ioc9, ioc72);
    }
    
    return 0;
}
