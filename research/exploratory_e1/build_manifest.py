"""Fresh selected-SDK identity and actual E1 build records, no historical recovery."""
import hashlib,json,os,pathlib,platform,stat,subprocess,sys
from experiment import digest,ENV,LABEL
root=pathlib.Path(sys.argv[1]);sdk=pathlib.Path('/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk').resolve();cache={};entries=[];observations={};errors=[]
paths=[sdk]
for directory,dirs,files in os.walk(sdk,followlinks=False):
 paths.extend(pathlib.Path(directory)/n for n in dirs+files)
for p in sorted(set(paths)):
 s=p.lstat();rel='.' if p==sdk else str(p.relative_to(sdk));stamp=(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns);observations[str(p)]=stamp
 typ='symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file' if p.is_file() else 'unsupported';target=os.readlink(p) if typ=='symlink' else None;h=None
 try:
  resolved=p.resolve() if typ=='symlink' else p
  if typ=='symlink' and resolved!=sdk and sdk not in resolved.parents:raise ValueError('SDK symlink escape')
  if resolved.is_file():
   key=str(resolved)
   if key not in cache:
    before=resolved.stat();value=digest(resolved);after=resolved.stat();assert (before.st_size,before.st_mtime_ns,before.st_ctime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ctime_ns,after.st_ino);cache[key]=value
   h=cache[key]
 except (OSError,ValueError,AssertionError) as e:errors.append({'path':rel,'error':str(e)})
 entries.append({'path':rel,'type':typ,'size':s.st_size if typ=='file' else None,'mode':stat.S_IMODE(s.st_mode),'symlink_target':target,'sha256':h})
for p,expected in observations.items():
 s=pathlib.Path(p).lstat();assert (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==expected,'SDK changed'
assert not errors,errors
identity=hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest();(root/'fresh-sdk-inventory.json').write_text(json.dumps({'label':LABEL,'root':str(sdk),'entries':entries,'tree_sha256':identity,'entry_count':len(entries),'errors':errors},separators=(',',':')))
def capture(argv):
 r=subprocess.run(argv,capture_output=True,env=ENV);return {'argv':argv,'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()}
manifest={'label':LABEL,'baseline_commit':'5e8b11b4db8a0883969e7fe1405b048f419d7f07','historical_byte_equivalence_claimed':False,'environment_selection':{k:ENV[k] for k in ['DEVELOPER_DIR','SDKROOT']},'host':platform.uname()._asdict(),'compiler':{'path':'/Library/Developer/CommandLineTools/usr/bin/clang++','resolved_path':str(pathlib.Path('/Library/Developer/CommandLineTools/usr/bin/clang++').resolve()),'sha256':digest('/Library/Developer/CommandLineTools/usr/bin/clang++'),'version':capture(['/Library/Developer/CommandLineTools/usr/bin/clang++','--version'])},'sdk':{'root':str(sdk),'tree_sha256':identity,'entry_count':len(entries),'inventory_sha256':digest(root/'fresh-sdk-inventory.json')},'host_commands':[capture(argv) for argv in [['/usr/bin/sw_vers'],['/usr/sbin/sysctl','-n','machdep.cpu.brand_string','hw.memsize','hw.ncpu'],['/usr/bin/pmset','-g','therm'],['/usr/bin/vm_stat']]],'builds':{}}
for variant in ['baseline','candidate']:
 build=root/('build-'+variant);records=json.loads((build/'compile_commands.json').read_text());exe=build/'e1_native';manifest['builds'][variant]={'executable_sha256':digest(exe),'library_sha256':digest(build/'libbmssp_foundation.a'),'compile_commands':records,'link_command':(build/'CMakeFiles/e1_native.dir/link.txt').read_text(),'cmake_cache':(build/'CMakeCache.txt').read_text(),'CMakeCXXCompiler':next(build.glob('CMakeFiles/*/CMakeCXXCompiler.cmake')).read_text()}
(root/'native-build-manifest.json').write_text(json.dumps(manifest,indent=2));print('Fresh SDK',len(entries),identity)
