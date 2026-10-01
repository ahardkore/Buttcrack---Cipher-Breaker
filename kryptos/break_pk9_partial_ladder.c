/*
 * PK9 partial-ladder attack: enumerate insertion-related Q5/Q6 dictionary
 * pairs, recover unrestricted Q7 statistically, and solve T8 by assignment.
 * No PK9 key or plaintext constants are used.
 *
 * Build/run from repository root:
 *   cc -std=c11 -O3 -march=native -fopenmp -Wall -Wextra -Werror \
 *      kryptos/break_pk9_partial_ladder.c -o /tmp/break_pk9_partial_ladder -lm
 *   OMP_NUM_THREADS=32 /tmp/break_pk9_partial_ladder --self-test
 *   OMP_NUM_THREADS=32 /tmp/break_pk9_partial_ladder
 */
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A 26
#define N 144
#define W 8
#define H 18
#define TOP 100
#define KEEP 500
#define QSIZE (A*A*A*A)
#define BSIZE (A*A)
#define MAX_WORDS 100000
#define STARTS 12
#define ALT_PASSES 12

static const char *KALPH="KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9=
 "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXL"
 "EHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQ"
 "GLHDKEWSKAMHIJXD";
static const char *CONTROL=
 "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWN"
 "TOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHE";
static int ki[256],to_std[A];
static double logmono[26];
static float *bi,*quad;

typedef struct { char text[9]; } Word;
typedef struct {
 float qs,bs,ms;
 char q5[6],q6[7],q7[8],plain[N+1];
 unsigned char order[W];
 int exact;
} Hit;
static Word *w5,*w6; static int n5,n6;

static inline int qi(int a,int b,int c,int d){return((a*A+b)*A+c)*A+d;}
static float *load_ng(const char *path,int order,int size){
 float*t=calloc((size_t)size,sizeof(*t));if(!t)exit(2);
 char cmd[512],line[128],g[8];long long count,total=0;
 snprintf(cmd,sizeof(cmd),"gzip -cd -- '%s'",path);FILE*f=popen(cmd,"r");if(!f)exit(2);
 while(fgets(line,sizeof(line),f)){
  if(sscanf(line,"%7s %lld",g,&count)!=2||(int)strlen(g)!=order)continue;
  int at;if(order==4){int a=g[0]-65,b=g[1]-65,c=g[2]-65,d=g[3]-65;if(a<0||a>=A||b<0||b>=A||c<0||c>=A||d<0||d>=A)continue;at=qi(a,b,c,d);}
  else{int a=g[0]-65,b=g[1]-65;if(a<0||a>=A||b<0||b>=A)continue;at=a*A+b;}
  t[at]=(float)count;total+=count;
 }
 if(pclose(f)||!total)exit(2);
 float lt=(float)log10((double)total),floor=(float)log10(0.1/(double)total);
 for(int i=0;i<size;i++)t[i]=t[i]>0?log10f(t[i])-lt:floor;
 return t;
}
static int cmpw(const void*a,const void*b){return strcmp(((const Word*)a)->text,((const Word*)b)->text);}
static void add(const char*path,int len,Word*out,int*n){
 FILE*f=fopen(path,"r");if(!f){perror(path);exit(2);}char line[256];
 while(fgets(line,sizeof(line),f)){char s[9];int k=0,letters=0;for(int i=0;line[i];i++)if(line[i]>='A'&&line[i]<='Z'){letters++;if(k<8)s[k++]=line[i];}if(letters!=len)continue;s[k]=0;if(*n>=MAX_WORDS)exit(2);strcpy(out[(*n)++].text,s);}fclose(f);
}
static int dedup(Word*w,int n){qsort(w,(size_t)n,sizeof(*w),cmpw);int o=0;for(int i=0;i<n;i++){if(o&&!strcmp(w[i].text,w[o-1].text))continue;w[o++]=w[i];}return o;}
static const Word*findw(const Word*w,int n,const char*s){Word p={{0}};strcpy(p.text,s);return bsearch(&p,w,(size_t)n,sizeof(*w),cmpw);}
static void load_words(void){
 w5=malloc(MAX_WORDS*sizeof(*w5));w6=malloc(MAX_WORDS*sizeof(*w6));if(!w5||!w6)exit(2);
 add("kryptos/all_words.txt",5,w5,&n5);add("kryptos/words_5.txt",5,w5,&n5);
 add("kryptos/all_words.txt",6,w6,&n6);add("kryptos/words_6.txt",6,w6,&n6);
 n5=dedup(w5,n5);n6=dedup(w6,n6);printf("dictionary words: len5=%d len6=%d\n",n5,n6);
}
static void vals(const char*w,int n,int*v){for(int i=0;i<n;i++)v[i]=ki[(unsigned char)w[i]];}
static uint64_t mix(uint64_t x){x^=x>>30;x*=UINT64_C(0xbf58476d1ce4e5b9);x^=x>>27;x*=UINT64_C(0x94d049bb133111eb);return x^(x>>31);}
static void start_order(unsigned char o[W],uint64_t seed){for(int i=0;i<W;i++)o[i]=(unsigned char)i;for(int i=W-1;i>0;i--){seed=mix(seed+(uint64_t)i);int j=(int)(seed%(unsigned)(i+1));unsigned char z=o[i];o[i]=o[j];o[j]=z;}}

static double derive_q7(const int ct[N],const int q5[5],const int q6[6],
                        const unsigned char order[W],int q7[7],int qfirst){
 double total=0;
 for(int phase7=0;phase7<7;phase7++){
  double best=-1e300;int bv=0;
  for(int shift=0;shift<A;shift++){
   double score=0;
   for(int r=0;r<H;r++)for(int c=0;c<W;c++){
    int pos=r*W+c,source=order[c]*H+r,phase=qfirst?pos:source;
    if(phase%7!=phase7)continue;
    int p=(ct[source]-q5[phase%5]-q6[phase%6]-shift)%A;if(p<0)p+=A;
    score+=logmono[to_std[p]];
   }
   if(score>best){best=score;bv=shift;}
  }
  q7[phase7]=bv;total+=best;
 }
 return total/(double)N;
}

static double assign_mono(const int ct[N],const int q5[5],const int q6[6],const int q7[7],
                          unsigned char order[W],int qfirst){
 double cost[W][W];
 for(int c=0;c<W;c++)for(int b=0;b<W;b++){
  double s=0;for(int r=0;r<H;r++){int pos=r*W+c,source=b*H+r,phase=qfirst?pos:source;
   int p=(ct[source]-q5[phase%5]-q6[phase%6]-q7[phase%7])%A;if(p<0)p+=A;s+=logmono[to_std[p]];}cost[c][b]=s;
 }
 double dp[1<<W];signed char parent[1<<W];for(int m=0;m<(1<<W);m++){dp[m]=-1e300;parent[m]=-1;}dp[0]=0;
 for(int mask=0;mask<(1<<W)-1;mask++){int c=__builtin_popcount((unsigned)mask);for(int b=0;b<W;b++)if(!(mask&(1<<b))){int nm=mask|(1<<b);double x=dp[mask]+cost[c][b];if(x>dp[nm]){dp[nm]=x;parent[nm]=(signed char)b;}}}
 int mask=(1<<W)-1;for(int c=W-1;c>=0;c--){int b=parent[mask];order[c]=(unsigned char)b;mask^=1<<b;}return dp[(1<<W)-1]/N;
}

static float assign_bigram(const int ct[N],const int q5[5],const int q6[6],const int q7[7],
                           unsigned char order[W],int qfirst){
 unsigned char d[W][W][H];
 for(int c=0;c<W;c++)for(int b=0;b<W;b++)for(int r=0;r<H;r++){int pos=r*W+c,source=b*H+r,phase=qfirst?pos:source;int p=(ct[source]-q5[phase%5]-q6[phase%6]-q7[phase%7])%A;if(p<0)p+=A;d[c][b][r]=(unsigned char)to_std[p];}
 float edge[W][W][W]={{{0}}},bound[W][W]={{0}};
 for(int c=1;c<W;c++)for(int a=0;a<W;a++)for(int b=0;b<W;b++)if(a!=b)for(int r=0;r<H;r++)edge[c][a][b]+=bi[d[c-1][a][r]*A+d[c][b][r]];
 for(int a=0;a<W;a++)for(int b=0;b<W;b++)if(a!=b)for(int r=0;r<H-1;r++)bound[a][b]+=bi[d[7][a][r]*A+d[0][b][r+1]];
 float best=-1e30f;unsigned char bo[W]={0};
 for(int first=0;first<W;first++){
  float dp[1<<W][W];signed char par[1<<W][W];for(int m=0;m<(1<<W);m++)for(int b=0;b<W;b++){dp[m][b]=-1e30f;par[m][b]=-1;}dp[1<<first][first]=0;
  for(int mask=1;mask<(1<<W);mask++){if(!(mask&(1<<first)))continue;int used=__builtin_popcount((unsigned)mask);if(used>=W)continue;for(int last=0;last<W;last++){float base=dp[mask][last];if(base<-1e20f)continue;for(int b=0;b<W;b++)if(!(mask&(1<<b))){int nm=mask|(1<<b);float x=base+edge[used][last][b];if(x>dp[nm][b]){dp[nm][b]=x;par[nm][b]=(signed char)last;}}}}
  int full=(1<<W)-1;for(int last=0;last<W;last++){float x=dp[full][last]+bound[last][first];if(x<=best)continue;best=x;int mask=full,at=last;for(int c=W-1;c>=0;c--){bo[c]=(unsigned char)at;int p=par[mask][at];mask^=1<<at;at=p;}}
 }
 memcpy(order,bo,W);return best/(N-1);
}

static Hit finish(const int ct[N],const char*w5s,const char*w6s,const int q5[5],const int q6[6],
                  const int q7[7],const unsigned char order[W],float bs,double ms,const char*truth,int qfirst){
 Hit h;strcpy(h.q5,w5s);strcpy(h.q6,w6s);for(int i=0;i<7;i++)h.q7[i]=KALPH[q7[i]];h.q7[7]=0;memcpy(h.order,order,W);h.bs=bs;h.ms=(float)ms;int p[N];h.exact=truth?1:0;
 for(int r=0;r<H;r++)for(int c=0;c<W;c++){int pos=r*W+c,source=order[c]*H+r,phase=qfirst?pos:source;int x=(ct[source]-q5[phase%5]-q6[phase%6]-q7[phase%7])%A;if(x<0)x+=A;p[pos]=to_std[x];h.plain[pos]=(char)(65+p[pos]);if(truth&&h.plain[pos]!=truth[pos])h.exact=0;}
 h.plain[N]=0;
 float s=0;for(int i=0;i<=N-4;i++)s+=quad[qi(p[i],p[i+1],p[i+2],p[i+3])];h.qs=s/(N-3);return h;
}
static void insert(Hit top[TOP],const Hit*h){if(h->qs<=top[TOP-1].qs)return;int at=TOP-1;while(at&&h->qs>top[at-1].qs){top[at]=top[at-1];at--;}top[at]=*h;}
static Hit attack_pair(const int ct[N],const char*w5s,const char*w6s,uint64_t seed,const char*truth,int qfirst){
 int q5[5],q6[6];vals(w5s,5,q5);vals(w6s,6,q6);Hit best={.qs=-1e30f};
 int starts=qfirst?STARTS:1;
 for(int st=0;st<starts;st++){
  unsigned char order[W];start_order(order,seed+(uint64_t)st*UINT64_C(0x9e3779b97f4a7c15));int q7[7];double ms=0;
  for(int pass=0;pass<ALT_PASSES;pass++){unsigned char old[W];memcpy(old,order,W);ms=derive_q7(ct,q5,q6,order,q7,qfirst);assign_mono(ct,q5,q6,q7,order,qfirst);if(!memcmp(old,order,W))break;}
  /* Bigram order and monogram Q7 alternation sharpens promising basins. */
  float bs=assign_bigram(ct,q5,q6,q7,order,qfirst);
  for(int pass=0;pass<3;pass++){derive_q7(ct,q5,q6,order,q7,qfirst);bs=assign_bigram(ct,q5,q6,q7,order,qfirst);}
  ms=derive_q7(ct,q5,q6,order,q7,qfirst);bs=assign_bigram(ct,q5,q6,q7,order,qfirst);
  Hit h=finish(ct,w5s,w6s,q5,q6,q7,order,bs,ms,truth,qfirst);if(h.qs>best.qs)best=h;
 }
 return best;
}
static void encrypt_control(int ct[N]){
 const char*a="IRATE",*b="PIRATE",*c="CAPTAIN",*t="LANGUAGE";int q5[5],q6[6],q7[7],ro[W];vals(a,5,q5);vals(b,6,q6);vals(c,7,q7);for(int i=0;i<W;i++)ro[i]=i;for(int i=1;i<W;i++){int v=ro[i],j=i-1;while(j>=0&&t[ro[j]]>t[v]){ro[j+1]=ro[j];j--;}ro[j+1]=v;}int z[N],o=0;for(int i=0;i<N;i++)z[i]=(ki[(unsigned char)CONTROL[i]]+q5[i%5]+q6[i%6]+q7[i%7])%A;for(int x=0;x<W;x++)for(int r=0;r<H;r++)ct[o++]=z[r*W+ro[x]];
}
static void print_hit(const Hit*h,int rank,const char*label){printf("\n%s #%d quad=%.6f bigram=%.6f mono=%.6f keys=%s/%s/%s exact=%d\norder=",label,rank,h->qs,h->bs,h->ms,h->q5,h->q6,h->q7,h->exact);for(int i=0;i<W;i++)printf("%d%s",h->order[i],i==W-1?"\n":",");printf("plaintext=%s\n",h->plain);}

int main(int argc,char**argv){
 int self=argc==2&&!strcmp(argv[1],"--self-test");if(argc!=1&&!self){fprintf(stderr,"usage: %s [--self-test]\n",argv[0]);return 2;}memset(ki,-1,sizeof(ki));for(int i=0;i<A;i++){ki[(unsigned char)KALPH[i]]=i;to_std[i]=KALPH[i]-65;}
 static const double freq[26]={.08167,.01492,.02782,.04253,.12702,.02228,.02015,.06094,.06966,.00153,.00772,.04025,.02406,.06749,.07507,.01929,.00095,.05987,.06327,.09056,.02758,.00978,.02360,.00150,.01974,.00074};for(int i=0;i<26;i++)logmono[i]=log(freq[i]);
 bi=load_ng("buttcrack/data/english_bigrams.txt.gz",2,BSIZE);quad=load_ng("buttcrack/data/english_quadgrams.txt.gz",4,QSIZE);load_words();int target[N];const char*truth=NULL;if(self){encrypt_control(target);truth=CONTROL;}else for(int i=0;i<N;i++)target[i]=ki[(unsigned char)PK9[i]];
 int self_ok=0,models=self?1:2;
 for(int model=0;model<models;model++){int qfirst=model==0;Hit global[TOP];for(int i=0;i<TOP;i++)global[i].qs=-1e30f;long long pairs=0,exact=0;double started=omp_get_wtime();
  #pragma omp parallel
  {Hit local[TOP];for(int i=0;i<TOP;i++)local[i].qs=-1e30f;long long lp=0,le=0;
   #pragma omp for schedule(dynamic,16)
   for(int i6=0;i6<n6;i6++){char seen[6][6];int ns=0;for(int cut=0;cut<6;cut++){char x[6];int o=0;for(int j=0;j<6;j++)if(j!=cut)x[o++]=w6[i6].text[j];x[o]=0;int dup=0;for(int j=0;j<ns;j++)if(!strcmp(x,seen[j]))dup=1;if(dup||!findw(w5,n5,x))continue;strcpy(seen[ns++],x);lp++;Hit h=attack_pair(target,x,w6[i6].text,(uint64_t)i6*17u+(unsigned)cut,truth,qfirst);if(h.exact)le++;insert(local,&h);}}
   #pragma omp atomic
   pairs+=lp;
   #pragma omp atomic
   exact+=le;
   #pragma omp critical
   {for(int i=0;i<TOP;i++)insert(global,&local[i]);}
  }
  double elapsed=omp_get_wtime()-started;printf("\n=== %s ===\npairs=%lld exact=%lld elapsed=%.3fs\n",qfirst?"Q5+Q6+Q7 THEN T8":"T8 THEN Q5+Q6+Q7",pairs,exact,elapsed);for(int i=0;i<10;i++)print_hit(&global[i],i+1,"RANK");if(self&&exact>0&&global[0].exact)self_ok=1;
 }
 free(w5);free(w6);free(bi);free(quad);return self&&!self_ok?1:0;
}
