"""Named local character versions. Pixels/clips remain content-addressed local assets."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime,timezone
from contextlib import contextmanager
import threading
from .config import data_dir,safe_character
from . import artwork,motion_pack

FORMAT='pawzura-character-v1'
SUFFIX='.pawzura-character.json'
MAX_ENTRIES=500
MAX_ENTRY=32768
_STORAGE_THREAD_LOCK=threading.RLock()
_STORAGE_LOCAL=threading.local()


@contextmanager
def storage_lock(folder=None):
    """Serialize owned file/reference mutations across threads and app instances."""
    if not _STORAGE_THREAD_LOCK.acquire(timeout=1):raise OSError('Character storage is busy')
    lock=None
    try:
        base=root(folder).parent.resolve()
        depths=getattr(_STORAGE_LOCAL,'depths',{})
        key=str(base);depth=depths.get(key,0)
        if not depth:
            from PySide6.QtCore import QLockFile
            base.mkdir(parents=True,exist_ok=True)
            lock=QLockFile(str(base/'.character-storage.lock'));lock.setStaleLockTime(0)
            if not lock.tryLock(1000):raise OSError('Character storage is busy')
        depths[key]=depth+1;_STORAGE_LOCAL.depths=depths
        try:yield
        finally:depths[key]=depth
    finally:
        if lock is not None:lock.unlock()
        _STORAGE_THREAD_LOCK.release()


def root(folder=None):return Path(folder) if folder is not None else artwork.asset_root().parent/'character-library'


def identity(spec):
    return hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def validate_assets(spec):
    if spec.get('kind')!='artwork':return
    path=artwork.asset_root()/(spec['art_id']+'.png')
    if path.resolve().parent!=artwork.asset_root().resolve() or path.stat().st_size>artwork.MAX_ART_BYTES:raise ValueError('Invalid source')
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=spec['art_id']:raise ValueError('Missing/corrupt source')
    artwork.validate_png(data)
    if spec.get('animation_id'):
        path=motion_pack.asset_root()/(spec['animation_id']+'.zip')
        if path.resolve().parent!=motion_pack.asset_root().resolve() or path.stat().st_size>motion_pack.MAX_PACK:raise ValueError('Invalid motion')
        data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=spec['animation_id']:raise ValueError('Missing/corrupt motion')
        # Recheck disk identity every time, reuse decoded validation for the
        # same immutable content hash rather than decoding hundreds of PNGs.
        if motion_pack.load_pack(spec['animation_id'],spec['art_id']) is None:raise ValueError('Invalid motion')


def _read(path,folder=None):
    if path.resolve().parent!=root(folder).resolve() or path.stat().st_size>MAX_ENTRY:raise ValueError('Invalid entry')
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('format')!=FORMAT:raise ValueError('Invalid entry')
    raw=data.get('character')
    if not isinstance(raw,dict):raise ValueError('Invalid appearance')
    spec=safe_character(raw)
    if (set(raw)-set(spec) or raw.get('kind')=='artwork' and spec.get('kind')!='artwork' or
        data.get('id')!=identity(raw) or path.name!=data['id']+SUFFIX):raise ValueError('Invalid identity')
    name=data.get('name')
    if not isinstance(name,str) or not name.strip() or len(name)>64 or any(ord(c)<32 for c in name):raise ValueError('Invalid name')
    return {'format':FORMAT,'id':data['id'],'name':name,'character':spec}


def entries(folder=None):
    result=[]
    for path in sorted(root(folder).glob('*'+SUFFIX),key=lambda p:p.name)[:MAX_ENTRIES]:
        try:result.append(_read(path,folder))
        except (OSError,ValueError,TypeError,KeyError):continue
    return sorted(result,key=lambda e:(e['name'].casefold(),e['id']))


def load(entry_id,folder=None):
    if not artwork.valid_art_id(entry_id):raise ValueError('Invalid identity')
    with storage_lock(folder):
        data=_read(root(folder)/(entry_id+SUFFIX),folder);validate_assets(data['character']);return data


def save(spec,name=None,folder=None):
    with storage_lock(folder):return _save(spec,name,folder)


def _save(spec,name=None,folder=None):
    raw=spec;spec=safe_character(spec)
    if not isinstance(raw,dict) or raw.get("kind")=="artwork" and spec.get("kind")!="artwork":raise ValueError("Invalid character")
    validate_assets(spec)
    entry_id=identity(spec);folder=root(folder).resolve();folder.mkdir(parents=True,exist_ok=True);path=folder/(entry_id+SUFFIX)
    if path.resolve().parent!=folder:raise ValueError('Invalid destination')
    old=None
    if path.exists():
        try:old=_read(path,folder)
        except (OSError,ValueError,TypeError,KeyError):pass
    if name is None:
        name=old['name'] if old else ('Artwork 3D' if spec.get('animation_id') else 'Artwork 2D' if spec.get('kind')=='artwork' else 'Vector')+' · '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    if not isinstance(name,str) or not name.strip() or len(name.strip())>64 or any(ord(c)<32 for c in name):raise ValueError('Use 1-64 printable characters')
    if not path.exists() and len(list(folder.glob('*'+SUFFIX)))>=MAX_ENTRIES:raise ValueError('Library is full')
    data={'format':FORMAT,'id':entry_id,'name':name.strip(),'character':spec}
    payload=json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2).encode('utf-8')
    if len(payload)>MAX_ENTRY:raise ValueError('Entry too large')
    fd,temporary=tempfile.mkstemp(prefix='character-',suffix='.tmp',dir=folder)
    try:
        with os.fdopen(fd,'wb') as output:output.write(payload)
        os.replace(temporary,path)
    finally:Path(temporary).unlink(missing_ok=True)
    return data


def try_save(spec,folder=None):
    try:save(spec,folder=folder);return True
    except (OSError,ValueError):return False
