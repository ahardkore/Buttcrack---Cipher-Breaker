/* Joint PK9 Q(7)+Q(6)+Q(5) -> T(8) search.
 * This is an answer-free cryptanalytic tool: it searches arbitrary wheel
 * coordinates and the complete 8-column read order, scoring plaintext with
 * English quadgrams.  It is deliberately separate from the historical word
 * wheel campaigns, which only test dictionary-key hypotheses.
 */
#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 144
#define W 8
#define H 18
#define A 26
#define QSIZE (A*A*A*A)
static const char *ALPH="KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CTSTR="KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int ct[N], to_std[A];
static float *quad, *tri, *bi;

typedef struct { uint64_t x; } Rng;
static inline uint64_t rng(Rng *r){uint64_t x=r->x;x^=x>>12;x^=x<<25;x^=x>>27;r->x=x;return x*UINT64_C(2685821657736338717);}
static inline int ri(Rng *r,int n){return (int)(rng(r)%(uint64_t)n);}
static inline double ur(Rng *r){return (rng(r)>>11)*(1.0/9007199254740992.0);}
static inline int q4(int a,int b,int c,int d){return ((a*A+b)*A+c)*A+d;}
static inline int q3(int a,int b,int c){return (a*A+b)*A+c;}
static float *load_ngram(const char *path,int order,int size){
    float *t=calloc((size_t)size,sizeof(*t)); if(!t) exit(2); char cmd[512];
    snprintf(cmd,sizeof(cmd),"gzip -cd -- '%s'",path); FILE *f=popen(cmd,"r"); if(!f) exit(2);
    char g[8],line[128]; long long n,total=0;
    while(fgets(line,sizeof line,f)) if(sscanf(line,"%7s %lld",g,&n)==2 && (int)strlen(g)==order){
        int x[4]={0},ok=1; for(int i=0;i<order;i++){x[i]=g[i]-'A';if(x[i]<0||x[i]>=A)ok=0;} if(!ok)continue;
        int at=order==4?q4(x[0],x[1],x[2],x[3]):order==3?q3(x[0],x[1],x[2]):x[0]*A+x[1];
        t[at]=(float)n; total+=n;
    }
    pclose(f); if(!total) exit(2); float lt=log10f((float)total), floor=log10f(.1f/(float)total);
    for(int i=0;i<size;i++)t[i]=t[i]>0?log10f(t[i])-lt:floor; return t;
}
static void init(void){int idx[256];memset(idx,-1,sizeof idx);for(int i=0;i<A;i++){idx[(unsigned char)ALPH[i]]=i;to_std[i]=ALPH[i]-'A';}for(int i=0;i<N;i++)ct[i]=idx[(unsigned char)CTSTR[i]];quad=load_ngram("buttcrack/data/english_quadgrams.txt.gz",4,QSIZE);tri=load_ngram("buttcrack/data/english_trigrams.txt.gz",3,A*A*A);bi=load_ngram("buttcrack/data/english_bigrams.txt.gz",2,A*A);}

typedef struct {unsigned char q5[5],q6[6],q7[7],ord[8]; int pt[N]; float score, smooth;} State;
static inline float score_state(State *s){float q=0,t=0,b=0;for(int i=0;i<N-3;i++)q+=quad[q4(s->pt[i],s->pt[i+1],s->pt[i+2],s->pt[i+3])];for(int i=0;i<N-2;i++)t+=tri[q3(s->pt[i],s->pt[i+1],s->pt[i+2])];for(int i=0;i<N-1;i++)b+=bi[s->pt[i]*A+s->pt[i+1]];s->score=q/(N-3);s->smooth=.60f*s->score+.25f*t/(N-2)+.15f*b/(N-1);return s->smooth;}
static inline void build(State *s){for(int r=0;r<H;r++)for(int c=0;c<W;c++){int pos=r*W+c,src=s->ord[c]*H+r,key=s->q5[pos%5]+s->q6[pos%6]+s->q7[pos%7];int pk=(ct[src]-key)%A;if(pk<0)pk+=A;s->pt[pos]=to_std[pk];}score_state(s);}
static void randomize(State*s,Rng*r){s->q5[0]=s->q6[0]=0;for(int i=1;i<5;i++)s->q5[i]=ri(r,A);for(int i=1;i<6;i++)s->q6[i]=ri(r,A);for(int i=0;i<7;i++)s->q7[i]=ri(r,A);for(int i=0;i<W;i++)s->ord[i]=i;for(int i=W-1;i;i--){int j=ri(r,i+1);unsigned char x=s->ord[i];s->ord[i]=s->ord[j];s->ord[j]=x;}build(s);}
static unsigned char *coord(State*s,int x){if(x<4)return&s->q5[x+1];if(x<9)return&s->q6[x-3];return&s->q7[x-9];}
static void q_polish(State*s){for(int pass=0;pass<4;pass++){float before=s->smooth;for(int z=0;z<16;z++){unsigned char*v=coord(s,z),old=*v,best=old;float bs=s->smooth;for(int x=0;x<A;x++){*v=x;build(s);if(s->smooth>bs){bs=s->smooth;best=x;}}*v=best;build(s);}if(s->smooth<=before+1e-5f)break;}}
static void p_polish(State*s){for(int pass=0;pass<3;pass++){float before=s->smooth;for(int i=0;i<W-1;i++)for(int j=i+1;j<W;j++){unsigned char x=s->ord[i];s->ord[i]=s->ord[j];s->ord[j]=x;build(s);if(s->smooth<=before+1e-5f){x=s->ord[i];s->ord[i]=s->ord[j];s->ord[j]=x;build(s);}else before=s->smooth;}if(s->smooth<=before+1e-5f)break;}}
static void anneal(State*s,Rng*r,int steps){State best=*s;for(int st=0;st<steps;st++){State n=*s;int m=ri(r,100);if(m<58){unsigned char*v=coord(&n,ri(r,16));unsigned char old=*v;do *v=ri(r,A);while(*v==old);}else{int i=ri(r,W),j=ri(r,W);if(i==j)continue;unsigned char x=n.ord[i];n.ord[i]=n.ord[j];n.ord[j]=x;}build(&n);int ph=st%6000;double z=(double)ph/5999.0,temp=.45*pow(.012/.45,z),d=n.smooth-s->smooth;if(d>=0||ur(r)<exp(d/temp))*s=n;if(s->smooth>best.smooth)best=*s;if(ph==5999){*s=best;for(int k=0;k<2+ri(r,4);k++){if(ri(r,100)<60){unsigned char*v=coord(s,ri(r,16));*v=ri(r,A);}else{int i=ri(r,W),j=ri(r,W),x=s->ord[i];s->ord[i]=s->ord[j];s->ord[j]=x;}}build(s);}}*s=best;q_polish(s);p_polish(s);q_polish(s);}
static void print(const State*s,const char*tag){char p[N+1];for(int i=0;i<N;i++)p[i]='A'+s->pt[i];p[N]=0;printf("%s smooth=%.6f quad=%.6f\nq5=[",tag,s->smooth,s->score);for(int i=0;i<5;i++)printf("%d%s",s->q5[i],i==4?"]\n":",");printf("q6=[");for(int i=0;i<6;i++)printf("%d%s",s->q6[i],i==5?"]\n":",");printf("q7=[");for(int i=0;i<7;i++)printf("%d%s",s->q7[i],i==6?"]\n":",");printf("ord=[");for(int i=0;i<W;i++)printf("%d%s",s->ord[i],i==W-1?"]\n":",");printf("pt=%s\n",p);fflush(stdout);}
int main(int argc,char**argv){int rest=2000,steps=12000,threads=2;uint64_t seed=20261003;for(int i=1;i<argc;i++){if(!strcmp(argv[i],"--restarts")&&i+1<argc)rest=atoi(argv[++i]);else if(!strcmp(argv[i],"--steps")&&i+1<argc)steps=atoi(argv[++i]);else if(!strcmp(argv[i],"--seed")&&i+1<argc)seed=strtoull(argv[++i],0,10);else if(!strcmp(argv[i],"--threads")&&i+1<argc)threads=atoi(argv[++i]);}omp_set_num_threads(threads);init();State global;global.smooth=-1e30f;double t=omp_get_wtime();
#pragma omp parallel
{Rng r={seed^(UINT64_C(0x9e3779b97f4a7c15)*(omp_get_thread_num()+1))};if(!r.x)r.x=1;State local;local.smooth=-1e30f;
#pragma omp for schedule(dynamic,1)
for(int z=0;z<rest;z++){r.x^=UINT64_C(0xd1b54a32d192ed03)*(z+1);State s;randomize(&s,&r);anneal(&s,&r,steps);if(s.smooth>local.smooth)local=s;
#pragma omp critical
{if(s.smooth>global.smooth){global=s;char tag[64];snprintf(tag,sizeof tag,"best restart %d",z);print(&global,tag);}}}}
print(&global,"FINAL");printf("elapsed=%.3fs\n",omp_get_wtime()-t);return 0;}
