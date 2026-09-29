#include <stdio.h>
#include <string.h>
#include <assert.h>

static inline void decrypt_single(const char *ct, int n, int width, const int *order, char *out) {
    int h = n / width;
    char grid[400][50];
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            grid[r][col] = ct[k++];
        }
    }
    int idx = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < width; c++) {
            out[idx++] = grid[r][c];
        }
    }
    out[n] = '\0';
}

int main() {
    const char *z6 = "ONEEIHTEEIEKWSUAANCENOEOHGFIIHETIIRHTSUWQSFEEHYSIHTRERYRKINEYTEWUSWCAIEESWGSTMLTEIWHUHTTNLEMAREYEAHEMNOEKILLTPEWYLHDHTDNSDMRAYHNOTNOIRAIIHCLMTOEAEDMHVIHTTEKSISORKDHSTTLSEWTTEMDASWUYRTLDESIGTLTERDXEMOEHEASATEYTOHOLHHHNASSATIUWOSTSIHWSLSSHFOEFNTACEEOIDEAROHALYAYETEHGGRPTEOLRIOISNANFEYLESLNEMEOTDASANMTWOHFWTDTIHEOLDH";
    int n = strlen(z6);
    int o1[9] = {1,3,0,4,8,2,6,7,5};
    int o2[9] = {4,2,8,1,6,7,0,3,5};
    char inter[400], plain[400];
    decrypt_single(z6, n, 9, o2, inter);
    decrypt_single(inter, n, 9, o1, plain);
    printf("Decrypted: %.60s...\n", plain);
    const char *expected = "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWNTOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHEMAKESONEEVERYDAYANDLOSTCOUNTLONGAGOIASKWHATHEDOESWITHTHEMANDHESAYSTHEYAREONLYTHERESIDUEOFHISPRACTICEHETELLSMETHATIFISTUDYUNDERHIMFORTENYEARSHEWILLLETMETAKEONEOFMYOWNMAKING";
    assert(strcmp(plain, expected) == 0);
    printf("C decrypt matches Python exactly!\n");
    return 0;
}
