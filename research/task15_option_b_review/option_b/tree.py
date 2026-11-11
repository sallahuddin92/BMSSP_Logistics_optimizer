"""Streaming no-follow tree inventory with metadata/race/alias/closure checks."""
from collections import deque
import hashlib
import os
from pathlib import Path
import stat
from .core import require,sha,canonical,ReviewError

MAX_ENTRIES=200000


def stamp(st):return (st.st_dev,st.st_ino,st.st_mode,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
def inside(path,roots):return any(path==r or r in path.parents for r in roots)


def resolve_safe(path,roots,aliases=()):
    """Resolve one component at a time; never inspect an outside target's bytes."""
    path=Path(os.path.abspath(path));roots=[Path(os.path.abspath(r)) for r in roots];aliases=[Path(os.path.abspath(a)) for a in aliases]
    def authorized(p):return inside(p,roots) or any(p==a or a in p.parents for a in aliases)
    require(authorized(path),'SYMLINK_ESCAPE')
    pending=list(path.parts[1:]);current=Path('/');hops=0
    while pending:
        current=current/pending.pop(0)
        # Prefix metadata is needed to reach the explicitly authorized root. Do not
        # follow a prefix symlink unless its target remains in the declared roots.
        try:st=current.lstat()
        except OSError as exc:raise ReviewError('SYMLINK_TARGET_UNAVAILABLE:'+str(current)) from exc
        if stat.S_ISLNK(st.st_mode):
            hops+=1;require(hops<=40,'SYMLINK_CYCLE')
            target=os.readlink(current);target=Path(os.path.normpath(str(current.parent/target if not os.path.isabs(target) else Path(target))))
            require(authorized(target),'SYMLINK_ESCAPE')
            path=target.joinpath(*pending);require(authorized(path),'SYMLINK_ESCAPE')
            pending=list(path.parts[1:]);current=Path('/')
    require(inside(current,roots),'SYMLINK_ESCAPE')
    return current


def content_hash(path,before,cache,after_read=None):
    identity=stamp(before)
    if identity in cache:return cache[identity],True
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(path,flags)
    try:
        require(stamp(os.fstat(fd))==identity,'FILE_CHANGED_BEFORE_READ')
        h=hashlib.sha256()
        with os.fdopen(fd,'rb',closefd=False) as stream:
            while chunk:=stream.read(1024*1024):h.update(chunk)
        if after_read:after_read(path)
        require(stamp(os.fstat(fd))==identity and stamp(Path(path).lstat())==identity,'FILE_CHANGED_DURING_READ')
        value=h.hexdigest();cache[identity]=value;return value,False
    finally:os.close(fd)


def walk(root,errors=None):
    """Enumerate physical entries once; symlink directories are never traversed."""
    root=Path(root);result=[];todo=[root];errors=[] if errors is None else errors
    while todo:
        path=todo.pop();relative='.' if path==root else path.relative_to(root).as_posix()
        try:st=path.lstat()
        except OSError as exc:errors.append({'path':relative,'code':'INCOMPLETE_TRAVERSAL','message':str(exc)});continue
        target=None
        if stat.S_ISLNK(st.st_mode):
            try:target=os.readlink(path)
            except OSError as exc:errors.append({'path':relative,'code':'INCOMPLETE_SYMLINK_READ','message':str(exc)})
        result.append((relative,path,st,target))
        require(len(result)<=MAX_ENTRIES,'TREE_ENTRY_BOUND')
        if stat.S_ISDIR(st.st_mode):
            try:
                with os.scandir(path) as it:names=sorted(entry.name for entry in it)
            except OSError as exc:errors.append({'path':relative,'code':'INCOMPLETE_TRAVERSAL','message':str(exc)});continue
            todo.extend(path/name for name in reversed(names))
    return sorted(result,key=lambda v:v[0])


def inventory(root,root_id,authorized_roots=None,aliases=(),cache=None,after_read=None):
    root=Path(os.path.abspath(root));authorized_roots=[Path(os.path.abspath(r)) for r in (authorized_roots or [root])];cache={} if cache is None else cache
    if not root.is_dir():return {'root':str(root),'root_id':root_id,'status':'MISSING_OR_UNAVAILABLE','traversal_complete':False,'closure_complete':False,'tree_sha256':None,'entries':[],'errors':[{'code':'ROOT_UNAVAILABLE'}],'aliases':[]}
    require(not root.is_symlink(),'ROOT_REDIRECTION')
    entries=[];errors=[];duplicates=[];seen={};physical={};initial=[]
    try:initial=walk(root,errors)
    except (OSError,ReviewError) as exc:errors.append({'code':'INCOMPLETE_TRAVERSAL','message':str(exc)})
    initial_map={name:(stamp(st),link) for name,path,st,link in initial}
    for name,path,st,target in initial:
        row={'path':name,'type':'directory' if stat.S_ISDIR(st.st_mode) else 'file' if stat.S_ISREG(st.st_mode) else 'symlink' if stat.S_ISLNK(st.st_mode) else 'unsupported',
             'size':st.st_size if stat.S_ISREG(st.st_mode) else None,'mode':stat.S_IMODE(st.st_mode),'symlink_target':target,'sha256':None,'resolved_target':None,'alias_of':None}
        try:
            if row['type']=='file':
                value,dedup=content_hash(path,st,cache,after_read);row['sha256']=value
                inode=(st.st_dev,st.st_ino)
                if inode in seen:row['alias_of']=seen[inode];duplicates.append({'path':name,'alias_of':seen[inode],'kind':'hardlink'})
                else:seen[inode]=name
                physical[str(path)]=row
            elif row['type']=='unsupported':raise ReviewError('UNSUPPORTED_FILE_TYPE')
        except (OSError,ReviewError) as exc:errors.append({'path':name,'code':str(exc)})
        entries.append(row)
    for row in entries:
        if row['type']!='symlink':continue
        path=root/row['path']
        try:
            resolved=resolve_safe(path,authorized_roots,aliases);row['resolved_target']=str(resolved)
            if resolved.is_file():
                st=resolved.lstat();value,_=content_hash(resolved,st,cache,after_read);row['sha256']=value
            row['alias_of']=str(resolved)
            duplicates.append({'path':row['path'],'alias_of':str(resolved),'kind':'symlink'})
        except (OSError,ReviewError) as exc:errors.append({'path':row['path'],'code':str(exc)})
    try:
        final=walk(root,errors);final_map={name:(stamp(st),link) for name,path,st,link in final}
        if initial_map!=final_map:errors.append({'code':'TREE_CHANGED_DURING_INVENTORY'})
    except (OSError,ReviewError) as exc:errors.append({'code':'INCOMPLETE_FINAL_TRAVERSAL','message':str(exc)})
    # Identity excludes inode/timestamps/absolute resolution observations. Symlink
    # targets, relative names, types, modes, sizes and bytes remain deterministic.
    identities=[{k:r[k] for k in ['path','type','size','mode','symlink_target','sha256']} for r in entries]
    return {'root':str(root),'root_id':root_id,'status':'CURRENT_BYTES_VERIFIED' if not errors else 'CURRENT_BYTES_PARTIAL',
            'traversal_complete':not any(e['code'].startswith(('INCOMPLETE','TREE_CHANGED')) for e in errors),'closure_complete':not errors,
            'tree_sha256':sha(canonical(identities)),'entries':entries,'entry_count':len(entries),'regular_file_bytes':sum(r['size'] or 0 for r in entries),'errors':errors,'aliases':duplicates,
            'identity_definition':'SHA256 canonical relative path/type/mode/size/raw symlink target/content SHA list; metadata checked before/after each read and traversal. No snapshot/adversarial OS immutability claim.'}
