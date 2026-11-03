"""Pinned TripoSR -> CPU ViTPose -> own pose-assisted rig -> cached PNG clips.

Each invocation performs one stage and exits. No GUI, generated code or close API.
"""
import os
os.environ.update(OPENBLAS_NUM_THREADS="4", OMP_NUM_THREADS="4", HF_HUB_DISABLE_TELEMETRY="1",
                  HF_HUB_DISABLE_IMPLICIT_TOKEN="1", TOKENIZERS_PARALLELISM="false")
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import time
from urllib.request import urlopen
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
CATALOG=json.loads((HERE/'motion_catalog.json').read_text())
SOURCES=json.loads((HERE/'triposr-sources.json').read_text())


def report(stage, completed=None, total=None):
    data={'stage':stage}
    if completed is not None:data.update(completed=completed,total=total)
    print('PAWZURA_PROGRESS '+json.dumps(data),file=sys.stderr,flush=True)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(cache):
    from huggingface_hub import hf_hub_download
    report('motion_downloading',0,3)
    for index,key in enumerate(('triposr','dino_config')):
        item=CATALOG[key]
        for name,sha in item['files'].items():
            p=Path(hf_hub_download(item['repo'],name,revision=item['revision'],cache_dir=cache/'hf',token=False))
            if digest(p)!=sha:raise RuntimeError('motion_download_failed')
        report('motion_downloading',index+1,3)
    from runner import snapshot
    snapshot('pose',cache,download=True)
    source=cache.parent/'motion-source'/'triposr'
    for name,sha in SOURCES['files'].items():
        p=source/name
        # Original files are immutable; adapted optional imports go in a separate tree.
        if not p.is_file() or digest(p)!=sha:
            url=f"https://raw.githubusercontent.com/{SOURCES['repo']}/{SOURCES['revision']}/{name}"
            with urlopen(url,timeout=30) as response:data=response.read(512*1024+1)
            if len(data)>512*1024 or hashlib.sha256(data).hexdigest()!=sha:raise RuntimeError('motion_download_failed')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    adapted=cache.parent/'motion-source'/'adapted'
    for name in SOURCES['files']:
        data=(source/name).read_bytes()
        if name=='tsr/models/isosurface.py':
            text=data.decode().replace('from torchmcubes import marching_cubes\n','')
            text=text.replace('self.mc_func: Callable = marching_cubes','from torchmcubes import marching_cubes\n        self.mc_func: Callable = marching_cubes')
            data=text.encode()
        elif name=='tsr/utils.py':
            text=data.decode().replace('import rembg\n','')
            text=text.replace('image = rembg.remove(image, session=rembg_session, **rembg_kwargs)','import rembg\n        image = rembg.remove(image, session=rembg_session, **rembg_kwargs)')
            data=text.encode()
        p=adapted/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    record={'version':1,'source_revision':SOURCES['revision'],'adaptations':'Defer unused rembg/torchmcubes imports; own extraction used','files':{name:digest(adapted/name) for name in SOURCES['files']}}
    (adapted/'provenance.json').write_text(json.dumps(record,indent=2))
    report('motion_downloading',3,3)


def model_path(key,name,cache):
    from huggingface_hub import hf_hub_download
    item=CATALOG[key]
    p=Path(hf_hub_download(item['repo'],name,revision=item['revision'],cache_dir=cache/'hf',local_files_only=True,token=False))
    if digest(p)!=item['files'][name]:raise RuntimeError('motion_not_prepared')
    return p


def reconstruct(cache,job):
    import numpy as np
    from PIL import Image
    import torch
    from motion_geometry import extract,projected_colors
    source=cache.parent/'motion-source'/'adapted'
    record=json.loads((source/'provenance.json').read_text())
    if record.get('source_revision')!=SOURCES['revision'] or any(digest(source/name)!=sha for name,sha in record['files'].items()):
        raise RuntimeError('motion_not_prepared')
    if not torch.cuda.is_available() or torch.cuda.get_device_properties(0).total_memory<7.5*1024**3:
        raise RuntimeError('motion_gpu_required')
    if torch.cuda.mem_get_info()[0]<2.5*1024**3:raise RuntimeError('model_memory_error')
    sys.path.insert(0,str(source))
    from tsr.system import TSR
    from tsr.utils import resize_foreground
    report('motion_reconstructing')
    config=model_path('triposr','config.yaml',cache);model_path('triposr','model.ckpt',cache)
    dino=model_path('dino_config','config.json',cache)
    torch.set_num_threads(4);torch.cuda.reset_peak_memory_stats()
    with patch('tsr.models.tokenizers.image.hf_hub_download',return_value=str(dino)):
        model=TSR.from_pretrained(str(config.parent),'config.yaml','model.ckpt')
    model.renderer.set_chunk_size(4096);model.to('cuda').eval()
    original=Image.open(job/'source.png').convert('RGBA')
    rgba=np.asarray(resize_foreground(original,.85)).astype(np.float32)/255
    image=Image.fromarray(np.round((rgba[:,:,:3]*rgba[:,:,3:4]+(1-rgba[:,:,3:4])*.5)*255).astype(np.uint8))
    image.save(job/'reference.png')
    with torch.inference_mode():scene=model([image],device='cuda')
    if not torch.isfinite(scene).all():raise RuntimeError('motion_reconstruction_failed')
    # One shared learned scene provides consistent views; this is not multi-view fusion.
    views=[];report('motion_views',0,8)
    from tsr.utils import get_spherical_cameras
    rays_o,rays_d=get_spherical_cameras(8,0,1.9,40,192,192)
    with torch.inference_mode():
        for i in range(8):
            rgb=model.renderer(model.decoder,scene[0],rays_o[i].cuda(),rays_d[i].cuda()).cpu().numpy()
            if not np.isfinite(rgb).all():raise RuntimeError('motion_reconstruction_failed')
            Image.fromarray(np.round(np.clip(rgb,0,1)*255).astype(np.uint8)).save(job/f'view-{i}.png')
            views.append(rgb);report('motion_views',i+1,8)
        n=96;radius=float(model.renderer.cfg.radius);axis=np.linspace(-radius,radius,n,dtype=np.float32)
        grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),-1)
        density=model.renderer.query_triplane(model.decoder,torch.from_numpy(grid).cuda(),scene[0])['density_act'].cpu().numpy().reshape(n,n,n)
    vertices,faces,points=extract(density,radius)
    colors=projected_colors(points,views)
    np.savez_compressed(job/'surface.npz',vertices=vertices,faces=faces,points=points,colors=colors)
    metrics={'vertices':len(vertices),'triangles':len(faces),'samples':len(points),'peak_allocated_mib':round(torch.cuda.max_memory_allocated()/2**20,2),'method':'One TripoSR scene,8camera views,own marching tetrahedra and projected colors'}
    (job/'reconstruction.json').write_text(json.dumps(metrics))


def rig(cache,job,payload):
    import numpy as np
    import torch
    from PIL import Image
    from transformers import VitPoseForPoseEstimation,VitPoseImageProcessor
    from runner import snapshot
    from motion_geometry import fit
    report('motion_rigging')
    path=snapshot('pose',cache)
    processor=VitPoseImageProcessor.from_pretrained(path,local_files_only=True)
    model=VitPoseForPoseEstimation.from_pretrained(path,local_files_only=True,use_safetensors=True).eval()
    torch.set_num_threads(4)
    image=Image.open(job/'reference.png').convert('RGB');width,height=image.size
    with torch.inference_mode():output=model(**processor(image,boxes=[[[0,0,width,height]]],return_tensors='pt'))
    result=processor.post_process_pose_estimation(output,boxes=[[[0,0,width,height]]])[0][0]
    keypoints=result['keypoints'].numpy()/[width,height];scores=result['scores'].numpy()
    if scores.shape!=(17,) or not np.isfinite(keypoints).all() or scores[[5,6,7,8,9,10,11,12,13,14,15,16]].min()<.15:
        raise RuntimeError('motion_pose_uncertain')
    # Transform the approved source mouth point through the same foreground crop/pad.
    original=Image.open(job/'source.png').convert('RGBA');alpha=np.asarray(original)[:,:,3]
    yy,xx=np.where(alpha>0)
    x1,y1,x2,y2=xx.min(),yy.min(),xx.max()+1,yy.max()+1
    side=max(x2-x1,y2-y1);padded=int(side/.85)
    mouth=[(payload['mouth'][0]*original.width-x1+(side-(x2-x1))//2+(padded-side)//2)/padded,
           (payload['mouth'][1]*original.height-y1+(side-(y2-y1))//2+(padded-side)//2)/padded]
    with np.load(job/'surface.npz',allow_pickle=False) as data:points=data['points']
    try:bones,weights,joints,mouth3d=fit(points,keypoints,mouth)
    except (ValueError,IndexError):raise RuntimeError('motion_pose_uncertain') from None
    np.savez_compressed(job/'rig.npz',bones=bones,weights=weights,joints=joints,mouth=mouth3d)
    (job/'rig.json').write_text(json.dumps({'backend':'pose-assisted','model':'ViTPose-base-simple','minimum_score':round(float(scores.min()),4),'bones':len(bones),'limits':'Humanoid pose lifting and computed weights; not a learned3Drigging/facialmodel'}))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','reconstruct','rig','bake']);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--job',type=Path,required=True)
    args=parser.parse_args();payload=json.load(sys.stdin);start=time.monotonic()
    if not isinstance(payload,dict):raise RuntimeError('motion_runtime_failed')
    if args.action=='prepare':prepare(args.cache);names=[]
    elif args.action=='reconstruct':
        reconstruct(args.cache,args.job);names=['surface.npz','reference.png','reconstruction.json']+[f'view-{i}.png' for i in range(8)]
    elif args.action=='rig':rig(args.cache,args.job,payload);names=['rig.npz','rig.json']
    else:
        from motion_bake import bake
        bake(args.job,payload,report);names=['motion.zip']
    result={'stage':args.action,'seconds':round(time.monotonic()-start,3),'files':[{"name":name,"sha256":digest(args.job/name),"bytes":(args.job/name).stat().st_size} for name in names]}
    print(json.dumps(result))


if __name__=='__main__':
    try:main()
    except Exception as error:
        allowed={'motion_not_prepared','motion_download_failed','motion_reconstruction_failed','motion_gpu_required','model_memory_error','motion_pose_uncertain'}
        code=str(error)
        if isinstance(error,MemoryError) or 'out of memory' in code.lower():code='model_memory_error'
        print(json.dumps({'error':code if code in allowed else 'motion_runtime_failed'}));raise SystemExit(1)
