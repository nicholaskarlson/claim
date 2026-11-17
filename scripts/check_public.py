"""Verify the public inventory, ordinary Tonmick cases and invented examples."""
import argparse,csv,hashlib,io,json,math,os,shutil,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_s5 import require,compare as score_compare
from check_part1 import validate as validate_assignment

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and not set(p.relative_to(root).parts)&{'.git','build','__pycache__','.venv'} and p.relative_to(root).as_posix()!='release.json'}
def verify_inventory(root=ROOT):
    require(not any(p.is_symlink() for p in root.rglob('*') if '.git' not in p.relative_to(root).parts),'Public symlink refused')
    release=json.loads((root/'release.json').read_text());require(release['schema']=='nekpress-claim-public-v1','Unknown public release')
    require(inventory(root)==release['files'],'Public files differ from the release inventory')
    return release

def calculate(command,*args):
    text=subprocess.check_output([*map(str,command),*map(str,args)],text=True,timeout=60)
    rows=list(csv.reader(io.StringIO(text)));values={k:float(v) for k,v in rows}
    require(len(values)==len(rows) and all(math.isfinite(v) for v in values.values()),'Invalid public calculation output')
    return values

def same(expected,result,tol,label):
    require(expected.keys()==result.keys(),label+': result inventory differs')
    require(all(math.isclose(expected[k],result[k],rel_tol=0,abs_tol=tol) for k in expected),label+': result differs')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=ROOT/'build/verified');parser.add_argument('--inventory-only',action='store_true');a=parser.parse_args()
    release=verify_inventory()
    if a.inventory_only: print('CLAIM_PUBLIC_INVENTORY_OK files='+str(len(release['files'])));return
    rscript=os.environ.get('CLAIM_RSCRIPT') or shutil.which('Rscript');require(rscript,'Install actual base R or set CLAIM_RSCRIPT')
    spec=json.loads((ROOT/'config/public-cases.json').read_text());require(spec['world_commit']==release['world_commit'],'World provenance differs')
    for name,entry in spec['datasets'].items():
        p=ROOT/name
        with p.open(newline='') as f:
            reader=csv.DictReader(f);rows=list(reader)
        require(reader.fieldnames==entry['fields'] and len(rows)==entry['rows'] and sha(p)==entry['sha256'],'Public dataset differs: '+name)
    data=ROOT/'data/ordinary';assignment=data/'baseline-offer.csv';registry=data/'observed-registry.csv';baseline=data/'baseline-items.csv'
    read=lambda p:list(csv.DictReader(p.open(newline='')))
    validate_assignment(read(assignment),read(registry))
    require({x["student_id"] for x in read(assignment)} == {x["student_id"] for x in read(registry) if x["responded_baseline"]=="1"},"Registry respondent roster differs")
    pairs,score_values=score_compare(baseline,rscript,spec['s5'],1e-12)
    scripts=ROOT/'scripts';engines={'numpy':sys.executable,'scalar':sys.executable,'base':rscript};suffix={'numpy':'numpy.py','scalar':'scalar.py','base':'base.R'}
    results={};joined=None;measurement_ids=None
    with tempfile.TemporaryDirectory(prefix='claim-public-') as name:
        temp=Path(name);p=temp/'normal.csv';settings=spec['normal_parameters']
        with p.open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['case','estimate_pp','se_pp','margin_pp','prior_sd_pp']);w.writerows((f'prior{t}',settings['estimate_pp'],settings['se_pp'],settings['margin_pp'],t) for t in settings['prior_sd_pp'])
        for route,interpreter in engines.items():
            suf=suffix[route];command=lambda stem:[interpreter,scripts/(stem+'_'+suf)]
            path=temp/route
            subprocess.run([*map(str,command('part1')),'withdrawal',str(assignment),str(path),str(registry)],check=True,timeout=60)
            values={k:float(v) for k,v in list(csv.reader((path/'values.csv').open()))[1:]}
            sample=list(csv.reader((path/'joined.csv').open()));require(joined is None or sample==joined,'Independent public joins differ');joined=sample
            run={'withdrawal':values,'observation':calculate(command('observation'),'registry',registry),'design':calculate(command('design'),'registry',assignment,registry),'visits':calculate(command('visits'),'ordinary',data/'visits-exposure.csv',assignment,*spec['visits_beta']),'synthesis':calculate(command('synthesis'),data/'synthesis-colleges.csv'),'screen':calculate(command('learning'),'screen',data/'month3-screen.csv'),'normal':calculate(command('learning'),'normal',p)}
            raw=subprocess.check_output([*map(str,command('measurement')),str(baseline),str(assignment),str(data/'month3-stress.csv'),str(spec['s5']['r'])],text=True,timeout=60)
            rows=list(csv.reader(io.StringIO(raw)));metrics={row[0]:float(row[1]) for row in rows if len(row)==2};ids=[row for row in rows if len(row)==3]
            require(measurement_ids is None or ids==measurement_ids,'Independent retest selections differ');measurement_ids=ids;run['measurement']=metrics
            for case,result in run.items():same(spec['expected'][case],result,spec['tolerances'][case],route+'/'+case)
            results[route]=run
    for name in ('s5','part1','observation','design','visits','forecast','precision','reproduction','synthesis','learning'):
        subprocess.run([sys.executable,scripts/('check_'+name+'.py'),'--fixture-only'],check=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    a.out.mkdir(parents=True,exist_ok=True)
    report={'schema':'nekpress-claim-public-check-v1','release':release['version'],'world_commit':release['world_commit'],'release_manifest_sha256':sha(ROOT/'release.json'),'files_verified':len(release['files']),'ordinary_groups':9,'routes':['NumPy','standard-library Python','base R'],'paired_ids_verified':len(pairs),'joined_rows_verified':len(joined)-1,'s5_by_route':score_values,'results':results,'inherited_not_refitted':spec['inherited_not_refitted'],'status':'passed'}
    (a.out/'public-check.json').write_text(json.dumps(report,indent=2)+'\n');print('CLAIM_PUBLIC_OK ordinary_groups=9 routes=3 fixtures=10 world='+spec['world_commit'])

if __name__=='__main__':main()
