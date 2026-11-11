"""Read dyld image headers, not performance counters; no native BMSSP dispatch."""
import ctypes
import struct
from production_adapter import require
from production_adapter.artifacts import macho


def parse_image(data,path):
    identity = macho(data)
    cursor = 32
    install = None
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        cmd,length = struct.unpack_from('<II',data,cursor)
        if cmd == 0xd:  # LC_ID_DYLIB
            require(length >= 24, 'DYLIB_ID')
            offset = struct.unpack_from('<I',data,cursor+8)[0]
            require(24 <= offset < length, 'DYLIB_ID')
            name = data[cursor+offset:cursor+length]
            require(b'\0' in name, 'DYLIB_ID')
            require(install is None, 'DUPLICATE_DYLIB_ID')
            install = name.split(b'\0',1)[0].decode()
        cursor += length
    require(identity['uuid'] != '0'*32,'EMPTY_DEPENDENCY_UUID')
    return {'loaded_path':path,'architecture':identity['architecture'],'loaded_uuid':identity['uuid'],
            'install_name':install,'file_sha256':None,'file_sha_unavailable_reason':'IDENTITY_FROM_LOADED_MACHO_HEADER_NOT_STANDALONE_FILE'}


def loaded_images(paths,forbidden_paths=()):
    dyld = ctypes.CDLL(None)
    dyld._dyld_image_count.restype = ctypes.c_uint32
    dyld._dyld_get_image_name.argtypes = [ctypes.c_uint32]
    dyld._dyld_get_image_name.restype = ctypes.c_char_p
    dyld._dyld_get_image_header.argtypes = [ctypes.c_uint32]
    dyld._dyld_get_image_header.restype = ctypes.c_void_p
    found = {}
    for i in range(dyld._dyld_image_count()):
        path = dyld._dyld_get_image_name(i).decode()
        require(path not in forbidden_paths,'OTHER_VARIANT_ALREADY_LOADED')
        if path not in paths: continue
        require(path not in found, 'DUPLICATE_LOADED_IMAGE')
        address = dyld._dyld_get_image_header(i)
        require(bool(address),'DYLD_NULL_HEADER')
        header = ctypes.string_at(address,32)
        magic,cpu,_,_,_,size,_,_ = struct.unpack('<8I',header)
        require(magic == 0xfeedfacf and cpu == 0x0100000c and 0 < size < 16*1024*1024, 'DYLD_IMAGE_HEADER')
        found[path] = parse_image(ctypes.string_at(address,32+size),path)
    require(set(found) == set(paths),'LOADED_IMAGE_MISSING')
    return found


def verify_dependencies(found,expected_names):
    require(set(found) == set(expected_names),'UNEXPECTED_DEPENDENCY_IDENTITY')
    for name,item in found.items():
        require(item['loaded_path'] == name and item['install_name'] == name and item['architecture'] == 'arm64', 'UNEXPECTED_DEPENDENCY_IDENTITY')
        uuid = item['loaded_uuid']
        require(type(uuid) is str and len(uuid) == 32 and uuid != '0'*32 and all(c in '0123456789abcdef' for c in uuid),'UNEXPECTED_DEPENDENCY_UUID')
    return found
