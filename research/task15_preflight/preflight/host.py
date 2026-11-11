"""Fixed read-only host commands; never sampling/recording instruments or clocks."""
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from .core import require,sha

COMMANDS={
 'hardware':['/usr/sbin/sysctl','-n','hw.machine','hw.model','machdep.cpu.brand_string','hw.memsize'],
 'os':['/usr/bin/sw_vers'],
 'memory_pressure':['/usr/bin/memory_pressure','-Q'],
 'vm_stat':['/usr/bin/vm_stat'],
 'swap':['/usr/sbin/sysctl','vm.swapusage'],
 'power':['/usr/bin/pmset','-g','batt'],
 'power_modes':['/usr/bin/pmset','-g','custom'],
 'thermal':['/usr/bin/pmset','-g','therm'],
 'developer_directory':['/usr/bin/xcode-select','-p'],
 'sdk_path':['/usr/bin/xcrun','--show-sdk-path'],
 'sdk_version':['/usr/bin/xcrun','--show-sdk-version'],
 'active_compiler':['/usr/bin/xcrun','--find','clang++'],
 'active_compiler_version':['/usr/bin/xcrun','clang++','--version'],
 'frozen_compiler_version':['/Library/Developer/CommandLineTools/usr/bin/clang++','--version'],
 'xctrace_path':['/usr/bin/xcrun','--find','xctrace'],
 'xctrace_version':['/usr/bin/xcrun','xctrace','version'],
 'processes':['/bin/ps','-axo','pid,ppid,comm,args'],
 'filesystem':['/bin/df','-k'],
}


def command(name):
    args=COMMANDS[name]
    try:
        p=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=15,
                         env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','LC_ALL':'C','LANG':'C'})
        stdout=p.stdout
        if name=='processes':
            stdout='\n'.join(line for line in stdout.splitlines() if any(t in line.lower() for t in ['bmssp','xctrace','instruments','powermetrics','sample ','spindump']))
        return {'command':args,'returncode':p.returncode,'stdout':stdout,'stderr':p.stderr,'error':None}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'command':args,'returncode':None,'stdout':'','stderr':'','error':{'type':type(exc).__name__,'message':str(exc)}}


def observe(p):
    records={name:command(name) for name in COMMANDS}
    compiler=records['active_compiler']['stdout'].strip()
    compiler_identity=None
    if records['active_compiler']['returncode']==0 and Path(compiler).is_file():
        compiler_identity={'path':compiler,'resolved_path':str(Path(compiler).resolve()),'sha256':sha(Path(compiler).read_bytes())}
    power=records['power']['stdout']
    active='AC Power' if 'AC Power' in power else 'Battery Power' if 'Battery Power' in power else None
    match=re.search(re.escape(active)+r':\n(.*?)(?=\n(?:AC Power|Battery Power):|\Z)',records['power_modes']['stdout'],re.S) if active else None
    mode=re.search(r'lowpowermode\s+(\d+)',match.group(1)) if match else None
    low_power=int(mode.group(1)) if mode else None
    return {'interpreter':{'executable':sys.executable,'resolved_executable':str(Path(sys.executable).resolve()),'version':sys.version,
                           'implementation':sys.implementation.name,'abi':sys.implementation.cache_tag,'isolated':bool(sys.flags.isolated),'architecture':platform.machine()},
            'commands':records,'active_compiler_identity':compiler_identity,
            'declared_compiler_path':p['environment']['compiler_path'],
            'selected_compiler_path_matches_protocol':compiler==p['environment']['compiler_path'],
            'tool_paths':{name:shutil.which(name) for name in ['xctrace','atos','sample','spindump','powermetrics']},
            'permissions':{'status':'PENDING','reason':'Installed tools do not establish runtime/TCC/profile permissions; no recording or permission probe authorized.'},
            'clock_mapping_resolution_aperture_overhead':{'status':'PENDING','reason':'No clock or timing-endpoint probe executed.'},
            'available_memory_interpretation':'Physical bytes, vm_stat pages and memory_pressure query are point-in-time observations; prepared-worker footprint/reservation/prefault gate remains PENDING.',
            'power_policy':{'status':'VERIFIED' if records['power']['returncode']==0 and 'AC Power' in records['power']['stdout'] else 'PENDING',
                            'low_power_mode_status':'VERIFIED' if low_power is not None else 'PENDING','active_power_source':active,'low_power_mode_enabled':bool(low_power) if low_power is not None else None,'reason':'Active-source lowpowermode setting parsed from read-only pmset snapshot; no setting changed.'},
            'injection_environment_names':[k for k in os.environ if k.startswith(('DYLD_','LD_PRELOAD'))],
            'trace_or_profile_active':sys.gettrace() is not None or sys.getprofile() is not None,
            'native_dependency_observation':'Historical Phase7 loaded identities verified; no current extension load or dyld native probe performed.'}
