"""Scalar fractions and independent score-product covariance for Chapter 7."""
from collections import defaultdict
from fractions import Fraction as F
from math import exp, fsum, sqrt

from visits_io import run


def dot(left,right):
    return fsum(a*b for a,b in zip(left,right))


def solve(matrix, target):
    augmented = [row+[value] for row,value in zip(matrix,target)]
    size = len(augmented)
    for i in range(size):
        pivot = max(range(i,size),key=lambda j:abs(augmented[j][i]))
        augmented[i],augmented[pivot]=augmented[pivot],augmented[i]
        row = augmented[i]
        scale = row[i]
        if not scale:
            raise ValueError("Singular visit model information")
        row[:] = [v/scale for v in row]
        for j,other in enumerate(augmented):
            if j != i:
                factor = other[i]
                other[:] = [a-factor*b for a,b in zip(other,row)]
    return [row[-1] for row in augmented]


def analyze(rows,beta):
    measurements = [(int(r["offer"]),int(r["visits"]),F(r["months"])) for r in rows]
    if any(t<=0 for _,_,t in measurements):
        raise ValueError("Exposure must be positive")
    values = {"raw/zeros":sum(y==0 for _,y,_ in measurements)}
    for arm in (0,1):
        pairs=[(y,t) for z,y,t in measurements if z==arm]
        n=len(pairs)
        visits=sum(y for y,_ in pairs)
        months=sum(t for _,t in pairs)
        stats={"n":n,"visits":visits,"months":float(months),"mean_count":visits/n,
               "aggregate_rate":float(visits/months),
               "mean_individual_rate":float(sum(y/t for y,t in pairs)/n)}
        values.update({f"arm{arm}/{key}":v for key,v in stats.items()})
    values.update({"raw/count_difference":values["arm1/mean_count"]-values["arm0/mean_count"],
                   "raw/rate_ratio":values["arm1/aggregate_rate"]/values["arm0/aggregate_rate"]})
    if not beta:
        return values

    n,k=len(rows),len(beta)
    grouped_counts=defaultdict(lambda:[[],[]])
    records=[]
    for row,(z,y,t) in zip(rows,measurements):
        c=row["college_id"]
        grouped_counts[c][z].append(y)
        x=[1,z,float(row["prior_grade"])-3,int(row["part_time"]),int(row["first_gen"])]
        mu=float(t)*exp(dot(x,beta))
        records.append((c,x,y,mu))
    estimate=sum(F(len(a)+len(b),n)*(F(sum(b),len(b))-F(sum(a),len(a)))
                 for a,b in grouped_counts.values())
    info=[[fsum(mu*x[i]*x[j] for _,x,_,mu in records) for j in range(k)] for i in range(k)]
    contrast=solve(info,[0,1,0,0,0])
    scores=defaultdict(list)
    for c,x,y,mu in records:
        scores[c].append(dot(x,contrast)*(y-mu))
    g=len(scores)
    row_se=sqrt(n/(n-k)*fsum(v*v for group in scores.values() for v in group))
    college_se=sqrt(g/(g-1)*(n-1)/(n-k)*fsum(fsum(group)**2 for group in scores.values()))
    score=max(abs(fsum(x[i]*(y-mu) for _,x,y,mu in records))/n for i in range(k))
    crit=2.131449545559323
    values.update({"design/colleges":g,"design/difference":float(estimate),"model/row_se":row_se,
                   "model/college_se":college_se,"model/score_max_per_row":score,
                   "model/college_lower":exp(beta[1]-crit*college_se),
                   "model/college_upper":exp(beta[1]+crit*college_se)})
    return values


if __name__=="__main__":
    run(analyze)
