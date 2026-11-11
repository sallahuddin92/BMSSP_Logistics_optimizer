"""Deterministic negative controls; never executes a real recovery or native engine."""
import copy
import io
from contextlib import redirect_stdout
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from recovery.core import component,validate_component,compare_versions,require_no_approval,RecoveryError,digest
from recovery.sources import authenticated_index,archived
from recovery.collector import sdk_current

class Tests(unittest.TestCase):
    def test_01_missing_historical_hash(self):
        r=component('compiler','ORIGINAL_CXX_COMPILER','/fixed/clang',version='clang21',current={'sha256':'a'*64,'resolved_path':'/fixed/clang'})
        self.assertIsNone(r['historical_sha256']);self.assertEqual(r['historical_identity_status'],'VERSION_ONLY');self.assertFalse(r['historical_byte_continuity_proven'])
    def test_02_altered_historical_hash(self):
        with self.assertRaisesRegex(RecoveryError,'ALTERED_HISTORICAL_HASH'):
            component('original-production-baseline','ORIGINAL_PRODUCTION_EXTENSION','/fixed/binary',historical_sha='f'*64,anchors=[{'independently_anchored':True,'component':'original-production-baseline','component_sha256':'f'*64,'kind':'ARCHIVED_COMPONENT_BYTES'}])
    def test_03_current_historical_confusion(self):
        r=component('compiler','ORIGINAL_CXX_COMPILER','/fixed/clang',current={'sha256':'a'*64,'resolved_path':'/fixed/clang'})
        r.update(historical_identity_status='HISTORICALLY_VERIFIED',historical_byte_continuity_proven=True)
        with self.assertRaisesRegex(RecoveryError,'CONFUSION'):validate_component(r)
    def test_04_version_only(self):
        r=component('compiler','ORIGINAL_CXX_COMPILER','/fixed/clang',version='21.0.0')
        self.assertEqual(r['historical_identity_status'],'VERSION_ONLY');self.assertIsNone(r['historical_sha256'])
        self.assertEqual(compare_versions([{'version':'21.0.0'},{'version':'21.0.0'}])['status'],'VERSION_ONLY')
    def test_05_contradictory_compiler(self):
        r=compare_versions([{'version':'clang17'},{'version':'clang21'}]);self.assertTrue(r['contradiction']);self.assertEqual(r['status'],'UNVERIFIED')
    def test_06_redirected_sdk(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'other').mkdir();(root/'sdk').symlink_to(root/'other')
            with self.assertRaisesRegex(RecoveryError,'REDIRECTED_SDK'):sdk_current(root/'sdk')
    def test_07_missing_linker_provenance(self):
        r=component('linker','ORIGINAL_LINKER','/missing/linker',available=False)
        self.assertEqual(r['historical_identity_status'],'UNAVAILABLE');self.assertFalse(r['historical_byte_continuity_proven'])
    def test_08_unsupported_dependency_continuity(self):
        r=component('pybind11-build-headers','ORIGINAL_PYBIND11_BUILD_HEADERS','/fixed/include',version='2.11.1',current={'sha256':'a'*64,'resolved_path':'/fixed/include'},scope='SELECTED_HEADER_NOT_COMPLETE_PACKAGE')
        r['historical_byte_continuity_proven']=True
        with self.assertRaisesRegex(RecoveryError,'CONFUSION'):validate_component(r)
    def test_09_corrupted_archive_index(self):
        import recovery.sources as sources
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'evidence-index.json';path.write_bytes(b'{"original":true}')
            p={'evidence_files_used':{str(path):{'sha256':digest(path.read_bytes())}}};path.write_bytes(b'{"tampered":true}')
            with patch.object(sources,'ARCHIVE',root),self.assertRaisesRegex(RecoveryError,'CORRUPTED_ARCHIVE_INDEX'):authenticated_index(p)
    def test_10_forged_approval(self):
        for value in [{'approved':True},{'g8_approved':True},{'scientific_acceptance':'approved'},{'calibration_authorized':True}]:
            with self.subTest(value=value),self.assertRaisesRegex(RecoveryError,'FORGED_PROVENANCE_APPROVAL'):require_no_approval(value)
    def test_11_self_attested_hash_not_historical(self):
        value=digest(b'new manifest')
        with self.assertRaisesRegex(RecoveryError,'NOT_HISTORICALLY_ANCHORED'):
            component('compiler','ORIGINAL_CXX_COMPILER','/fixed/clang',historical_sha=value,anchors=[{'kind':'PREEXISTING_COMPONENT_HASH_RECORD','independently_anchored':True,'component':'compiler','component_sha256':value}])
    def test_12_unavailable_artifact(self):
        import recovery.sources as sources
        with tempfile.TemporaryDirectory() as d:
            with patch.object(sources,'ARCHIVE',Path(d)):
                data,status=archived('run/toolchain.json',{})
                self.assertIsNone(data);self.assertEqual(status['status'],'UNAVAILABLE')
    def test_13_current_receipt_is_not_historical_hash(self):
        r=component('sdk-and-headers','ORIGINAL_APPLE_SDK_AND_CXX_HEADERS','/sdk',version='26.5',anchors=[{'kind':'CURRENT_RECEIPT','sha256':'a'*64,'install_time':1}])
        self.assertEqual(r['historical_identity_status'],'VERSION_ONLY');self.assertIsNone(r['historical_sha256'])
    def test_14_closed_component_schema(self):
        r=component('compiler','ORIGINAL_CXX_COMPILER','/fixed/clang');r['PASS']=True
        with self.assertRaisesRegex(RecoveryError,'SCHEMA'):validate_component(r)
    def test_15_bounded_source_allowlist(self):
        with self.assertRaisesRegex(RecoveryError,'OUT_OF_SCOPE'):archived('../../personal/file',{})
    def test_16_unauthorized_commands(self):
        import run
        for name in ['build','benchmark','collect','calibrate','profile','approve','resume','run-real']:
            with redirect_stdout(io.StringIO()):self.assertEqual(run.main([name]),2)
    def test_17_native_import_denied(self):
        with self.assertRaisesRegex(RecoveryError,'NATIVE_IMPORT'):__import__('bmssp_native')
    def test_18_current_mismatch_is_not_missing_evidence_failure(self):
        r=component('compiler','ORIGINAL_CXX_COMPILER','/fixed/clang',version='21',current={'sha256':'b'*64,'resolved_path':'/fixed/clang'})
        self.assertEqual(r['historical_identity_status'],'VERSION_ONLY');self.assertFalse(r['contradictions']);self.assertFalse(r['historical_byte_continuity_proven'])

if __name__=='__main__':unittest.main()
