#!/usr/bin/env python3
"""PK10 model-selection preflight.

This does not claim a solve. It records geometry, lag, and alphabet-index
statistics in one reproducible report before expensive key searches are run.
"""
from collections import Counter
from pathlib import Path
import argparse, json
CT="UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ"
A="KRYPTOSABCDEFGHIJLMNQUVWXZ"
def ioc(s):
 c=Counter(s); n=len(s); return sum(v*(v-1) for v in c.values())/(n*(n-1))
def lags(s, maxlag=120):
 out=[]
 for k in range(1,min(maxlag,len(s)-1)+1):
  m=sum(a==b for a,b in zip(s,s[k:])); exp=(len(s)-k)/26
  out.append((m/exp,k,m))
 return sorted(out,reverse=True)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--out',default='/tmp/pk10_architecture_sweep.json'); a=ap.parse_args()
 factors=[(w,len(CT)//w) for w in range(2,len(CT)+1) if len(CT)%w==0]
 report={"length":len(CT),"ioc":ioc(CT),"factors":factors,
  "top_lags":[{"lag":k,"ratio":round(r,4),"matches":m} for r,k,m in lags(CT)[:30]],
  "alphabet_counts":dict(sorted(Counter(A.index(c) for c in CT).items()))}
 Path(a.out).write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
if __name__=='__main__': main()
