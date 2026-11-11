"""Conservative instruction normalization; registers, opcodes, order and stack survive."""
import re
from .core import canonical,sha,require

BRANCH={'b','bl','cbz','cbnz','tbz','tbnz'}


def normalize(instructions,start,end,external_symbols=None):
    external_symbols=external_symbols or {}
    normalized=[];encodings=[];cfg=[];registers=set();stack=[];unresolved=[]
    for i,row in enumerate(instructions):
        address=row['address'];asm=row['asm'].split(';',1)[0].strip()
        require(asm and '.long' not in asm and '<unknown>' not in asm,'UNDECODED_INSTRUCTION')
        parts=asm.split(None,1);opcode=parts[0];operands=parts[1] if len(parts)>1 else ''
        operands=re.sub(r'\s+','',operands)
        registers.update(re.findall(r'(?<![a-z0-9])(?:[xwvsdqbh][0-9]+|sp|wsp|fp|lr|xzr|wzr)(?![a-z0-9])',operands))
        if opcode in BRANCH or opcode.startswith('b.'):
            pieces=operands.split(',');target_text=pieces[-1]
            try:target=int(target_text,0)
            except ValueError:target=None
            if target is not None and start<=target<end and (target-start)%4==0:
                target_id='I'+str((target-start)//4)
            elif address in external_symbols:target_id='S:'+external_symbols[address]
            else:target_id=target_text;unresolved.append({'instruction':i,'reason':'UNRESOLVED_EXTERNAL_BRANCH','target':target_text})
            pieces[-1]=target_id;operands=','.join(pieces);cfg.append([i,opcode,target_id])
        elif opcode in {'adr','adrp'}:
            # Only externally verified relocation identity may replace this address.
            if address in external_symbols:
                pieces=operands.split(',');pieces[-1]='S:'+external_symbols[address];operands=','.join(pieces)
            else:unresolved.append({'instruction':i,'reason':'UNRESOLVED_PC_RELATIVE_ADDRESS'})
        # All non-address immediate offsets, opcode, registers and operand order retained.
        word=row['word']
        require(type(word) is int and 0<=word<2**32,'INSTRUCTION_ENCODING')
        if (opcode in BRANCH or opcode.startswith('b.')) and not any(u['instruction']==i for u in unresolved):
            if opcode in {'b','bl'}:word &= ~0x03ffffff
            elif opcode in {'tbz','tbnz'}:word &= ~(0x3fff<<5)
            else:word &= ~(0x7ffff<<5)
        elif opcode in {'adr','adrp'} and address in external_symbols:word &= ~((3<<29)|(0x7ffff<<5))
        encodings.append(f'{word:08x}')
        value=opcode+(' '+operands if operands else '')
        normalized.append(value)
        if re.search(r'(?<![a-z])(?:sp|wsp|fp|x29)(?![0-9a-z])',operands):stack.append([i,value])
        if opcode in {'br','blr','ret'}:cfg.append([i,opcode,operands])
    return {'instructions':normalized,'encoding_signatures':encodings,'fingerprint':sha(canonical(normalized)),'cfg':cfg,'registers':sorted(registers),
            'frame_and_spill_evidence':stack,'unresolved':unresolved,
            'limitation':'Stack-register-touching instructions preserved verbatim; not a full liveness/unwind or spill-origin proof.'}


_TOKEN=object()
class VerifiedEvidence:
    """Comparator inputs can only come from byte/tool attestors, never a JSON PASS flag."""
    def __init__(self,token,data):
        require(token is _TOKEN,'UNVERIFIED_EVIDENCE')
        self._json=canonical(data)
    @property
    def data(self):
        import json
        return json.loads(self._json)


def _from_extracted(data):return VerifiedEvidence(_TOKEN,data)


def compare(production,diagnostic):
    require(isinstance(production,VerifiedEvidence) and isinstance(diagnostic,VerifiedEvidence),'UNVERIFIED_COMPARATOR_INPUT')
    a,b=production.data,diagnostic.data
    reasons=[];differences=[];layout=[]
    if not a.get('build_verified') or not b.get('build_verified'):reasons.append('MISSING_VERIFIED_BUILD_PROVENANCE')
    if a.get('variant')!=b.get('variant'):reasons.append('WRONG_VARIANT_PAIR')
    if a.get('build_identity')!=b.get('build_identity'):reasons.append('COMPILER_OR_SDK_LOCK_MISMATCH')
    if a['synthetic']!=b['synthetic']:reasons.append('SYNTHETIC_REAL_MIX')
    if not a['coverage_complete'] or not b['coverage_complete']:reasons.append('MISSING_OR_AMBIGUOUS_G8_COVERAGE')
    if set(a['functions'])!=set(b['functions']):reasons.append('MISSING_HOT_FUNCTION')
    for identity in sorted(set(a['functions'])&set(b['functions'])):
        x,y=a['functions'][identity],b['functions'][identity]
        if x['boundary_status']!='VERIFIED' or y['boundary_status']!='VERIFIED' or not x['disassembly_complete'] or not y['disassembly_complete']:
            reasons.append('BOUNDARY_OR_DISASSEMBLY:'+identity)
        if x['normalized']['unresolved'] or y['normalized']['unresolved']:reasons.append('UNRESOLVABLE_ATTRIBUTION:'+identity)
        for field in ['instructions','encoding_signatures','cfg','registers','frame_and_spill_evidence']:
            if x['normalized'][field]!=y['normalized'][field]:differences.append({'function':identity,'field':field,'production':x['normalized'][field],'diagnostic':y['normalized'][field]})
        la={k:x[k] for k in ['start','end','alignment_mod64','page_start','page_end']};lb={k:y[k] for k in la}
        if la!=lb:layout.append({'function':identity,'production':la,'diagnostic':lb,'risk':'Layout/alignment/page placement changed; not assumed performance equivalent.'})
    classification='CLASS_M' if reasons or differences else 'CLASS_L' if layout else 'CLASS_I'
    return {'classification':classification,'status':'BLOCKED' if classification=='CLASS_M' else 'PENDING' if classification=='CLASS_L' else 'VERIFIED',
            'differences':differences,'layout_risks':layout,'missing_or_unresolved':reasons,'synthetic':a['synthetic'],
            'independent_layout_risk_approval_required':classification=='CLASS_L','scientific_approval':'pending','calibration_authorized':False,'collection_authorized':False,'measurement_eligible':False,
            'meaning':'Structural G8 classification only; no approval and not all G1–G10 gates.'}
