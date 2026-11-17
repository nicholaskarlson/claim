"""Verify the two unfamiliar-method cases and their failure controls."""
import argparse,csv,io,json,math,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from check_s5 import ROOT,require,sha
from learning_io import rows,normal_rows

ROUTES={'numpy':'learning_numpy.py','stdlib':'learning_scalar.py','base_r':'learning_base.R'}
def load(p): return json.loads(p.read_text())
def calculate(command,mode,path):
    out=subprocess.check_output([*map(str,command),mode,str(path)],text=True,timeout=40)
    pairs=list(csv.reader(io.StringIO(out)));result={k:float(v) for k,v in pairs}
    require(len(pairs)==len(result) and all(math.isfinite(v) for v in result.values()),'Invalid learning-route output')
    return result

def compare(runs,tol):
    reference=runs['numpy']
    for name,run in runs.items():
        require(run.keys()==reference.keys(),f'{name}: learning inventory differs')
        require(all(abs(run[k]-reference[k])<=tol for k in run),f'{name}: learning results disagree')

def fixture(engines):
    path=ROOT/'fixtures/learning/screen.csv'
    runs={k:calculate(c,'screen',path) for k,c in engines.items()};compare(runs,2e-9)
    expected={'total':8,'eligible':7,'scorable':6,'known':4,'unknown':2,'tp':1,'fp':1,'fn':1,'tn':1,'hit':.5,'false_alarm':.5,'ppv':.5,'hit_low':1/3,'hit_high':2/3,'ppv_low':1/3,'ppv_high':2/3,'d_prime':0,'criterion':0}
    require(all(abs(runs['numpy'][k]-v)<2e-9 for k,v in expected.items()),'Wrong exact screening example')
    normals={k:calculate(c,'normal',ROOT/'fixtures/learning/normal.csv') for k,c in engines.items()};compare(normals,2e-9)
    require(abs(normals['numpy']['symmetric/bf01']-math.sqrt(2))<2e-9 and abs(normals['numpy']['symmetric/sd']**2-.5)<2e-9,'Wrong symmetric normal fixture')
    with tempfile.TemporaryDirectory(prefix='claim-learning-') as d:
        p=Path(d)/'screen.csv';original=path.read_text()
        for invalid in (original+original.splitlines()[1]+'\n',original.replace('F1,A,1,12,1','F1,A,2,12,1')):
            p.write_text(invalid)
            for command in engines.values():
                result=subprocess.run([*map(str,command),'screen',str(p)],capture_output=True,timeout=40)
                require(result.returncode!=0,'Invalid screening record accepted')
        p.write_text(original.replace('F2,A,1,12,0','F2,A,0,12,0'))
        for command in engines.values():
            result=calculate(command,'screen',p)
            require(result['raw_probit_defined']==0 and 'd_prime' not in result,'Extreme raw probit reported as finite')
        for value in ('0','nan'):
            p.write_text('case,estimate_pp,se_pp,margin_pp,prior_sd_pp\nbad,0,'+value+',1,1\n')
            for command in engines.values():
                result=subprocess.run([*map(str,command),'normal',str(p)],capture_output=True,timeout=40)
                require(result.returncode!=0,'Invalid normal reference accepted')
    return {'screen':runs['numpy'],'normal':normals['numpy'],'controls':{'duplicate_refused':True,'invalid_screen_refused':True,'zero_se_refused':True,'nonfinite_refused':True,'extreme_raw_probit_undefined':True}}

def printed(screen,normal):
    def pp(x):return f'{x:+.2f}'.replace('-','−')
    p={f'L14_{k.upper()}':f'{screen[k]:,.0f}' for k in ('total','eligible','scorable','known','unknown','positive_unknown','negative_unknown','tp','fp','fn','tn')}
    p.update({f'L14_{k.upper()}':f'{100*screen[k]:.2f}%' for k in ('hit','false_alarm','ppv','coverage','hit_low','hit_high','ppv_low','ppv_high')})
    p['L14_DPRIME']=f"{screen['d_prime']:.3f}";p['L14_CRITERION']=f"{screen['criterion']:.3f}"
    for t in (1,3,10):
        prefix=f'prior{t}/';p[f'L14_PRIOR{t}_MEAN']=pp(normal[prefix+'mean']);p[f'L14_PRIOR{t}_CI']=pp(normal[prefix+'lo95'])+' to '+pp(normal[prefix+'hi95'])
        for k in ('p_negative','p_benefit'):p[f'L14_PRIOR{t}_{k.upper()}']=f'{100*normal[prefix+k]:.1f}%'
        p[f'L14_PRIOR{t}_BF01']=f'{normal[prefix+"bf01"]:.3f}'
    p['L14_SCREEN_SENTENCE']=(f"Among {p['L14_KNOWN']} eligible Tonmick entrants with a month-three intention response and a known outcome, the hit rate was {p['L14_HIT']} and the false-alarm rate {p['L14_FALSE_ALARM']}.")
    p['L14_BAYES_SENTENCE']=(f"Under the fixed normal working likelihood and a zero-centered normal prior with SD three percentage points, the posterior probability within H1 of a reduction beyond two points is {p['L14_PRIOR3_P_BENEFIT']}.")
    return p

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path);parser.add_argument('--fixture-only',action='store_true');args=parser.parse_args()
    r=os.environ.get('CLAIM_RSCRIPT') or shutil.which('Rscript');require(r,'Actual base R required')
    engines={key:[r if key=='base_r' else sys.executable,ROOT/'scripts'/name] for key,name in ROUTES.items()}
    test=fixture(engines)
    if args.fixture_only: print('BOOK11_LEARNING_FIXTURE_OK routes=3 refusal_controls=4 extreme_probit=undefined');return
    require(args.out,'--out required');specpath=ROOT/'config/learning.json';spec=load(specpath)
    for name,want in spec['pinned'].items():require(sha(ROOT/name)==want,'Changed learning source: '+name)
    require(spec['landmark']==3 and spec['horizon']==12 and spec['primary_prior_sd_pp']==3,'Learning timing or primary prior differs')
    require(spec['prior_sd_pp']==[1,3,10] and spec['margin_pp']==2,'Prior sensitivity or teaching margin changed')
    screen={key:calculate(c,'screen',ROOT/spec['screen_input']) for key,c in engines.items()};compare(screen,spec['absolute_tolerance'])
    require(all(screen['numpy'][k]==v for k,v in {'total':1600,'eligible':1485,'scorable':1002,'known':995,'unknown':7,'tp':66,'fp':91,'fn':35,'tn':803}.items()),'Book 10 screen frame differs')
    prior_path=args.out.parent/'precision-receipt.json';prior=load(prior_path)
    require(prior['contract']=='B11-U9-MARGIN-v1' and prior['book9_rerun_sha256']==sha(ROOT/'private/evidence/book9-design-rerun.json'),'Normal reference source mismatch')
    normal={}
    with tempfile.TemporaryDirectory(prefix='claim-normal-') as directory:
        path=Path(directory)/'normal.csv'
        for key,command in engines.items():
            source=prior['model_by_route'][key];estimate=source['model/estimate'];se=source['model/se']
            with path.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['case','estimate_pp','se_pp','margin_pp','prior_sd_pp']);w.writerows((f'prior{t}',estimate,se,spec['margin_pp'],t) for t in spec['prior_sd_pp'])
            normal[key]=calculate(command,'normal',path)
    compare(normal,spec['absolute_tolerance']);tokens=printed(screen['numpy'],normal['numpy'])
    require(all(printed(screen[k],normal[k])==tokens for k in engines),'Learning print values disagree')
    receipt={'contract':spec['id'],'admitted_topics':['R27','R28'],'contract_sha256':sha(specpath),'source_commit':spec['source_commit'],'scope':spec['scope'],'known_exposure':spec['known_exposure'],'screen_input_sha256':sha(ROOT/spec['screen_input']),'upstream_screen_receipt_sha256':sha(ROOT/'private/evidence/book10-screen-rerun.json'),'precision_receipt_sha256':sha(prior_path),'normal_reference':spec['bayesian_reference'],'normal_parameters':{'estimate_pp':prior['model_by_route']['numpy']['model/estimate'],'se_pp':prior['model_by_route']['numpy']['model/se'],'margin_pp':spec['margin_pp'],'prior_sd_pp':spec['prior_sd_pp']},'bf_direction':spec['bf_direction'],'probability_scope':spec['probability_scope'],'screen_by_route':screen,'normal_by_route':normal,'fixture':test,'printed':tokens}
    args.out.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n');print('BOOK11_LEARNING_OK routes=3 screen_known=995 prior_sensitivities=3')

if __name__=='__main__': main()
