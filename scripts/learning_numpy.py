"""Array counts, quadrature probits and integrated alternative evidence."""
import csv,sys
import numpy as np
from learning_io import rows,normal_rows

N,W=np.polynomial.legendre.leggauss(320)
def integrate(f,lo,hi):
    x=(N+1)*(hi-lo)/2+lo
    return float(np.sum(W*f(x))*(hi-lo)/2)
def cdf(z):
    if z <= -12: return 0.
    if z >= 12: return 1.
    return integrate(lambda x:np.exp(-x*x/2)/np.sqrt(2*np.pi),-12,z)
def quantile(p):
    lo,hi=-9.,9.
    for _ in range(65):
        mid=(lo+hi)/2
        if cdf(mid)<p: lo=mid
        else: hi=mid
    return (lo+hi)/2

def screen(path):
    data=rows(path);t=np.array([float(r['exit_month']) for r in data]);s=np.array([r['intention'] for r in data]);y=np.array([r['label'] for r in data]);e=t>3;sc=e&(s!='');known=sc&(y!='')
    tp,fp,fn,tn=[int(np.count_nonzero(known&(s==a)&(y==b))) for a,b in [('1','1'),('1','0'),('0','1'),('0','0')]]
    up=int(np.count_nonzero(sc&(y=='')&(s=='1')));un=int(np.count_nonzero(sc&(y=='')&(s=='0')))
    v=dict(total=len(data),eligible=int(e.sum()),scorable=int(sc.sum()),known=int(known.sum()),unknown=up+un,positive_unknown=up,negative_unknown=un,tp=tp,fp=fp,fn=fn,tn=tn)
    if min(tp+fn,fp+tn,tp+fp)==0: raise ValueError('Screen denominators are zero')
    h,f=tp/(tp+fn),fp/(fp+tn)
    v.update(hit=h,false_alarm=f,ppv=tp/(tp+fp),coverage=float(sc.sum()/e.sum()),hit_low=tp/(tp+fn+un),hit_high=(tp+up)/(tp+fn+up),ppv_low=tp/(tp+fp+up),ppv_high=(tp+up)/(tp+fp+up),raw_probit_defined=int(0<h<1 and 0<f<1))
    if v['raw_probit_defined']:
        z=np.array([quantile(h),quantile(f)]);v.update(d_prime=float(z[0]-z[1]),criterion=float(-z.mean()))
    return v

def normal(r):
    y,s,t=[r[k] for k in ('estimate_pp','se_pp','prior_sd_pp')]
    density=lambda x,mu,sd:np.exp(-((x-mu)/sd)**2/2)/(sd*np.sqrt(2*np.pi))
    evidence=integrate(lambda x:density(y,x,s)*density(x,0,t),-12*t,12*t)
    first=integrate(lambda x:x*density(y,x,s)*density(x,0,t),-12*t,12*t)/evidence
    second=integrate(lambda x:(x-first)**2*density(y,x,s)*density(x,0,t),-12*t,12*t)/evidence
    sd=float(np.sqrt(second));z=quantile(.975)
    return dict(mean=first,sd=sd,lo95=first-z*sd,hi95=first+z*sd,p_negative=cdf(-first/sd),p_benefit=cdf((-r['margin_pp']-first)/sd),bf01=float(density(y,0,s)/evidence))

if __name__=='__main__':
    out=csv.writer(sys.stdout)
    if sys.argv[1]=='screen': out.writerows(sorted(screen(sys.argv[2]).items()))
    else:
        for r in normal_rows(sys.argv[2]): out.writerows((r['case']+'/'+k,v) for k,v in normal(r).items())
