"""Own procedural humanoid motion/facial correctives, baked as bounded PNG data."""
import hashlib
import io
import json
import math
import zipfile
import numpy as np
from PIL import Image
from motion_geometry import smooth,ry,rz,pose

COUNTS={'idle_front':90,'walk_left':72,'walk_right':72,'turn_left':8,'turn_right':8,
        'return_left':8,'return_right':8,'wave':48,'hop':27,'cheer':36,'bite_left':30,'bite_right':30}


def face(points,colors,joints,mouth,blink,opening,smile,height):
    p=points.copy();c=colors.copy();eyes=joints[[1,2]].copy()
    distance=max(height*.08,abs(eyes[0,1]-eyes[1,1]));front=p[:,0]>mouth[0]-height*.14
    skin_region=front&(abs(p[:,1]-mouth[1])<distance*.7)&(abs(p[:,2]-mouth[2])<height*.035)
    skin=c[skin_region & (c.mean(1)>.6)]
    skin=np.median(skin,0) if len(skin)>5 else np.array([.93,.79,.65])
    for eye in eyes:
        influence=(1-smooth(distance*.35,distance*.60,abs(p[:,1]-eye[1])))*(1-smooth(distance*.16,distance*.27,abs(p[:,2]-eye[2])))*front
        aperture=distance*.19*(1-blink)
        lid=influence*smooth(aperture-.0015,aperture+.003,abs(p[:,2]-eye[2]))*blink
        c=c*(1-lid[:,None])+skin*lid[:,None]
        curve=eye[2]+height*.003*((p[:,1]-eye[1])/(distance*.36))**2
        line=influence*(1-smooth(height*.001,height*.003,abs(p[:,2]-curve)))*smooth(.72,1,blink)
        c=c*(1-line[:,None])+np.array([.23,.16,.13])*line[:,None]
    dy=p[:,1]-mouth[1];dz=p[:,2]-mouth[2]
    jaw_weight=front*(1-smooth(height*.0,height*.04,dz))*smooth(-height*.08,-height*.04,dz)*(1-smooth(distance*.42,distance*.8,abs(dy)))
    pivot=mouth+[-height*.13,0,height*.035]
    jaw=(p-pivot)@ry(opening*.23).T+pivot
    p+=jaw_weight[:,None]*(jaw-p)
    corners=front*np.exp(-((abs(dy)-distance*.24)/(distance*.13))**2-(dz/(distance*.13))**2)
    p[:,2]+=smile*height*.009*corners
    cover=front&(abs(dy)<distance*.45)&(abs(dz)<height*.016)
    amount=float(smooth(.08,.35,opening));c[cover]=c[cover]*(1-amount)+skin*amount
    extra=[];extra_colors=[]
    if opening>.01:
        for radius in np.linspace(0,1,17):
            theta=np.linspace(0,2*math.pi,max(16,int(radius*160)),endpoint=False)
            y=mouth[1]+distance*.42*radius*np.cos(theta)
            z=mouth[2]-height*.006*opening+(height*.005+height*.023*opening)*radius*np.sin(theta)
            x=mouth[0]+height*.003-1.9*(y-mouth[1])**2/height-height*.004*(1-radius)
            color=np.tile([.19,.075,.09],(len(y),1));color[radius>.91]=[.68,.37,.31]
            color[(radius<.8)&(z>mouth[2]+opening*height*.012)]=[.98,.95,.85]
            color[(radius<.72)&(z<mouth[2]-opening*height*.012)]=[.83,.31,.39]
            extra.append(np.stack([x,y,z],1));extra_colors.append(color)
    return p,c,np.concatenate(extra) if extra else np.empty((0,3)),np.concatenate(extra_colors) if extra else np.empty((0,3))


def render(points,colors,yaw,floor,top,mouth):
    p=rz(points,yaw);m=rz(mouth[None],yaw)[0]
    size=256;scale=size*.90/(top-floor)
    u=np.rint(size*.5+p[:,1]*scale).astype(np.int32)
    v=np.rint(size-1-(p[:,2]-floor)*scale).astype(np.int32)
    n=len(p);rank=np.rint((3-p[:,0])*1e6).astype(np.int64)*n+np.arange(n,dtype=np.int64)
    sentinel=np.iinfo(np.int64).max;buffer=np.full(size*size,sentinel,np.int64)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            x=u+dx;y=v+dy;hit=(x>=0)&(x<size)&(y>=0)&(y<size)
            np.minimum.at(buffer,y[hit]*size+x[hit],rank[hit])
    hit=buffer!=sentinel;rgba=np.zeros((size*size,4),np.uint8)
    rgba[hit,:3]=np.round(np.clip(colors[(buffer[hit]%n).astype(np.int32)],0,1)*255).astype(np.uint8);rgba[hit,3]=255
    anchor=[float((size*.5+m[1]*scale)/size),float((size-1-(m[2]-floor)*scale)/size)]
    if not all(math.isfinite(x) and 0<=x<=1 for x in anchor):raise ValueError('Invalid contact anchor')
    return Image.fromarray(rgba.reshape(size,size,4),'RGBA'),anchor


def bake(job,payload,report):
    with np.load(job/'surface.npz',allow_pickle=False) as data:points=data['points'];colors=data['colors']
    with np.load(job/'rig.npz',allow_pickle=False) as data:bones=data['bones'];weights=data['weights'];joints=data['joints'];mouth=data['mouth']
    if (points.ndim!=2 or points.shape[1]!=3 or len(points)>300000 or weights.shape!=(len(points),12) or
            bones.shape!=(12,2,3) or not all(np.isfinite(x).all() for x in (points,colors,bones,weights,joints,mouth)) or
            np.max(abs(weights.sum(1)-1))>1e-4 or weights.min()<0):raise ValueError('Invalid rig')
    floor=float(points[:,2].min());top=float(points[:,2].max());height=top-floor
    manifest={'version':1,'source_art_id':payload['source_art_id'],'backend':'triposr-pose-v1','size':256,'fps':30,'clips':{}}
    total=sum(COUNTS.values());done=0;report('motion_baking',0,total)
    target=job/'motion.zip';temporary=job/'motion.tmp'
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
        for clip,count in COUNTS.items():
            manifest['clips'][clip]=[]
            for i in range(count):
                t=i/30;u=i/max(1,count-1);gait=1 if clip.startswith('walk_') else 0
                yaw=-math.pi/2 if clip.endswith('left') else math.pi/2 if clip.endswith('right') else 0
                if clip.startswith('turn_'):yaw*=float(smooth(0,1,u))
                elif clip.startswith('return_'):yaw*=1-float(smooth(0,1,u))
                blink=math.exp(-((t-count/30*.70)/.07)**2) if clip.startswith(('walk_','idle_')) else 0
                opening=(float(smooth(.35,.65,t))*(1-float(smooth(.72,.94,t)))) if clip.startswith('bite_') else 0
                tucked=math.sin(math.pi*u)*.7 if clip in ('hop','cheer') else math.sin(math.pi*min(t/.72,1))*.6 if clip.startswith('bite_') else 0
                matrices,_=pose(bones,phase=t/.8,gait=gait,crouch=math.sin(math.pi*u)*.4 if clip=='hop' else 0,
                                tucked=tucked,bite=opening,wave=math.sin(math.pi*u)**2 if clip in ('wave','cheer') else 0,height=height)
                p,c,extras,extra_colors=face(points,colors,joints,mouth,blink,opening,.3+.15*math.sin(t*2),height)
                deformed=np.zeros_like(p)
                for number,(rot,trans) in enumerate(matrices):
                    hit=weights[:,number]>1e-6
                    deformed[hit]+=(p[hit]@rot.T+trans)*weights[hit,number,None]
                r,tr=matrices[0];mouth_now=mouth@r.T+tr
                if len(extras):deformed=np.concatenate([deformed,extras@r.T+tr]);c=np.concatenate([c,extra_colors])
                image,anchor=render(deformed,c,yaw,floor,top,mouth_now)
                output=io.BytesIO();image.save(output,'PNG');png=output.getvalue();name=f'frames/{clip}-{i:03}.png'
                archive.writestr(name,png);manifest['clips'][clip].append({'file':name,'sha256':hashlib.sha256(png).hexdigest(),'mouth':anchor})
                done+=1
                if done%8==0 or done==total:report('motion_baking',done,total)
        archive.writestr('manifest.json',json.dumps(manifest,separators=(',',':')))
    temporary.replace(target)
