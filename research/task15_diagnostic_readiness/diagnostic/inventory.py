"""Actual frozen Mach-O inventory. Complete disassembly does not imply G8 coverage."""
import re
from pathlib import Path
from production_adapter.artifacts import verify_artifact
from .core import require,sha,canonical
from .tools import discover,run
from .macho import inspect,word_at
from .codegen import normalize,_from_extracted

GROUPS={
 'symbolic_comparisons':{'sources':['native/src/symbolic_label.cpp','native/include/bmssp/symbolic_label.hpp'],'patterns':['LabelArena::compare','compare_scalar','SymbolicLabel::']},
 'recursive_BMSSP':{'sources':['native/src/bmssp_bounded.cpp'],'patterns':['BMSSPWorkspace::run']},
 'BaseCase':{'sources':['native/src/bmssp_bounded.cpp'],'patterns':['base_case','BaseCaseHeap']},
 'FindPivots':{'sources':['native/src/bmssp_bounded.cpp'],'patterns':['find_pivots']},
 'BoundedFrontier':{'sources':['native/src/bounded_frontier.cpp'],'patterns':['BoundedFrontier::']},
 'Graph':{'sources':['native/src/graph.cpp'],'patterns':['bmssp::Graph::']},
 'degree_reduction':{'sources':['native/src/degree_reduction.cpp'],'patterns':['bmssp::reduce_degree']},
 'top_level_solve':{'sources':['native/src/bmssp_2025.cpp'],'patterns':['BMSSP2025Engine::solve']},
 'wrapper_workspace':{'sources':['native/python/bindings.cpp','native/src/bmssp_bounded.cpp'],'patterns':['PreparedBMSSP','BMSSPWorkspace::','pybind11_init_bmssp_native']},
}


def parse_symbols(text):
    result=[]
    for line in text.splitlines():
        m=re.match(r'^([0-9a-fA-F]{16})\s+([A-Za-z])\s+(.+)$',line)
        if m:result.append({'address':int(m[1],16),'visibility':m[2],'name':m[3]})
    return result


def parse_disassembly(text,data,metadata):
    rows={};bad=[]
    for line in text.splitlines():
        m=re.match(r'^\s*([0-9a-fA-F]+):\s+(.+)$',line)
        if not m:continue
        addr=int(m[1],16)
        if not metadata['text']['address']<=addr<metadata['text']['address']+metadata['text']['size']:continue
        require(addr not in rows,'DUPLICATE_DISASSEMBLY_ADDRESS')
        asm=m[2].strip()
        if '<unknown>' in asm or asm.startswith(('.long','.word','.byte')):bad.append(addr)
        rows[addr]={'address':addr,'word':word_at(data,metadata,addr),'asm':asm}
    return rows,bad


def record_from_actual(p,variant,tool_records=None,path_override=None,sha_override=None):
    if path_override is None:identity=verify_artifact(p,variant,p['binaries'][variant]['path'])
    else:
        # Future diagnostic entry is read-only and requires an independently expected hash.
        from production_adapter.artifacts import macho
        path=Path(path_override);require(path.is_file() and not path.is_symlink(),'MISSING_DIAGNOSTIC_BINARY')
        data=path.read_bytes();require(sha(data)==sha_override,'DIAGNOSTIC_SHA')
        identity={'path':str(path),'sha256':sha_override,**macho(data),'variant':variant}
    data=Path(identity['path']).read_bytes();require(sha(data)==identity['sha256'],'BINARY_SHA_CHANGED')
    metadata=inspect(data);tool_records=tool_records or {};tools={}
    for name in ['nm','otool','dwarfdump','llvm-objdump','atos']:
        tools[name],discovery=discover(name,'/Library/Developer/CommandLineTools');tool_records['discovery_'+name]=discovery
    commands={}
    for name,arg in [('llvm-objdump',['--version']),('nm',['--version']),('otool',['--version']),('dwarfdump',['--version']),('atos',['-h'])]:
        commands[name+'_version']=run([tools[name]['path'],*arg],limit=1024*1024)
    commands['symbols']=run([tools['nm']['path'],'--demangle','--numeric-sort','--defined-only',identity['path']])
    commands['load_commands']=run([tools['otool']['path'],'-l',identity['path']])
    commands['dependencies']=run([tools['otool']['path'],'-L',identity['path']])
    commands['relocations']=run([tools['otool']['path'],'-rv',identity['path']])
    commands['debug_info']=run([tools['dwarfdump']['path'],'--debug-info',identity['path']])
    commands['uuid']=run([tools['dwarfdump']['path'],'--uuid',identity['path']])
    disassembly=run([tools['llvm-objdump']['path'],'--macho','--disassemble','--no-show-raw-insn','--mattr=+lse',identity['path']])
    require(commands['symbols']['returncode']==0 and disassembly['returncode']==0,'ANALYSIS_TOOL_FAILURE')
    symbols=parse_symbols(commands['symbols']['stdout']);rows,bad=parse_disassembly(disassembly['stdout'],data,metadata)
    starts=metadata['function_starts'];text=metadata['text'];by_address={}
    for s in symbols:
        if s['visibility'].lower()=='t':by_address.setdefault(s['address'],[]).append(s)
    all_functions={};coverage={};sources={}
    for group,spec in GROUPS.items():
        matched=[s for s in symbols if s['visibility'].lower()=='t' and any(pattern in s['name'] for pattern in spec['patterns'])]
        ids=[]
        for s in matched:
            start=s['address'];name=s['name'];ids.append(name)
            if name in all_functions:continue
            next_starts=[v for v in starts if v>start]
            end=next_starts[0] if next_starts else text['address']+text['size']
            complete=start in starts and start%4==0 and (end-start)%4==0 and all(a in rows and a not in bad for a in range(start,end,4))
            ins=[rows[a] for a in range(start,end,4) if a in rows]
            # Resolve only real external branch targets with a unique symbol identity.
            external={}
            for row in ins:
                asm=row['asm'].split(';',1)[0].strip();op=asm.split(None,1)[0] if asm else ''
                if op in {'b','bl','cbz','cbnz','tbz','tbnz'} or op.startswith('b.'):
                    try:target=int(asm.split(',')[-1].split()[-1],0)
                    except (ValueError,IndexError):continue
                    names=sorted({item['name'] for item in by_address.get(target,[])})
                    if not start<=target<end and len(names)==1:external[row['address']]=names[0]
            normalized=normalize(ins,start,end,external) if complete else {'instructions':[],'encoding_signatures':[],'fingerprint':None,'cfg':[],'registers':[],'frame_and_spill_evidence':[],'unresolved':[{'reason':'INCOMPLETE_DISASSEMBLY'}]}
            all_functions[name]={'source_group':group,'start':start,'end':end,'alignment_mod64':start%64,'page_start':start//16384,'page_end':(end-1)//16384,
                  'page_size':16384,'page_size_scope':'Audited arm64 16KiB placement; modulo64 plus raw addresses retained for alternative analyses.',
                  'boundary_status':'UPPER_BOUND_ONLY','boundary_source':'LC_FUNCTION_STARTS_TO_NEXT_START_OR_TEXT_END',
                  'symbol_aliases':[v['name'] for v in by_address.get(start,[])],'disassembly_complete':complete,'instruction_count':len(ins),
                  'machine_bytes_sha256':sha(b''.join(row['word'].to_bytes(4,'little') for row in ins)),
                  'normalized':normalized,'instructions':ins}
        source_evidence=[]
        for source in spec['sources']:
            command=run(['git','show',p['binaries'][variant]['source_commit']+':'+source])
            if command['returncode']==0:
                sources[source]={'source_commit':p['binaries'][variant]['source_commit'],'sha256':sha(command['stdout'].encode()),
                    'declaration_candidates':[{'line':i+1,'text':line.strip()} for i,line in enumerate(command['stdout'].splitlines()) if '(' in line and any(x in line for x in ['::','bmssp(','base_case(','find_pivots(','compare(','solve('])]}
                source_evidence.append(source)
        coverage[group]={'status':'BLOCKED','located_symbol_count':len(ids),'located_symbols':ids,'source_files':source_evidence,
                         'missing_or_ambiguous':['No original DWARF source/inline provenance or approved compute/insertion-window ranges.','LC_FUNCTION_STARTS allocation ends include possible padding; source function/inline end boundaries are not independently established.']+(['No matching out-of-line symbol; inlining/removal cannot be silently treated as NOT_APPLICABLE.'] if not ids else [])}
    total=text['size']//4
    report={'binary':identity,'tools':tools,'commands':commands,'discovery_commands':tool_records,'macho':metadata,'symbols':symbols,'source_identities':sources,
            'functions':all_functions,'coverage':coverage,'disassembly_summary':{'returncode':disassembly['returncode'],'argv':disassembly['argv'],'stdout_sha256':sha(disassembly['stdout'].encode()),'stdout_bytes':len(disassembly['stdout'].encode()),'stderr':disassembly['stderr'],'instruction_addresses_decoded':len(rows),'text_instruction_slots':total,'undecoded_addresses':bad,'undecoded_instruction_records':[rows[a] for a in bad],'full_text_decode':len(rows)==total and not bad,'raw_dump_retained':False},
            'debug_info_available':bool(metadata['debug_sections']) and 'DW_TAG_' in commands['debug_info']['stdout'],
            'status':'BLOCKED','g8_coverage_complete':False,'reason':'Useful actual symbol/range/instruction inventory; original source/inline and insertion-window coverage is not proven. No diagnostic artifact exists.'}
    attested=_from_extracted({'synthetic':False,'build_verified':False,'variant':variant,'binary_sha256':identity['sha256'],'coverage_complete':False,'functions':all_functions})
    require(sha(Path(identity['path']).read_bytes())==identity['sha256'],'BINARY_CHANGED_DURING_ANALYSIS')
    return report,attested
