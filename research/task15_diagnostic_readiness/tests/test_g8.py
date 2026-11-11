"""Deterministic ARM64 byte fixtures; no compiled/executed native engine."""
import copy
import difflib
from pathlib import Path
import struct
import tempfile
import unittest
from diagnostic.core import DiagnosticError,sha
from diagnostic.fixtures import MAGIC,attest
from diagnostic.codegen import compare,VerifiedEvidence
from diagnostic.manifest import validate,validate_source_edits,whitelist,original,FORBIDDEN
from task15_cohort_a_runner.frozen import protocol

ADD=0x91000400;NOP=0xd503201f;RET=0xd65f03c0

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=protocol().data()
    def fixture(self,words=(ADD,RET),**kwargs):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);file=Path(temp.name)/'synthetic.bin'
        data=MAGIC+struct.pack('<'+'I'*len(words),*words);file.write_bytes(data)
        return attest(file,sha(data),**kwargs)
    def pair(self,a,b,expected,**kwargs):
        result=compare(self.fixture(a),self.fixture(b,**kwargs));self.assertEqual(result['classification'],expected);return result
    def manifest(self):
        variant='baseline';commit=self.p['binaries'][variant]['source_commit'];path='native/src/bmssp_2025.cpp'
        return {'schema':'cohort-b-build-1','variant':variant,'source_commit':commit,'production_binary_sha256':self.p['binaries'][variant]['sha256'],
                'source_files':{path:sha(original(commit,path).encode())},'compiler':{'path':'fixture-compiler'},'sdk':{'path':'fixture-sdk'},
                'build_arguments':[{'directory':'/fixture','command':'fixture-compiler -O3 -DNDEBUG -std=c++20 -arch arm64 -isysroot fixture-sdk -fPIC -c x.cpp -o x.o','file':'x.cpp','output':'x.o'}],
                'linker':{'identity':'fixture'},'dependencies':{'identity':'fixture'},'permitted_insertions':whitelist(self.p,variant),'forbidden_compute_modifications':FORBIDDEN,
                'source_diff':[],'diagnostic_binary':None,'function_coverage':{},'g8_claim':None,'missing_prerequisites':[],
                'scientific_approval':'pending','layout_risk_approved':False,'calibration_authorized':False,'collection_authorized':False}
    def validate(self,value,artifact=False):return validate(value,self.p,{'path':'fixture-compiler'},{'path':'fixture-sdk'},self.manifest()['build_arguments'],require_artifact=artifact)
    def test_01_identical_compute(self):self.pair((ADD,RET),(ADD,RET),'CLASS_I')
    def test_02_relocation_only(self):
        a=self.fixture((0x94000400,RET),relocations={0x1000:'external_foo'})
        b=self.fixture((0x94000800,RET),relocations={0x1000:'external_foo'})
        self.assertEqual(compare(a,b)['classification'],'CLASS_I')
    def test_03_address_only(self):
        r=compare(self.fixture((0x14000001,RET)),self.fixture((0x14000001,RET),start=0x1100))
        self.assertEqual(r['classification'],'CLASS_L');self.assertTrue(r['layout_risks'])
    def test_04_debug_metadata(self):self.assertEqual(compare(self.fixture(debug={'line':1}),self.fixture(debug={'line':99}))['classification'],'CLASS_I')
    def test_05_entry_alignment(self):
        r=compare(self.fixture(),self.fixture(start=0x1004));self.assertEqual(r['classification'],'CLASS_L');self.assertTrue(r['independent_layout_risk_approval_required']);self.assertFalse(r['calibration_authorized'])
    def test_06_page_placement(self):self.assertEqual(compare(self.fixture(),self.fixture(start=0x5000))['classification'],'CLASS_L')
    def test_07_opcode(self):self.pair((ADD,RET),(NOP,RET),'CLASS_M')
    def test_08_register(self):self.pair((ADD,RET),(0x91000401,RET),'CLASS_M')
    def test_09_branch(self):self.pair((0x14000001,NOP,RET),(0x14000002,NOP,RET),'CLASS_M')
    def test_10_stack_frame(self):self.pair((0xd10043ff,RET),(0xd10083ff,RET),'CLASS_M')
    def test_11_added_spill(self):self.pair((ADD,RET),(ADD,0xf90007e0,RET),'CLASS_M')
    def test_12_order(self):self.pair((ADD,NOP,RET),(NOP,ADD,RET),'CLASS_M')
    def test_13_missing_hot_function(self):self.assertEqual(compare(self.fixture(),self.fixture(missing=True))['classification'],'CLASS_M')
    def test_14_ambiguous_boundary(self):self.assertEqual(compare(self.fixture(),self.fixture(boundary='AMBIGUOUS'))['classification'],'CLASS_M')
    def test_15_incomplete_disassembly(self):self.assertEqual(compare(self.fixture(),self.fixture(complete=False))['classification'],'CLASS_M')
    def test_16_missing_production(self):
        with self.assertRaisesRegex(DiagnosticError,'MISSING_PRODUCTION'):attest('/nonexistent/g8-fixture','0'*64)
    def test_17_wrong_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture';p.write_bytes(MAGIC+struct.pack('<I',RET))
            with self.assertRaisesRegex(DiagnosticError,'WRONG_BINARY_SHA'):attest(p,'0'*64)
    def test_18_wrong_compiler(self):
        v=self.manifest();v['compiler']={'path':'another-compiler'}
        with self.assertRaisesRegex(DiagnosticError,'WRONG_COMPILER'):self.validate(v)
    def test_19_wrong_sdk(self):
        v=self.manifest();v['sdk']={'path':'another-sdk'}
        with self.assertRaisesRegex(DiagnosticError,'WRONG_SDK'):self.validate(v)
    def test_20_missing_provenance(self):
        v=self.manifest();v['build_arguments']=[]
        with self.assertRaisesRegex(DiagnosticError,'MISSING_BUILD_PROVENANCE'):self.validate(v)
    def test_21_unapproved_source_edit(self):
        path='native/src/bmssp_2025.cpp';source=original(self.p['binaries']['baseline']['source_commit'],path);modified=source.replace('const auto original_source','const auto changed_original_source',1)
        change={'file':path,'original_sha256':sha(source.encode()),'modified_text':modified,'unified_diff':''.join(difflib.unified_diff(source.splitlines(keepends=True),modified.splitlines(keepends=True),fromfile=path,tofile=path))}
        with self.assertRaisesRegex(DiagnosticError,'FORBIDDEN_COMPUTE_EDIT'):validate_source_edits(self.p,'baseline',[change])
    def test_22_forged_g8_pass(self):
        with self.assertRaisesRegex(DiagnosticError,'UNVERIFIED'):compare({'classification':'CLASS_I'},self.fixture())
        v=self.manifest();v['g8_claim']='CLASS_I'
        with self.assertRaisesRegex(DiagnosticError,'FORGED_G8'):self.validate(v)
    def test_23_forged_class_l_approval(self):
        v=self.manifest();v['layout_risk_approved']=True
        with self.assertRaisesRegex(DiagnosticError,'FORGED_APPROVAL'):self.validate(v)
    def test_24_missing_diagnostic(self):
        with self.assertRaisesRegex(DiagnosticError,'MISSING_DIAGNOSTIC'):self.validate(self.manifest(),artifact=True)
    def test_25_manifest_valid_static_only(self):self.assertTrue(self.validate(self.manifest()))
    def test_26_marker_anchor_and_no_compute_replacement(self):
        rules=whitelist(self.p,'baseline');rule=next(r for r in rules if r['tag']=='T2');source=original(self.p['binaries']['baseline']['source_commit'],rule['file']);lines=source.splitlines(keepends=True)
        self.assertIn('original_source',lines[rule['line']-2]);lines.insert(rule['line']-1,rule['allowed_line']);modified=''.join(lines)
        change={'file':rule['file'],'original_sha256':sha(source.encode()),'modified_text':modified,'unified_diff':''.join(difflib.unified_diff(source.splitlines(keepends=True),lines,fromfile=rule['file'],tofile=rule['file']))}
        self.assertTrue(validate_source_edits(self.p,'baseline',[change]))
    def test_27_unknown_attribution_is_m(self):self.assertEqual(compare(self.fixture((0x94000400,RET)),self.fixture((0x94000400,RET)))['classification'],'CLASS_M')
    def test_28_forbidden_flags(self):
        v=self.manifest();v['build_arguments'][0]['command']+=' -ffast-math'
        with self.assertRaisesRegex(DiagnosticError,'NUMERIC_ABI'):self.validate(v)
    def test_29_unverified_record_constructor(self):
        with self.assertRaisesRegex(DiagnosticError,'UNVERIFIED_EVIDENCE'):VerifiedEvidence(None,{})

    def test_30_build_and_link_commands_forbidden(self):
        from diagnostic.tools import run
        for argv in [['clang++','-c','engine.cpp'],['ld','engine.o','-o','diagnostic'],['xcrun','--sdk','macosx','clang++','-c','engine.cpp'],['cmake','--build','/fake']]:
            with self.subTest(argv=argv),self.assertRaises(DiagnosticError):run(argv)
    def test_31_public_cli_unauthorized(self):
        from contextlib import redirect_stdout
        import io,run
        for name in ['build','collect','calibrate','benchmark','profile','approve','run-real']:
            with redirect_stdout(io.StringIO()):self.assertEqual(run.main([name]),2)
    def test_32_mapping_requires_independent_build_context(self):
        from diagnostic.mapping import attest_mapping
        from diagnostic.manifest import VerifiedBuildContext
        with self.assertRaisesRegex(DiagnosticError,'UNVERIFIED_BUILD_CONTEXT'):VerifiedBuildContext(None,{})
        with self.assertRaisesRegex(DiagnosticError,'MISSING_VERIFIED_BUILD_CONTEXT'):attest_mapping({'binary':{'sha256':'f'*64,'variant':'baseline'}},'/never-read','f'*64,{'verified':True})

if __name__=='__main__':unittest.main()
