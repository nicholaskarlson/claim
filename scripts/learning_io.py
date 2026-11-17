"""Validate ordinary or invented learning-route records before computation."""
import csv
import math

FIELDS=('student_id','college_id','intention','exit_month','label')

def rows(path):
    with open(path,newline='') as f:
        reader=csv.DictReader(f)
        if tuple(reader.fieldnames)!=FIELDS: raise ValueError('Wrong screening schema')
        data=list(reader)
    if not data or len({r['student_id'] for r in data})!=len(data): raise ValueError('Duplicate or empty screening roster')
    for r in data:
        if not r['student_id'] or not r['college_id'] or r['intention'] not in {'','0','1'} or r['label'] not in {'','0','1'}:
            raise ValueError('Invalid screening code')
        t=float(r['exit_month'])
        if not math.isfinite(t) or not 0 <= t <=12: raise ValueError('Invalid observation time')
    return data

def normal_rows(path):
    with open(path,newline='') as f: data=list(csv.DictReader(f))
    if not data or len({r['case'] for r in data})!=len(data): raise ValueError('Duplicate normal case')
    for r in data:
        for key in ('estimate_pp','se_pp','margin_pp','prior_sd_pp'): r[key]=float(r[key])
        if not all(math.isfinite(r[k]) for k in ('estimate_pp','se_pp','margin_pp','prior_sd_pp')) or min(r['se_pp'],r['prior_sd_pp'])<=0 or r['margin_pp']<0:
            raise ValueError('Normal settings require finite values and positive SE and prior SD')
    return data
