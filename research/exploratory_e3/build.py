"""E3 external fresh builds; unchanged algorithm and exact H1, trace support outside core."""
import pathlib,json,shlex
from availability import ROOT,REPO,CLT,command,put,sha
def build():
 e2=json.loads(pathlib.Path('/Volumes/RAID1_PHOTOS/BMSSP-exploratory-E2-8va49w4u/source-identities.json').read_text())
 variants={}
 for v in ['A','B']:
  source=ROOT/('source-'+v);build=ROOT/('build-'+v)
  hashes={str(p.relative_to(source)):sha(p) for p in (source/'native').rglob('*') if p.is_file()};assert hashes==e2['sources'][v]
  command('configure-fixed-'+v,['/opt/homebrew/bin/cmake','-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER='+CLT+'/usr/bin/clang++','-DCMAKE_OSX_SYSROOT='+CLT+'/SDKs/MacOSX.sdk','-DCMAKE_OSX_ARCHITECTURES=arm64','-DCMAKE_OSX_DEPLOYMENT_TARGET=26.0','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DBMSSP_PYTHON=OFF','-DBMSSP_SANITIZERS=OFF','-DBMSSP_ALLOCATION_PROBE=OFF','-DCMAKE_PROJECT_bmssp_native_foundation_INCLUDE='+str(REPO/'research/exploratory_e3/add_target.cmake')],developer=CLT)
  command('build-fixed-'+v,['/opt/homebrew/bin/cmake','--build',str(build),'--parallel','4'],developer=CLT,timeout=90)
  command('ctest-'+v,['/opt/homebrew/bin/ctest','--test-dir',str(build),'--output-on-failure','-j','1'],developer=CLT,timeout=90)
  records=json.loads((build/'compile_commands.json').read_text());variants[v]={'source_hashes':hashes,'library_sha256':sha(build/'libbmssp_foundation.a'),'compile_commands':records,'cmake_cache':(build/'CMakeCache.txt').read_text(),'executables':{}}
  for exe in ['e3_off','e3_on','e3_check']:
   path=build/exe;uuid=command('uuid-'+v+'-'+exe,[CLT+'/usr/bin/dwarfdump','--uuid',str(path)],developer=CLT)[1]
   symbols=command('symbols-'+v+'-'+exe,[CLT+'/usr/bin/nm','--numeric-sort','--defined-only',str(path)],developer=CLT)[1]
   variants[v]['executables'][exe]={'path':str(path),'sha256':sha(path),'UUID_output':uuid,'symbols_stdout_sha256':sha(ROOT/('symbols-'+v+'-'+exe+'.stdout')),'link_command':(build/('CMakeFiles/'+exe+'.dir/link.txt')).read_text()}
  selection=json.loads((ROOT/'source-selection.json').read_text())
  for g,info in selection['graphs'].items():
   command('correctness-'+v+'-'+g,[str(build/'e3_check'),'check',info['native_export_path'],str(ROOT/(g+'.sources')),'bmssp','1','0',str(ROOT/(v+'-'+g+'-distances.bin'))],developer=CLT,timeout=90)
  for g in selection['graphs']:
   if v=='B':assert sha(ROOT/('A-'+g+'-distances.bin'))==sha(ROOT/('B-'+g+'-distances.bin'))
 put('build-identities.json',{'variants':variants,'A1_A2_same_executable_per_mode':True,'H1_patch_sha256':sha(REPO/'research/exploratory_e1/candidate-engine.diff'),'instrumentation_scope':'e3_on compile definition affects wrapper/span header only; native source/library compilation has no trace definitions.'})
if __name__=='__main__':build()
