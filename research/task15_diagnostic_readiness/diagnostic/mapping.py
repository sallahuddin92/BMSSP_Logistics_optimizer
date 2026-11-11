"""Future byte-checked, independently hash-locked source/compute mapping attestation.

No JSON verified/PASS flag creates comparator trust. A caller must supply a separate
reviewed mapping hash plus fresh tool-extracted binary evidence. Missing mappings
remain blocked; the Phase9 inventory never invents them.
"""
from pathlib import Path
from .core import require,sha,canonical
from .codegen import normalize,_from_extracted
from .inventory import GROUPS


def attest_mapping(report,mapping_path,independently_expected_sha256,build_context):
    from .manifest import VerifiedBuildContext
    require(isinstance(build_context,VerifiedBuildContext) and build_context.data["binary_sha256"]==report["binary"]["sha256"] and build_context.data["variant"]==report["binary"]["variant"],"MISSING_VERIFIED_BUILD_CONTEXT")
    data=Path(mapping_path).read_bytes();require(sha(data)==independently_expected_sha256,'UNVERIFIED_MAPPING_LOCK')
    import json
    mapping=json.loads(data)
    require(set(mapping)=={'schema','binary_sha256','source_identity_sha256','required_symbol_inventory_sha256','groups','functions','review_provenance_sha256'},'MAPPING_SCHEMA')
    require(mapping['schema']=='g8-locked-mapping-1' and mapping['binary_sha256']==report['binary']['sha256'],'MAPPING_BINARY_IDENTITY')
    require(sha(Path(report['binary']['path']).read_bytes())==mapping['binary_sha256'],'MAPPED_BINARY_CHANGED')
    require(mapping['source_identity_sha256']==sha(canonical(report['source_identities'])),'MAPPING_SOURCE_IDENTITY')
    required={g:sorted(c['located_symbols']) for g,c in report['coverage'].items()}
    require(mapping['required_symbol_inventory_sha256']==sha(canonical(required)),'MAPPING_SYMBOL_INVENTORY')
    require(set(mapping['groups'])==set(GROUPS),'MISSING_HOT_FUNCTION_GROUP')
    require(type(mapping['review_provenance_sha256']) is str and len(mapping['review_provenance_sha256'])==64,'MISSING_INDEPENDENT_MAPPING_PROVENANCE')
    # Every located critical symbol is covered; no unlocated/inline family may be skipped.
    required_names={name for names in required.values() for name in names}
    mapped_symbols={v['symbol'] for v in mapping['functions'].values()}
    require(required_names<=mapped_symbols,'MISSING_HOT_FUNCTION')
    for group in GROUPS:
        require(mapping['groups'][group] and all(i in mapping['functions'] for i in mapping['groups'][group]),'MISSING_INLINE_OR_FUNCTION_MAPPING')
    functions={}
    for identity,entry in mapping['functions'].items():
        require(set(entry)=={'symbol','start','end','source_origins','compute_ranges','approved_marker_ranges','source_mapping_evidence_sha256'},'MAPPED_FUNCTION_SCHEMA')
        require(entry['symbol'] in report['functions'] and entry['source_origins'] and len(entry['source_mapping_evidence_sha256'])==64,'UNPROVEN_SOURCE_MAPPING')
        raw=report['functions'][entry['symbol']];start,end=entry['start'],entry['end']
        require(raw['start']==start and start<end<=raw['end'] and start%4==end%4==0,'AMBIGUOUS_FUNCTION_BOUNDARY')
        rows={r['address']:r for r in raw['instructions']}
        require(all(a in rows for a in range(start,end,4)),'INCOMPLETE_DISASSEMBLY')
        # Approved marker removal is NOT implemented by this conservative version.
        # Thus no user can whitelist arbitrary instruction differences. Full reviewed
        # functions must be identical (apart from address normalization).
        require(entry['compute_ranges']==[[start,end]] and entry['approved_marker_ranges']==[],'UNSUPPORTED_MARKER_WINDOW_EXCLUSION')
        instructions=[rows[a] for a in range(start,end,4)]
        normalized=normalize(instructions,start,end)
        require(not normalized['unresolved'],'UNRESOLVED_ADDRESS_ATTRIBUTION')
        functions[identity]={'start':start,'end':end,'alignment_mod64':start%64,'page_start':start//16384,'page_end':(end-1)//16384,
                             'boundary_status':'VERIFIED','disassembly_complete':True,'normalized':normalized}
    return _from_extracted({'synthetic':False,'build_verified':True,'variant':report['binary']['variant'],'build_identity':{k:build_context.data[k] for k in ['compiler_lock_sha256','sdk_lock_sha256']},'binary_sha256':mapping['binary_sha256'],'coverage_complete':True,'functions':functions})
