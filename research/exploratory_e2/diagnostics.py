"""Separate E2 diagnostic processes; never overlap primary observations."""
import difflib,json,pathlib,subprocess,time
from campaign import ROOT,REPO,ENV,LABEL,read,rows,run,put,sha

def build_allocators():
 manifests={}
 for v in ['A','B']:
  source=ROOT/('source-'+v);original=(source/'native/src/bounded_frontier.cpp').read_text();marker='void BoundedFrontier::insert(VertexIndex key, const SymbolicLabel &value) {';assert original.count(marker)==1
  instrumented='#include "alloc_observer.hpp"\n'+original.replace(marker,marker+'\n    e2alloc::InsertScope e2_scope;')
  assert instrumented.removeprefix('#include "alloc_observer.hpp"\n').replace('\n    e2alloc::InsertScope e2_scope;','')==original
  observed=ROOT/('allocator-bounded-'+v+'.cpp');observed.write_text(instrumented)
  (ROOT/('allocator-source-'+v+'.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),instrumented.splitlines(True),fromfile='original',tofile='diagnostic')))
  target=ROOT/('build-allocator-'+v)
  run('configure-allocator-'+v,['/opt/homebrew/bin/cmake','-S',source,'-B',target,'-DCMAKE_BUILD_TYPE=Release','-DCMAKE_CXX_COMPILER=/Library/Developer/CommandLineTools/usr/bin/clang++','-DCMAKE_OSX_SYSROOT='+ENV['SDKROOT'],'-DCMAKE_OSX_ARCHITECTURES=arm64','-DCMAKE_OSX_DEPLOYMENT_TARGET=26.0','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DBUILD_TESTING=OFF','-DBMSSP_PYTHON=OFF','-DBMSSP_SANITIZERS=OFF','-DBMSSP_ALLOCATION_PROBE=OFF','-DE2_DIAGNOSTIC_SOURCE='+str(observed),'-DCMAKE_PROJECT_bmssp_native_foundation_INCLUDE='+str(REPO/'research/exploratory_e2/add_allocator.cmake')])
  run('build-allocator-'+v,['/opt/homebrew/bin/cmake','--build',target,'--target','e2_allocator','--parallel','4'])
  manifests[v]={'executable_sha256':sha(target/'e2_allocator'),'original_source_sha256':sha(source/'native/src/bounded_frontier.cpp'),'instrumented_source_sha256':sha(observed),'instrumentation_only_projection_verified':True,'compile_commands':read(target/'compile_commands.json'),'link_command':(target/'CMakeFiles/e2_allocator.dir/link.txt').read_text()}
 put('allocator-build-identities.json',{'variants':manifests})

def allocations():
 inputs=read(ROOT/'input-identities.json')['inputs']
 for replicate in range(2):
  for g,p in inputs.items():
   for v in (['A','B'] if replicate==0 else ['B','A']):run(f'allocator-{replicate}-{g}-{v}',[ROOT/('build-allocator-'+v)/'e2_allocator',p['native_export_path'],ROOT/(g+'-ten.sources')])

def sampling():
 inputs=read(ROOT/'input-identities.json')['inputs'];records=[]
 for g,p in inputs.items():
  for v in ['A','B']:
   name='sampling-'+g+'-'+v;argv=[str(ROOT/('build-'+v)/'e2_correctness'),'spin',p['native_export_path'],str(ROOT/(g+'-ten.sources')),'bmssp','1','0','5']
   with (ROOT/(name+'.worker.log')).open('xb') as f,(ROOT/(name+'.worker.stderr')).open('xb') as err:
    child=subprocess.Popen(argv,env=ENV,stdout=f,stderr=err);start=time.monotonic()
    while (ROOT/(name+'.worker.log')).stat().st_size==0 and child.poll() is None and time.monotonic()-start<2:time.sleep(.01)
    cmd=['/usr/bin/sample',str(child.pid),'3','1','-file',str(ROOT/(name+'.sample.txt'))];sample=subprocess.run(cmd,capture_output=True,env=ENV);(ROOT/(name+'.sampler.log')).write_bytes(sample.stdout+sample.stderr);status=child.wait()
   record={'label':LABEL,'graph':g,'variant':v,'worker_argv':argv,'worker_exit':status,'sampler_argv':cmd,'sampler_exit':sample.returncode,'supported_for_this_process':sample.returncode==0,'wall_seconds':time.monotonic()-start};records.append(record);print(name,status,sample.returncode,flush=True)
   if status:raise RuntimeError('Diagnostic worker failed; preserve records')
 put('sampling-records.json',{'processes':records})
if __name__=='__main__':
 import sys
 {'build':build_allocators,'allocations':allocations,'sampling':sampling}[sys.argv[1]]()
