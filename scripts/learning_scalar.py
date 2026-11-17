"""Scalar contingency arithmetic and conjugate normal model comparison."""
import csv,math,sys
from statistics import NormalDist
from learning_io import rows,normal_rows

def screen(path):
    data=rows(path); e=[r for r in data if float(r['exit_month'])>3]; s=[r for r in e if r['intention']!='']; k=[r for r in s if r['label']!='']
    tp=sum(r['intention']=='1' and r['label']=='1' for r in k);fp=sum(r['intention']=='1' and r['label']=='0' for r in k)
    fn=sum(r['intention']=='0' and r['label']=='1' for r in k);tn=sum(r['intention']=='0' and r['label']=='0' for r in k)
    up=sum(r['intention']=='1' and r['label']=='' for r in s);un=sum(r['intention']=='0' and r['label']=='' for r in s)
    v=dict(total=len(data),eligible=len(e),scorable=len(s),known=len(k),unknown=up+un,positive_unknown=up,negative_unknown=un,tp=tp,fp=fp,fn=fn,tn=tn)
    if min(tp+fn,fp+tn,tp+fp)==0: raise ValueError('Screen denominators are zero')
    h=tp/(tp+fn);f=fp/(fp+tn)
    v.update(hit=h,false_alarm=f,ppv=tp/(tp+fp),coverage=len(s)/len(e),hit_low=tp/(tp+fn+un),hit_high=(tp+up)/(tp+fn+up),ppv_low=tp/(tp+fp+up),ppv_high=(tp+up)/(tp+fp+up))
    v['raw_probit_defined']=int(0<h<1 and 0<f<1)
    if v['raw_probit_defined']:
        zh=NormalDist().inv_cdf(h);zf=NormalDist().inv_cdf(f)
        v.update(d_prime=zh-zf,criterion=-(zh+zf)/2)
    return v

def normal(r):
    y,s,t=(r[k] for k in ('estimate_pp','se_pp','prior_sd_pp'));v=1/(1/s**2+1/t**2);m=v*y/s**2;sd=math.sqrt(v)
    logbf=.5*math.log1p(t*t/(s*s))-.5*y*y*(1/(s*s)-1/(s*s+t*t))
    cdf=NormalDist(m,sd).cdf
    return dict(mean=m,sd=sd,lo95=m-NormalDist().inv_cdf(.975)*sd,hi95=m+NormalDist().inv_cdf(.975)*sd,p_negative=cdf(0),p_benefit=cdf(-r['margin_pp']),bf01=math.exp(logbf))

if __name__=='__main__':
    out=csv.writer(sys.stdout)
    if sys.argv[1]=='screen': out.writerows(sorted(screen(sys.argv[2]).items()))
    else:
        for r in normal_rows(sys.argv[2]): out.writerows((r['case']+'/'+k,v) for k,v in normal(r).items())
