"""Byte-verified deterministic ARM64 fixture attestor; never accepts production Mach-O."""
import struct
from pathlib import Path
from .core import require,sha
from .codegen import normalize,_from_extracted

MAGIC=b'G8_SYNTHETIC_ONLY\n'


def decode(word,pc):
    if word==0xd503201f:return 'nop'
    if word==0xd65f03c0:return 'ret'
    if word==0xa9bf7bfd:return 'stp x29, x30, [sp, #-0x10]!'
    if word==0xf90007e0:return 'str x0, [sp, #0x8]'
    if word&0xffc00000==0x91000000:
        rd,rn=word&31,(word>>5)&31;imm=(word>>10)&0xfff
        return f'add x{rd}, x{rn}, #0x{imm:x}'
    if word&0xffc003ff==0xd10003ff:return f'sub sp, sp, #0x{(word>>10)&0xfff:x}'
    if word&0x7c000000==0x14000000:
        immediate=word&0x3ffffff
        if immediate&(1<<25):immediate-=1<<26
        return ('bl' if word&0x80000000 else 'b')+f' 0x{pc+immediate*4:x}'
    raise ValueError('UNSUPPORTED_FIXTURE_OPCODE')


def attest(path,expected_sha,*,start=0x1000,debug=None,boundary='VERIFIED',complete=True,relocations=None,missing=False,compiler='fixture-compiler',sdk='fixture-sdk',provenance='fixed-fixture'):
    path=Path(path);require(path.is_file(),'MISSING_PRODUCTION_BINARY')
    data=path.read_bytes();require(sha(data)==expected_sha,'WRONG_BINARY_SHA')
    require(data.startswith(MAGIC) and len(data[len(MAGIC):])%4==0,'NOT_SYNTHETIC_FIXTURE')
    require(compiler=='fixture-compiler','WRONG_COMPILER');require(sdk=='fixture-sdk','WRONG_SDK');require(provenance=='fixed-fixture','MISSING_BUILD_PROVENANCE')
    words=struct.unpack('<'+'I'*((len(data)-len(MAGIC))//4),data[len(MAGIC):]);end=start+4*len(words)
    instructions=[{'address':start+4*i,'word':w,'asm':decode(w,start+4*i)} for i,w in enumerate(words)]
    normalized=normalize(instructions,start,end,relocations)
    function={'start':start,'end':end,'alignment_mod64':start%64,'page_start':start//16384,'page_end':(end-1)//16384,
              'boundary_status':boundary,'disassembly_complete':complete,'normalized':normalized}
    return _from_extracted({'synthetic':True,'build_verified':True,'variant':'fixture','build_identity':{'compiler':'fixture-compiler','sdk':'fixture-sdk'},'coverage_complete':not missing,'functions':{} if missing else {'hot':function},'debug':debug,'binary_sha256':expected_sha})
