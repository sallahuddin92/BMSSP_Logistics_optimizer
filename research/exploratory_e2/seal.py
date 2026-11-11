"""Hash and validate this retained E2 campaign; no native queries or approval."""
import argparse,json,pathlib,subprocess
from campaign import ROOT,REPO,LABEL,read,sha

def verify():
 receipt=read(ROOT/'completion-receipt.json');assert receipt['label']==LABEL and receipt['verdict']=='INCONCLUSIVE' and receipt['H1_assessment']=='STILL_INCONCLUSIVE'
 for name,value in receipt['files'].items():
  path=pathlib.Path(name);assert not path.is_absolute() and '..' not in path.parts;assert sha(ROOT/path)==value,name
 source={str(p.relative_to(REPO)):sha(p) for p in sorted((REPO/'research/exploratory_e2').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 assert source==receipt['source_lock']
 for name,value in read(ROOT/'source-integrity.json')['protected_files'].items():assert sha(REPO/name)==value,name
 for name,value in read(ROOT/'measurement-source-lock.json')['source_files'].items():assert sha(REPO/name)==value,name
 quality=read(ROOT/'primary-quality.json');assert quality['observations']==7200 and quality['clock_failures']==0 and quality['primary_exclusions']==[] and quality['cpu_outside_envelope']==0
 assert read(ROOT/'predeclared-plan-raw.json')['jobs']==read(ROOT/'predeclared-plan.json')['jobs']
 identities=read(ROOT/'build-identities-raw.json')
 assert identities['condition_executables']['A1']==identities['condition_executables']['A2']
 for v in ['A','B']:assert sha(ROOT/('build-raw-'+v)/'e2_worker')==identities['variants'][v]['executable_sha256']
 assessment=read(ROOT/'h1-acceptance-assessment.json');assert assessment['promoted'] is False and assessment['H1_assessment']=='STILL_INCONCLUSIVE'
 print(json.dumps({'label':LABEL,'verified':True,'files':len(receipt['files']),'sources':len(source),'verdict':'INCONCLUSIVE','H1_assessment':'STILL_INCONCLUSIVE','receipt_sha256':sha(ROOT/'completion-receipt.json')},indent=2))
def seal():
 assert not (ROOT/'completion-receipt.json').exists(),'Preserve existing receipt'
 source={str(p.relative_to(REPO)):sha(p) for p in sorted((REPO/'research/exploratory_e2').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 receipt={'schema':'exploratory-e2-completion-1','label':LABEL,'verdict':'INCONCLUSIVE','H1_assessment':'STILL_INCONCLUSIVE','primary_observations':7200,'files':files,'source_lock':source,'task15_status':'BLOCKED','algorithm_modified':False,'scientific_approval_granted':False}
 (ROOT/'completion-receipt.json').write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n');verify()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['seal','verify']);a=parser.parse_args();globals()[a.action]()
