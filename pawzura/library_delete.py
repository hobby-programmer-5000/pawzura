"""Reference-aware, confirmed deletion of local character versions and unused data."""
import hashlib
import json
import re
import stat
from pathlib import Path
from . import character_library as lib,artwork,motion_pack
from .config import safe_character

class DeleteError(ValueError):
    def __init__(self,code,removed_bytes=0):super().__init__(code);self.removed_bytes=removed_bytes


def _digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _regular(path,base):
    base=Path(base).resolve();path=Path(path).absolute()
    if not path.resolve().is_relative_to(base) or path.resolve()==base:raise DeleteError('delete_unsafe')
    current=path
    while True:
        info=current.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise DeleteError('delete_unsafe')
        # Windows TEMP may use an 8.3 alias (RUNNER~1). Compare canonical
        # identities while still checking every lexical ancestor for reparses.
        if current.resolve()==base:break
        if current.parent==current:raise DeleteError('delete_unsafe')
        current=current.parent
    info=path.stat()
    if not stat.S_ISREG(info.st_mode):raise DeleteError('delete_unsafe')
    return info


def _file(path,base,limit=32*1024*1024):
    info=_regular(path,base)
    if info.st_size>limit:raise DeleteError('delete_unsafe')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    after=_regular(path,base)
    before=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
    if before!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):raise DeleteError('delete_changed')
    return {'path':str(path.absolute()),'base':str(Path(base).resolve()),'bytes':info.st_size,'identity':list(before),'sha256':digest}


def _references(folder,provider):
    refs={'active':[],'history':[]};blocked=False;stamps=[]
    if provider is not None:
        try:
            extra=provider()
            if not isinstance(extra,dict) or extra.get('busy'):raise DeleteError('delete_busy')
            for key in refs:
                if not isinstance(extra.get(key,[]),(list,tuple)):raise DeleteError('delete_references')
                refs[key].extend(extra.get(key,[]))
        except DeleteError:raise
        except Exception:raise DeleteError('delete_references') from None
    settings=lib.root(folder).parent/'settings.json'
    if settings.exists():
        try:
            stamp=_file(settings,settings.parent,1024*1024);data=json.loads(settings.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or data.get('version')!=1:raise ValueError()
            refs['active'].append(data.get('character',{}))
            if not isinstance(data.get('character_history',[]),list):raise ValueError()
            refs['history'].extend(data.get('character_history',[]));stamps.append(stamp)
        except (OSError,ValueError,TypeError):raise DeleteError('delete_references') from None
    for key,values in refs.items():
        if any(not isinstance(value,dict) for value in values):raise DeleteError('delete_references')
    return refs,stamps,blocked


def _plan(entry_id,folder,include_files,provider):
    if not artwork.valid_art_id(entry_id):raise DeleteError('delete_changed')
    library=lib.root(folder).resolve();entry_path=library/(entry_id+lib.SUFFIX)
    try:entry=lib._read(entry_path,folder);entry_stamp=_file(entry_path,library,lib.MAX_ENTRY)
    except (OSError,ValueError,KeyError,TypeError):raise DeleteError('delete_changed') from None
    refs,reference_stamps,blocked=_references(folder,provider)
    selected=lib.identity(entry['character'])
    if any(lib.identity(safe_character(spec))==selected for spec in refs['active']):raise DeleteError('delete_active')
    metadata=[entry_stamp];remaining=[]
    paths=list(library.glob('*'+lib.SUFFIX))
    if len(paths)>lib.MAX_ENTRIES:blocked=True
    for path in paths:
        if path==entry_path:continue
        try:
            metadata.append(_file(path,library,lib.MAX_ENTRY));remaining.append(lib._read(path,folder)['character'])
        except (OSError,ValueError,TypeError,KeyError):blocked=True
    all_refs=[*remaining,*refs['active'],*refs['history']]
    art_ids={s.get('art_id') for s in all_refs if artwork.valid_art_id(s.get('art_id'))}
    motion_ids={s.get('animation_id') for s in all_refs if artwork.valid_art_id(s.get('animation_id'))}
    targets=[];directories=[];kept=0;cache_stamps=[]
    spec=entry['character'];art_id=spec.get('art_id');motion_id=spec.get('animation_id')
    data_root=artwork.asset_root().parent.resolve()
    if library.parent!=data_root:blocked=True  # A custom library cannot prove ownership of another store.
    cache_root=data_root/'motion-jobs';cache_files=[];busy=False
    if include_files and artwork.valid_art_id(art_id) and cache_root.exists():
        if cache_root.is_symlink() or cache_root.resolve().parent!=data_root or getattr(cache_root.lstat(),'st_file_attributes',0)&0x400:blocked=True
        else:
            allowed={'source.png','state.json','state.tmp','surface.npz','reference.png','reconstruction.json','rig.npz','rig.json','motion.zip','motion.tmp',*(f'view-{i}.png' for i in range(8))}
            for directory in sorted(cache_root.glob(art_id+'-*')):
                if not re.fullmatch(art_id+r'-(?:staged-)?[0-9a-f]{16}',directory.name):kept+=1;continue
                try:
                    if directory.is_symlink() or directory.resolve().parent!=cache_root.resolve() or getattr(directory.lstat(),'st_file_attributes',0)&0x400:raise ValueError()
                    state_path=directory/'state.json';stamp=_file(state_path,cache_root,65536);state=json.loads(state_path.read_text())
                    cache_stamps.append(stamp)
                    if not isinstance(state,dict) or state.get('status') not in ('ready','failed','cancelled'):
                        busy=True;kept+=1;continue
                    files=list(directory.iterdir())
                    if any(p.name not in allowed for p in files):kept+=1;continue
                    records=[_file(p,cache_root) for p in files]
                    cache_files.append((str(directory.absolute()),records))
                except (OSError,ValueError,TypeError):busy=True;kept+=1
    def add(path,base):
        nonlocal kept
        if not path.exists() and not path.is_symlink():return
        try:targets.append(_file(path,base))
        except (OSError,ValueError):kept+=1
    if include_files and not blocked and not busy:
        if artwork.valid_art_id(motion_id):
            if motion_id not in motion_ids:add(motion_pack.asset_root()/(motion_id+'.zip'),data_root)
            else:kept+=1
        if artwork.valid_art_id(art_id):
            if art_id not in art_ids:
                add(artwork.asset_root()/(art_id+'.png'),data_root)
                for directory,records in cache_files:directories.append(directory);targets.extend(records)
            else:kept+=1+len(cache_files)
    elif include_files:kept+=bool(art_id)+bool(motion_id)+len(cache_files)
    targets.append(entry_stamp)  # Metadata last: a failed cleanup remains retryable in the list.
    descriptor={'entry_id':entry_id,'name':entry['name'],'include_files':bool(include_files),'targets':targets,'directories':directories,
                'references':refs,'reference_stamps':reference_stamps,'metadata':metadata,'cache_stamps':cache_stamps,'blocked':blocked,'busy':busy,'kept':kept}
    return {'entry_id':entry_id,'name':entry['name'],'include_files':bool(include_files),'bytes':sum(f['bytes'] for f in targets),
            'files':len(targets),'kept':kept,'cleanup_limited':blocked or busy,'token':_digest(descriptor),'_descriptor':descriptor}


def plan_delete(entry_id,folder=None,include_files=True,reference_provider=None):
    with lib.storage_lock(folder):return _plan(entry_id,folder,include_files,reference_provider)


def delete(plan,folder=None,reference_provider=None):
    with lib.storage_lock(folder):
        current=_plan(plan['entry_id'],folder,plan['include_files'],reference_provider)
        if current['token']!=plan['token']:raise DeleteError('delete_changed')
        removed=0;count=0
        try:
            for record in current['_descriptor']['targets'][:-1]:
                path=Path(record['path'])
                if _file(path,record['base'])!=record:raise DeleteError('delete_changed',removed)
                path.unlink();removed+=record['bytes'];count+=1
            # Never recursively remove a calculated path. Unknown files keep their directory.
            cache_root=artwork.asset_root().parent.resolve()/'motion-jobs'
            for name in current['_descriptor']['directories']:
                directory=Path(name)
                if directory.resolve().parent!=cache_root.resolve() or directory.is_symlink():raise DeleteError('delete_unsafe',removed)
                directory.rmdir()
            record=current['_descriptor']['targets'][-1]
            path=Path(record['path'])
            if _file(path,record['base'])!=record:raise DeleteError('delete_changed',removed)
            path.unlink();removed+=record['bytes'];count+=1
        except (OSError,ValueError) as error:
            artwork._IMAGES.clear();motion_pack._PACKS.clear();motion_pack._FRAMES.clear()
            if isinstance(error,DeleteError):
                error.removed_bytes=removed
                raise
            raise DeleteError('delete_partial',removed) from None
        artwork._IMAGES.clear();motion_pack._PACKS.clear();motion_pack._FRAMES.clear()
        return {'removed_bytes':removed,'removed_files':count,'kept':current['kept']}
