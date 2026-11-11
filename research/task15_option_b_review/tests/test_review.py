import copy,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from option_b.core import *
from option_b.tree import inventory,resolve_safe
from option_b.collect import command,protocol,macho
from option_b.validate import tree_check,semantics,validate
from option_b.workflow import write_bundle

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.tree=self.root/'tree';self.tree.mkdir();(self.tree/'a').write_text('alpha')
    def reject(self,code,fn):
        with self.assertRaisesRegex((ReviewError,OSError),code):fn()
    def test_full_directory_identity(self):
        a=inventory(self.tree,'fixture');b=inventory(self.tree,'fixture');self.assertEqual(a['tree_sha256'],b['tree_sha256']);self.assertEqual(a['status'],'CURRENT_BYTES_VERIFIED');tree_check(a)
    def test_partial_directory_identity(self):
        (self.tree/'escape').symlink_to('/outside/forbidden');a=inventory(self.tree,'fixture');self.assertEqual(a['status'],'CURRENT_BYTES_PARTIAL');tree_check(a)
    def test_symlink_redirection(self):
        (self.tree/'redirect').symlink_to(self.root/'outside');self.reject('SYMLINK_ESCAPE',lambda:resolve_safe(self.tree/'redirect',[self.tree]))
    def test_changing_file(self):
        def change(p):p.write_text('changed')
        a=inventory(self.tree,'fixture',after_read=change);self.assertEqual(a['status'],'CURRENT_BYTES_PARTIAL');self.assertTrue(any('CHANGED' in e['code'] for e in a['errors']))
    def test_missing_sdk(self):
        a=inventory(self.root/'no-sdk','sdk');self.assertEqual(a['status'],'MISSING_OR_UNAVAILABLE');tree_check(a)
    def test_unreadable_tree(self):
        with patch('option_b.tree.walk',side_effect=PermissionError('denied')):a=inventory(self.tree,'sdk')
        self.assertFalse(a['traversal_complete']);self.assertEqual(a['status'],'CURRENT_BYTES_PARTIAL')
    def test_duplicate_alias(self):
        os.link(self.tree/'a',self.tree/'b');(self.tree/'c').symlink_to('a');a=inventory(self.tree,'fixture');self.assertEqual(len(a['aliases']),2);self.assertEqual(a['entry_count'],4)
    def test_symlink_cycle(self):
        (self.tree/'x').symlink_to('y');(self.tree/'y').symlink_to('x');a=inventory(self.tree,'fixture');self.assertTrue(a['errors'])
    def fixture(self):
        t=inventory(self.tree,'sdk');compiler={'sha256':'1220c0afafa12a6ae599d097ee7cf8b87c6b4d8e3fbb9783cee6b319a80683ba'}
        d={'current-toolchain-lock':{'status':'CURRENT_BYTES_PARTIAL','closure_complete':False,'compiler':compiler,'missing':['pybind'],'trees':{'sdk':t}},'current-sdk-inventory':t,'python-pybind-closure':{'pybind11_status':'MISSING_OR_UNAVAILABLE'},'original-current-evidence-matrix':{'historical_toolchain_byte_continuity':False,'records':[{'historical_identity_status':'VERSION_ONLY','historical_sha256':None,'historical_byte_continuity_proven':False}]},'g8-equivalence-feasibility':{'status':'BLOCKED','actual_comparison_performed':False,'independent_evidence':[],'marker_window_subtraction_supported':False,'original_source_inline_mapping_complete':False},'g1-g10-impact-matrix':{'gates':[{'id':'G8_codegen'}]*10}}
        for v in ['baseline','candidate']:d[v+'-build-comparison']={'byte_equivalence':False,'current_compiler':compiler,'original':{'binding_compile_record':{'command':'clang++ -O3 -arch arm64'}}}
        return d
    def fail_mutation(self,path,value,code):
        d=self.fixture();at=d
        for key in path[:-1]:at=at[key]
        at[path[-1]]=value;self.reject(code,lambda:semantics(d))
    def test_valid_blocked_submission(self):semantics(self.fixture())
    def test_missing_python_pybind(self):self.fail_mutation(['python-pybind-closure','pybind11_status'],'CURRENT_BYTES_VERIFIED','MISSING_PYBIND')
    def test_wrong_compiler(self):self.fail_mutation(['current-toolchain-lock','compiler','sha256'],'0'*64,'WRONG_COMPILER')
    def test_historical_current_confusion(self):self.fail_mutation(['original-current-evidence-matrix','records',0,'historical_sha256'],'a'*64,'HISTORICAL_CURRENT')
    def test_incomplete_closure(self):self.fail_mutation(['current-toolchain-lock','closure_complete'],True,'INCOMPLETE_CLOSURE')
    def test_forged_reviewer_approval(self):self.reject('FORGED_REVIEWER',lambda:no_approval({'nested':{'independent_reviewer_acceptance':'approved'}}))
    def test_forged_g8_pass(self):self.fail_mutation(['g8-equivalence-feasibility','status'],'PASS','FORGED_G8')
    def test_unauthorized_protocol(self):
        (self.root/'docs').mkdir();(self.root/'docs/task15_tail_attribution_protocol_v1.3.0.json').write_text(json.dumps({'identity':{'sha256':'forged'}}));self.reject('UNAUTHORIZED_PROTOCOL',lambda:protocol(self.root))
    def test_unsupported_equivalence(self):self.fail_mutation(['baseline-build-comparison','byte_equivalence'],True,'UNSUPPORTED_EQUIVALENCE')
    def test_contradictory_flags(self):self.fail_mutation(['candidate-build-comparison','original','binding_compile_record','command'],'clang++ -O3 -O0 -arch arm64','CONTRADICTORY_BUILD')
    def test_missing_independent_evidence(self):self.fail_mutation(['g8-equivalence-feasibility','independent_evidence'],['invented signature'],'MISSING_INDEPENDENT')
    def test_unauthorized_native_command(self):self.reject('UNAUTHORIZED_EXECUTION',lambda:command(['python','native_solve.py']))
    def test_corrupted_output_identity(self):
        t=inventory(self.tree,'x');t['entries'][1]['sha256']='bad';self.reject('CORRUPTED_TREE',lambda:tree_check(t))
    def test_stale_bundle(self):self.reject('STALE_EVIDENCE',lambda:write_bundle(self.tree,self.root,{},{}))
    def test_duplicate_json(self):
        p=self.root/'dup.json';p.write_text('{"a":1,"a":2}');self.reject('DUPLICATE_JSON',lambda:read(p))
    def test_root_redirection(self):
        p=self.root/'redirect';p.symlink_to(self.tree);self.reject('ROOT_REDIRECTION',lambda:inventory(p,'x'))
    def test_forged_partial_as_complete(self):
        (self.tree/'x').symlink_to('/outside');t=inventory(self.tree,'x');t['closure_complete']=True;self.reject('INCOMPLETE_CLOSURE',lambda:tree_check(t))
    def test_macho_bounded_truncation(self):
        import struct
        p=self.root/'binary';p.write_bytes(struct.pack('<8I',0xfeedfacf,0x100000c,0,2,1,8,0,0));self.reject('MACHO_TRUNCATED',lambda:macho(p))

    def bundle_fixture(self):
        from option_b.validate import KINDS,DOCS
        from option_b.collect import PROTOCOL,BASE
        bundle=self.root/'bundle';bundle.mkdir();items=self.fixture();items.update({'negative-tests':{},'source-integrity':{'protected_files':{}}})
        for name in KINDS:(bundle/(name+'.json')).write_bytes(canonical({'schema':'option-b-1','kind':name,'authorization':AUTH,'data':items[name]}))
        for name in DOCS:(bundle/(name+'.md')).write_text('fixture')
        source=self.root/'source.py';source.write_text('original')
        receipt={'schema':'option-b-completion-1','authorization':AUTH,'protocol_sha256':PROTOCOL,'baseline_commit':BASE,'files':{p.name:file_sha(p) for p in bundle.iterdir()},'source_lock':{'source.py':file_sha(source)},'package_status':'PASS','scientific_recommendation':'BLOCKED'}
        (bundle/'completion-receipt.json').write_bytes(canonical(receipt));return bundle
    def test_bundle_roundtrip(self):
        bundle=self.bundle_fixture()
        with patch('option_b.validate.protocol'):self.assertTrue(validate(bundle,self.root)['validated'])
    def test_corrupted_bundle_file(self):
        bundle=self.bundle_fixture();(bundle/'reviewer-decision-template.md').write_text('corrupt')
        with patch('option_b.validate.protocol'):self.reject('CORRUPTED_OUTPUT',lambda:validate(bundle,self.root))
    def test_stale_source_lock(self):
        bundle=self.bundle_fixture();(self.root/'source.py').write_text('changed')
        with patch('option_b.validate.protocol'):self.reject('STALE_EVIDENCE',lambda:validate(bundle,self.root))
    def test_rehashed_forged_approval(self):
        bundle=self.bundle_fixture();p=bundle/'g8-equivalence-feasibility.json';v=read(p);v['authorization']['collection_authorized']=True;p.write_bytes(canonical(v));r=read(bundle/'completion-receipt.json');r['files'][p.name]=file_sha(p);(bundle/'completion-receipt.json').write_bytes(canonical(r))
        with patch('option_b.validate.protocol'):self.reject('SCHEMA_OR_APPROVAL',lambda:validate(bundle,self.root))

    def test_partial_traversal_retains_readable_entries(self):
        (self.tree/'blocked').mkdir();real=os.scandir
        def denied(path):
            if Path(path).name=='blocked':raise PermissionError('fixture denied')
            return real(path)
        with patch('option_b.tree.os.scandir',side_effect=denied):t=inventory(self.tree,'x')
        self.assertEqual(t['status'],'CURRENT_BYTES_PARTIAL');self.assertFalse(t['traversal_complete']);self.assertTrue(next(r for r in t['entries'] if r['path']=='a')['sha256'])
    def test_unauthorized_calibration_approval(self):
        self.reject('FORGED_REVIEWER',lambda:no_approval({'calibration_authorized':True}))

    def test_forged_route_authorization(self):
        self.reject('FORGED_G8_PASS',lambda:no_approval({'route1':{'authorized':True}}))
