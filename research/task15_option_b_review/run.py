#!/usr/bin/env python3
"""collect requires fresh bundle path; validate reads existing evidence only."""
import argparse,json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from option_b.workflow import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['collect','validate']);ap.add_argument('--bundle',type=Path,required=True);ap.add_argument('--test-results',type=Path);ap.add_argument('--regression-results',type=Path);args=ap.parse_args()
    repo=Path(__file__).resolve().parents[2]
    if args.action=='validate':print(json.dumps(validate(args.bundle,repo),indent=2));return
    require(args.test_results and args.regression_results,'TEST_EVIDENCE_REQUIRED');require(not args.bundle.exists(),'STALE_EVIDENCE_BUNDLE')
    tests=read(args.test_results);regressions=read(args.regression_results)
    require(tests['failures']==0 and tests['tests']>=18 and all(r['returncode']==0 for r in regressions['runs']),'TESTS_NOT_PASSING')
    start=time.monotonic();before=protected(repo);sources=source_lock(repo);hist=history();lock=collect();require(source_lock(repo)==sources and protected(repo)==before,'SOURCE_CHANGED_DURING_COLLECTION')
    lock['collection_elapsed_seconds']=time.monotonic()-start
    items,docs=prepare(repo,lock,hist,tests,regressions,before);print(json.dumps(write_bundle(args.bundle,repo,items,docs),indent=2))
if __name__=='__main__':main()
