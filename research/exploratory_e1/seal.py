"""Stream-hash E1 retained evidence and verify it without running native code."""
import argparse,json,pathlib,sys
from experiment import digest,LABEL

def verify(root,repo):
 r=json.loads((root/'completion-receipt.json').read_text());assert r['label']==LABEL and r['verdict']=='INCONCLUSIVE' and r['candidate_accepted'] is False
 for name,value in r['files'].items():
  p=pathlib.Path(name);assert not p.is_absolute() and '..' not in p.parts;assert digest(root/p)==value,name
 source={str(p.relative_to(repo)):digest(p) for p in sorted((repo/'research/exploratory_e1').rglob('*')) if p.is_file() and '__pycache__' not in p.parts};assert source==r['experiment_source_lock']
 integrity=json.loads((root/'source-integrity.json').read_text())
 for name,value in integrity['protected_files'].items():assert digest(repo/name)==value,name
 assert digest(repo/'research/exploratory_e1/candidate-engine.diff')==integrity['candidate_patch_sha256']
 verdict=json.loads((root/'performance-verdict.json').read_text());assert verdict['verdict']=='INCONCLUSIVE' and verdict['candidate_accepted'] is False and verdict['task15_status']=='BLOCKED'
 comparison=json.loads((root/'controlled-comparison.json').read_text());assert comparison['sample_count']==6000
 print(json.dumps({'verified_files':len(r['files']),'experiment_sources':len(source),'verdict':r['verdict'],'candidate_accepted':False,'receipt_sha256':digest(root/'completion-receipt.json')},indent=2))

def seal(root,repo):
 assert not (root/'completion-receipt.json').exists(),'Preserve the existing receipt'
 files={str(p.relative_to(root)):digest(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 source={str(p.relative_to(repo)):digest(p) for p in sorted((repo/'research/exploratory_e1').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 receipt={'schema':'exploratory-e1-completion-1','label':LABEL,'verdict':'INCONCLUSIVE','candidate_accepted':False,'baseline_commit':'5e8b11b4db8a0883969e7fe1405b048f419d7f07','files':files,'experiment_source_lock':source,'task15_status':'BLOCKED','scientific_approval_granted':False}
 (root/'completion-receipt.json').write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n');verify(root,repo)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['seal','verify']);ap.add_argument('--evidence',type=pathlib.Path,required=True);a=ap.parse_args();repo=pathlib.Path(__file__).resolve().parents[2]
 (seal if a.action=='seal' else verify)(a.evidence,repo)
