"""Seal/verify E3 external bytes and delivered source, without execution/tracing."""
import argparse,json
from availability import ROOT,REPO,LABEL,sha
def sources():
 return {str(p.relative_to(REPO)):sha(p) for p in sorted((REPO/'research/exploratory_e3').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def run():
 parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
 receipt=ROOT/'completion-receipt.json'
 if args.verify:
  r=json.loads(receipt.read_text());assert r['sources']==sources()
  current={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p!=receipt}
  assert current==set(r['files']),('external file set changed',current.symmetric_difference(r['files']))
  for path,value in r['files'].items():assert sha(ROOT/path)==value,path
  print(json.dumps({'receipt_sha256':sha(receipt),'verified_files':len(r['files']),'verified_sources':len(r['sources']),'verdict':r['verdict']}))
 else:
  assert not receipt.exists()
  files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=receipt}
  with receipt.open('x') as f:json.dump({'label':LABEL,'verdict':'BLOCKED','campaign_closed':True,'files':files,'sources':sources(),'excludes':'This self-referential receipt only. Git delivery metadata stays in Git outside immutable receipt.','git_parent':'e6d562782a5d292b06d2db8e01acd1f2727e2932'},f,indent=2)
  print('sealed',len(files),'files',sha(receipt))
if __name__=='__main__':run()
