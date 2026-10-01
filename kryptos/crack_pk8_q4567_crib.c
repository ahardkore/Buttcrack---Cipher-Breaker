/*
 * Exact crib attack for the tentative PK8 Q(4)+Q(5)+Q(6)+Q(7) hypothesis.
 *
 * The four additive wheels have 22 raw coordinates but only 18 effective
 * coordinates: three constant gauges plus one parity gauge shared by Q4/Q6.
 * We fix q4[0]=q4[1]=q5[0]=q6[0]=0.  Every consecutive 18-position design
 * matrix is invertible mod 26, so a crib placement determines the normalized
 * key exactly.  Extra crib letters are verified before full decryption.
 *
 * The dictionary filter accounts for all four gauges.  It accepts a normalized
 * key iff a gauge-equivalent set of literal 4-, 5-, 6-, and 7-letter words
 * occurs in the repository's broad dictionaries.
 *
 * Build from repository root:
 *   cc -O3 -march=native -fopenmp kryptos/crack_pk8_q4567_crib.c \
 *      -o /tmp/crack_pk8_q4567_crib -lm
 */

#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 153
#define NV 18
#define A 26
#define TOP 20
#define QSIZE (A*A*A*A)
#define SPACE4 (A*A)
#define SPACE5 (A*A*A*A)
#define SPACE6 (A*A*A*A*A)
#define H7SIZE 131072

static const char *KALPH="KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8=
    "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWO"
    "YIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUT"
    "HQCXNWPQZOIRJZGSWVPY";
static const char *CONTROL_PLAIN=
    "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWN"
    "TOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHS"
    "AYSHEMAKESONEE";

static int kindex[256],to_std[A],inv26[NV][NV];
static float *quad;
/* Q4 table: normalized signature -> parity gauge e -> first-letter mask a. */
static uint32_t q4mask[SPACE4][A];
static uint32_t *wordmask5,*wordmask6;
static uint32_t h7code[H7SIZE],h7mask[H7SIZE];
static unsigned char h7used[H7SIZE];

typedef struct {
    float score;
    int offset;
    char crib[65],word_keys[40],plain[N+1];
    unsigned char key[NV];
} Hit;

static inline int qidx(int a,int b,int c,int d){return ((a*A+b)*A+c)*A+d;}
static inline uint32_t tuple_code(const int *x,int n){uint32_t z=0;for(int i=0;i<n;i++)z=z*A+(uint32_t)x[i];return z;}

static float *load_quads(void) {
    float *t=calloc(QSIZE,sizeof(*t));if(!t)exit(2);
    FILE *f=popen("gzip -cd -- 'buttcrack/data/english_quadgrams.txt.gz'","r");
    if(!f){fprintf(stderr,"cannot load quadgrams\n");exit(2);}
    char line[128],g[8];long long count,total=0;
    while(fgets(line,sizeof(line),f)) {
        if(sscanf(line,"%7s %lld",g,&count)!=2||strlen(g)!=4)continue;
        int a=g[0]-'A',b=g[1]-'A',c=g[2]-'A',d=g[3]-'A';
        if(a<0||a>=A||b<0||b>=A||c<0||c>=A||d<0||d>=A)continue;
        t[qidx(a,b,c,d)]=(float)count;total+=count;
    }
    if(pclose(f)!=0||!total){fprintf(stderr,"bad quadgram model\n");exit(2);}
    float lt=(float)log10((double)total),floor=(float)log10(0.1/(double)total);
    for(int i=0;i<QSIZE;i++)t[i]=t[i]>0?log10f(t[i])-lt:floor;
    return t;
}

static int egcd_inv(int x){x%=A;if(x<0)x+=A;for(int y=1;y<A;y++)if((x*y)%A==1)return y;return -1;}

static void build_inverse(int offset) {
    int m[NV][2*NV];memset(m,0,sizeof(m));
    for(int row=0;row<NV;row++) {
        int i=offset+row;
        /* q4[2..3], q5[1..4], q6[1..5], q7[0..6]. */
        if(i%4>=2)m[row][i%4-2]=1;
        if(i%5)m[row][2+i%5-1]=1;
        if(i%6)m[row][6+i%6-1]=1;
        m[row][11+i%7]=1;
        m[row][NV+row]=1;
    }
    for(int c=0;c<NV;c++) {
        int p=-1,iv=-1;
        for(int r=c;r<NV;r++)if((iv=egcd_inv(m[r][c]))>=0){p=r;break;}
        if(p<0){fprintf(stderr,"18-window matrix not invertible at offset %d col %d\n",offset,c);exit(2);}
        if(p!=c)for(int j=0;j<2*NV;j++){int z=m[c][j];m[c][j]=m[p][j];m[p][j]=z;}
        iv=egcd_inv(m[c][c]);
        for(int j=0;j<2*NV;j++)m[c][j]=(m[c][j]*iv)%A;
        for(int r=0;r<NV;r++)if(r!=c){int z=m[r][c];for(int j=0;j<2*NV;j++){m[r][j]=(m[r][j]-z*m[c][j])%A;if(m[r][j]<0)m[r][j]+=A;}}
    }
    for(int i=0;i<NV;i++)for(int j=0;j<NV;j++)inv26[i][j]=m[i][NV+j];
}

static void add_word(const char *w,int len) {
    int v[7],d[6];for(int i=0;i<len;i++){v[i]=kindex[(unsigned char)w[i]];if(v[i]<0)return;}
    if(len==4) {
        int d2=(v[2]-v[0]+A)%A,d31=(v[3]-v[1]+A)%A,e=(v[1]-v[0]+A)%A;
        q4mask[d2*A+d31][e]|=UINT32_C(1)<<v[0];return;
    }
    for(int i=1;i<len;i++)d[i-1]=(v[i]-v[0]+A)%A;
    uint32_t bit=UINT32_C(1)<<v[0];
    if(len==5)wordmask5[tuple_code(d,4)]|=bit;
    else if(len==6)wordmask6[tuple_code(d,5)]|=bit;
    else if(len==7){uint32_t code=tuple_code(d,6),at=(code*UINT32_C(2654435761))&(H7SIZE-1);while(h7used[at]&&h7code[at]!=code)at=(at+1)&(H7SIZE-1);h7used[at]=1;h7code[at]=code;h7mask[at]|=bit;}
}

static void build_word_filter(void) {
    wordmask5=calloc(SPACE5,sizeof(*wordmask5));wordmask6=calloc(SPACE6,sizeof(*wordmask6));
    if(!wordmask5||!wordmask6){fprintf(stderr,"word-filter allocation failed\n");exit(2);}
    const char *paths[]={"kryptos/all_words.txt","kryptos/words_4.txt","kryptos/words_5.txt","kryptos/words_6.txt","kryptos/words_7.txt"};
    long long loaded[8]={0};
    for(int fno=0;fno<5;fno++) {
        FILE *f=fopen(paths[fno],"r");if(!f){perror(paths[fno]);exit(2);}char line[128];
        while(fgets(line,sizeof(line),f)) {
            char w[8];int n=0,letters=0;
            for(int i=0;line[i];i++)if(line[i]>='A'&&line[i]<='Z'){letters++;if(n<7)w[n++]=line[i];}
            if(letters<4||letters>7)continue;
            w[n]=0;add_word(w,n);loaded[n]++;
        }
        fclose(f);
    }
    printf("word-filter entries loaded: len4=%lld len5=%lld len6=%lld len7=%lld\n",loaded[4],loaded[5],loaded[6],loaded[7]);
}

static uint32_t lookup7(uint32_t code){uint32_t at=(code*UINT32_C(2654435761))&(H7SIZE-1);while(h7used[at]){if(h7code[at]==code)return h7mask[at];at=(at+1)&(H7SIZE-1);}return 0;}

static int word_key_hit(const unsigned char key[NV],char out[40]) {
    uint32_t m5=wordmask5[tuple_code((int[]){key[2],key[3],key[4],key[5]},4)];if(!m5)return 0;
    int d7[6];for(int i=0;i<6;i++){d7[i]=(key[12+i]-key[11]+A)%A;}
    uint32_t m7=lookup7(tuple_code(d7,6));if(!m7)return 0;
    uint32_t sig=(uint32_t)key[0]*A+key[1];
    for(int e=0;e<A;e++) {
        uint32_t ma=q4mask[sig][e];if(!ma)continue;
        int d6[5];for(int i=1;i<6;i++)d6[i-1]=(key[6+i-1]-(i&1?e:0)+A)%A;
        uint32_t m6=wordmask6[tuple_code(d6,5)];if(!m6)continue;
        for(int a=0;a<A;a++)if(ma&(UINT32_C(1)<<a))
            for(int b=0;b<A;b++)if(m5&(UINT32_C(1)<<b))
                for(int c=0;c<A;c++)if(m6&(UINT32_C(1)<<c)) {
                    int d=(key[11]-a-b-c)%A;if(d<0)d+=A;
                    if(!(m7&(UINT32_C(1)<<d)))continue;
                    int p=0;
                    int q4[4]={a,(a+e)%A,(a+key[0])%A,(a+e+key[1])%A};
                    for(int i=0;i<4;i++)out[p++]=KALPH[q4[i]];
                    out[p++]='/';
                    for(int i=0;i<5;i++)out[p++]=KALPH[((i?key[1+i]:0)+b)%A];
                    out[p++]='/';
                    for(int i=0;i<6;i++){int z=(i?key[5+i]:0)+c-(i&1?e:0);z%=A;if(z<0)z+=A;out[p++]=KALPH[z];}
                    out[p++]='/';
                    for(int i=0;i<7;i++){int z=key[11+i]-a-b-c;z%=A;if(z<0)z+=A;out[p++]=KALPH[z];}
                    out[p]=0;return 1;
                }
    }
    return 0;
}

static inline int plain_at(const int ct[N],const unsigned char key[NV],int i) {
    int q4=(i%4<2)?0:key[i%4-2];
    int q5=(i%5)?key[2+i%5-1]:0;
    int q6=(i%6)?key[6+i%6-1]:0;
    int x=(ct[i]-q4-q5-q6-key[11+i%7])%A;if(x<0)x+=A;return x;
}

static int crib_matches(const int ct[N],const unsigned char key[NV],const char *crib,int off,int len) {
    for(int j=NV;j<len;j++)if(plain_at(ct,key,off+j)!=kindex[(unsigned char)crib[j]])return 0;
    return 1;
}

static float decrypt_score(const int ct[N],const unsigned char key[NV],char out[N+1]) {
    int p[N];for(int i=0;i<N;i++){int x=plain_at(ct,key,i);p[i]=to_std[x];out[i]=(char)('A'+p[i]);}out[N]=0;
    float s=0;for(int i=0;i<=N-4;i++)s+=quad[qidx(p[i],p[i+1],p[i+2],p[i+3])];return s/(N-3);
}

static void insert_hit(Hit top[TOP],const Hit *h){if(h->score<=top[TOP-1].score)return;int i=TOP-1;while(i>0&&h->score>top[i-1].score){top[i]=top[i-1];i--;}top[i]=*h;}

static int load_cribs(const char *path,char (**out)[65]) {
    FILE *f=fopen(path,"r");if(!f){perror(path);exit(2);}int cap=4096,n=0;char(*a)[65]=malloc((size_t)cap*65),line[512];
    while(fgets(line,sizeof(line),f)){char clean[65];int k=0;for(int i=0;line[i]&&k<64;i++)if(line[i]>='A'&&line[i]<='Z')clean[k++]=line[i];if(k<NV)continue;clean[k]=0;if(n==cap){cap*=2;a=realloc(a,(size_t)cap*65);if(!a)exit(2);}strcpy(a[n++],clean);}
    fclose(f);*out=a;return n;
}

static void encrypt_control(int ct[N]) {
    const char *w4="IRON",*w5="STEEL",*w6="SILVER",*w7="DRAWING";
    for(int i=0;i<N;i++)ct[i]=(kindex[(unsigned char)CONTROL_PLAIN[i]]+kindex[(unsigned char)w4[i%4]]+kindex[(unsigned char)w5[i%5]]+kindex[(unsigned char)w6[i%6]]+kindex[(unsigned char)w7[i%7]])%A;
}

int main(int argc,char **argv) {
    int self=argc==2&&!strcmp(argv[1],"--self-test");
    int all=argc==3&&(!strcmp(argv[1],"--word-filter-all-offsets")||!strcmp(argv[1],"--all-keys-all-offsets"));
    int prefix=argc==3&&(!strcmp(argv[1],"--word-filter")||!strcmp(argv[1],"--all-keys"));
    int dict_filter=self||(argc==3&&(!strcmp(argv[1],"--word-filter")||!strcmp(argv[1],"--word-filter-all-offsets")));
    if(!(self||all||prefix)){fprintf(stderr,"usage: %s --self-test | --word-filter CRIB_FILE | --word-filter-all-offsets CRIB_FILE | --all-keys CRIB_FILE | --all-keys-all-offsets CRIB_FILE\n",argv[0]);return 2;}
    if(strlen(PK8)!=N||strlen(CONTROL_PLAIN)!=N){fprintf(stderr,"internal length error PK8=%zu control=%zu\n",strlen(PK8),strlen(CONTROL_PLAIN));return 2;}
    memset(kindex,-1,sizeof(kindex));for(int i=0;i<A;i++){kindex[(unsigned char)KALPH[i]]=i;to_std[i]=KALPH[i]-'A';}
    quad=load_quads();if(dict_filter)build_word_filter();
    int ct[N];char(*cribs)[65]=NULL;int nc=0;
    if(self){encrypt_control(ct);cribs=malloc(2*65);strcpy(cribs[0],"THEWHITESMITHSWORK");strcpy(cribs[1],"THEMASTERTOOKSTEEL");nc=2;}
    else{for(int i=0;i<N;i++)ct[i]=kindex[(unsigned char)PK8[i]];nc=load_cribs(argv[2],&cribs);}
    int last=0;if(all)for(int i=0;i<nc;i++){int x=N-(int)strlen(cribs[i]);if(x>last)last=x;}
    long long placements=0;for(int i=0;i<nc;i++){int len=(int)strlen(cribs[i]);placements+=all?(len<=N?N-len+1:0):(len<=N);}
    printf("cribs=%d offsets=%d placements=%lld candidates=%lld threads=%d\n",nc,last+1,placements,placements,omp_get_max_threads());
    double t0=omp_get_wtime();Hit global[TOP];for(int i=0;i<TOP;i++)global[i].score=-1e30f;long long word_hits=0,full_hits=0;
    for(int off=0;off<=last;off++) {
        build_inverse(off);int base[NV];
        for(int v=0;v<NV;v++){int z=0;for(int j=0;j<NV;j++)z+=inv26[v][j]*ct[off+j];base[v]=z%A;}
        #pragma omp parallel
        {
            Hit local[TOP];for(int i=0;i<TOP;i++)local[i].score=-1e30f;
            #pragma omp for schedule(dynamic,64)
            for(int ci=0;ci<nc;ci++) {
                int len=(int)strlen(cribs[ci]);if(off+len>N)continue;int pv[NV],keyv[NV];
                for(int j=0;j<NV;j++)pv[j]=kindex[(unsigned char)cribs[ci][j]];
                for(int v=0;v<NV;v++){int z=0;for(int j=0;j<NV;j++)z+=inv26[v][j]*pv[j];keyv[v]=(base[v]-z)%A;if(keyv[v]<0)keyv[v]+=A;}
                Hit h;h.word_keys[0]=0;for(int v=0;v<NV;v++)h.key[v]=(unsigned char)keyv[v];
                if(dict_filter) {
                    if(!word_key_hit(h.key,h.word_keys))continue;
                    #pragma omp atomic
                    word_hits++;
                }
                if(!crib_matches(ct,h.key,cribs[ci],off,len))continue;
                #pragma omp atomic
                full_hits++;
                h.score=decrypt_score(ct,h.key,h.plain);h.offset=off;strcpy(h.crib,cribs[ci]);insert_hit(local,&h);
            }
            #pragma omp critical
            {for(int i=0;i<TOP;i++)insert_hit(global,&local[i]);}
        }
        if(all&&(off%16==15||off==last))fprintf(stderr,"offset %d/%d%s\n",off,last,global[0].score>-1e20f?" survivor":" no full-crib survivor");
    }
    double elapsed=omp_get_wtime()-t0;printf("elapsed=%.3fs rate=%.3f million placements/s word_key_hits=%lld full_crib_hits=%lld\n",elapsed,placements/elapsed/1e6,word_hits,full_hits);
    for(int n=0;n<TOP;n++)if(global[n].score>-1e20f){Hit*h=&global[n];printf("\n#%d score=%.6f offset=%d crib=%s",n+1,h->score,h->offset,h->crib);if(h->word_keys[0])printf(" word_keys=%s",h->word_keys);printf("\nplaintext=%s\n",h->plain);}
    if(self){int ok=global[0].score>-1e20f&&!strcmp(global[0].plain,CONTROL_PLAIN)&&strstr(global[0].word_keys,"IRON/STEEL/SILVER/DRAWING");printf("self_test_exact=%s\n",ok?"PASS":"FAIL");free(cribs);return ok?0:1;}
    free(cribs);return 0;
}
