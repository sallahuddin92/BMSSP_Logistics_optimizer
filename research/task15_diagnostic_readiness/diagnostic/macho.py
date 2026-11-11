"""Bounded Mach-O load commands and LC_FUNCTION_STARTS; no guessed source boundaries."""
import struct
from .core import require


def inspect(data):
    require(len(data)>=32,'MACHO_HEADER')
    magic,cpu,_,_,count,size,_,_=struct.unpack_from('<8I',data)
    require(magic==0xfeedfacf and cpu==0x0100000c and 32+size<=len(data),'MACHO_ARM64')
    cursor=32;segments=[];sections=[];function_data=None;uuid=None
    for _ in range(count):
        require(cursor+8<=32+size,'LOAD_COMMAND_BOUND')
        cmd,length=struct.unpack_from('<II',data,cursor)
        require(length>=8 and cursor+length<=32+size,'LOAD_COMMAND_BOUND')
        if cmd==0x19:
            require(length>=72,'SEGMENT')
            name=data[cursor+8:cursor+24].split(b'\0')[0].decode()
            va,vs,fo,fs=struct.unpack_from('<4Q',data,cursor+24)
            segments.append({'name':name,'vmaddr':va,'vmsize':vs,'fileoff':fo,'filesize':fs})
            ns=struct.unpack_from('<I',data,cursor+64)[0]
            require(72+ns*80<=length,'SECTION_BOUND')
            for i in range(ns):
                pos=cursor+72+i*80
                sn=data[pos:pos+16].split(b'\0')[0].decode();sg=data[pos+16:pos+32].split(b'\0')[0].decode()
                addr,sz,offset,align,reloff,nreloc,flags=struct.unpack_from('<QQ5I',data,pos+32)
                sections.append({'segment':sg,'name':sn,'address':addr,'size':sz,'offset':offset,'alignment_power':align,'relocation_offset':reloff,'relocation_count':nreloc,'flags':flags})
        elif cmd==0x26:function_data=struct.unpack_from('<II',data,cursor+8)
        elif cmd==0x1b:uuid=data[cursor+8:cursor+24].hex()
        cursor+=length
    text=next((s for s in sections if s['segment']=='__TEXT' and s['name']=='__text'),None)
    require(text is not None and text['offset']+text['size']<=len(data),'TEXT_SECTION')
    starts=[]
    if function_data:
        off,sz=function_data;require(off+sz<=len(data),'FUNCTION_STARTS_BOUND')
        addr=next(s['vmaddr'] for s in segments if s['name']=='__TEXT');value=shift=0
        for byte in data[off:off+sz]:
            value|=(byte&127)<<shift
            if byte&128:shift+=7;require(shift<64,'ULEB_OVERFLOW');continue
            if value==0:break
            addr+=value;require(text['address']<=addr<text['address']+text['size'] and addr%4==0,'FUNCTION_START_RANGE')
            starts.append(addr);value=shift=0
    require(starts==sorted(set(starts)),'FUNCTION_START_ORDER')
    return {'uuid':uuid,'architecture':'arm64','sections':sections,'segments':segments,'text':text,'function_starts':starts,
            'debug_sections':[s for s in sections if s['segment']=='__DWARF'],
            'boundary_limitation':'LC_FUNCTION_STARTS supplies starts/allocation upper bounds, not source compute windows, inline provenance or exact instruction-vs-padding ends.'}


def word_at(data,metadata,address):
    text=metadata['text'];off=text['offset']+address-text['address']
    require(text['address']<=address and address+4<=text['address']+text['size'],'INSTRUCTION_RANGE')
    return struct.unpack_from('<I',data,off)[0]
