"""Original bounded mesh extraction and humanoid pose-assisted skinning math."""
import math
import numpy as np


def smooth(a, b, x):
    u = np.clip((x-a)/(b-a), 0, 1)
    return u*u*(3-2*u)


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


def rz(points, a):
    c, s = math.cos(a), math.sin(a)
    return points @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]], np.float32)


def extract(density, radius=1., threshold=25.):
    n = density.shape[0]
    if density.shape != (n, n, n) or not 32 <= n <= 128 or not np.isfinite(density).all():
        raise ValueError('Invalid density grid')
    axis = np.linspace(-radius, radius, n, dtype=np.float32)
    offsets = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
    base = np.stack(np.meshgrid(*[np.arange(n-1)]*3, indexing='ij'), -1).reshape(-1,3)
    values = np.stack([density[base[:,0]+o[0],base[:,1]+o[1],base[:,2]+o[2]] for o in offsets], 1)
    active = (values.min(1)<threshold) & (values.max(1)>=threshold)
    base, values = base[active], values[active]
    positions = axis[base[:,None,:]+offsets[None,:,:]]
    triangles = []
    for tet in ((0,5,1,6),(0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6)):
        val, pos = values[:,tet], positions[:,tet]
        bits = ((val>=threshold)*[1,2,4,8]).sum(1)
        for case in range(1,15):
            hit = bits==case
            if not hit.any():
                continue
            q, d = pos[hit], val[hit]
            inside = [i for i in range(4) if case & (1<<i)]
            outside = [i for i in range(4) if not case & (1<<i)]
            def edge(a,b):
                t = (threshold-d[:,a])/(d[:,b]-d[:,a])
                return q[:,a]+t[:,None]*(q[:,b]-q[:,a])
            if len(inside) in (1,3):
                one, rest = (inside[0],outside) if len(inside)==1 else (outside[0],inside)
                triangles.append(np.stack([edge(one,j) for j in rest],1))
            else:
                a,b=inside; c,d_=outside
                quad=[edge(a,c),edge(a,d_),edge(b,d_),edge(b,c)]
                triangles += [np.stack([quad[0],quad[1],quad[2]],1),np.stack([quad[0],quad[2],quad[3]],1)]
    if not triangles:
        raise ValueError('Empty surface')
    tri = np.concatenate(triangles).astype(np.float32)
    vertices, inverse = np.unique(np.round(tri.reshape(-1,3),6),axis=0,return_inverse=True)
    cloud = [tri[:,0]*(i/3)+tri[:,1]*(j/3)+tri[:,2]*((3-i-j)/3) for i in range(4) for j in range(4-i)]
    points = np.unique(np.round(np.concatenate(cloud),6),axis=0).astype(np.float32)
    if len(points)>300000 or len(vertices)>100000 or len(tri)>200000:
        raise ValueError('Surface too large')
    return vertices, inverse.reshape(-1,3).astype(np.int32), points


def projected_colors(points, views):
    from scipy.ndimage import map_coordinates
    from scipy.spatial import cKDTree
    count=len(views);side=views[0].shape[0];focal=side*.5/math.tan(math.radians(20))
    angle=(np.arctan2(points[:,1],points[:,0])%(2*math.pi))*count/(2*math.pi)
    base=np.floor(angle).astype(int);fraction=angle-base;colors=np.zeros((len(points),3),np.float32)
    for delta in (0,1):
        ids=(base+delta)%count;weights=1-fraction if delta==0 else fraction
        for i in range(count):
            hit=ids==i;p=points[hit];a=i*2*math.pi/count;c,s=math.cos(a),math.sin(a)
            depth=1.9-p[:,0]*c-p[:,1]*s
            u=side*.5-.5+(-p[:,0]*s+p[:,1]*c)*focal/depth
            v=side*.5-.5-p[:,2]*focal/depth
            rgb=np.stack([map_coordinates(views[i][:,:,j],[v,u],order=1,mode='nearest') for j in range(3)],1)
            colors[hit]+=rgb*weights[hit,None]
    height=np.ptp(points[:,2]);zmin=points[:,2].min()
    region=(points[:,2]>zmin+height*.77)|(points[:,2]<zmin+height*.22)
    bad=region&(colors.min(1)>.88);good=region&(colors.min(1)<.75)
    if good.any() and bad.any():
        distances,near=cKDTree(points[good]).query(points[bad]);use=distances<height*.055
        colors[np.flatnonzero(bad)[use]]=colors[good][near[use]]
    return np.clip(colors,0,1).astype(np.float32)


def lift(points, uv):
    from scipy.spatial import cKDTree
    depth=1.9-points[:,0];focal=.5/math.tan(math.radians(20))
    projected=np.stack([.5+points[:,1]*focal/depth,.5-points[:,2]*focal/depth],1)
    _,nearest=cKDTree(projected).query(np.asarray(uv),k=48)
    return np.median(points[nearest],axis=1).astype(np.float32)


def fit(points, keypoints, mouth_uv):
    joints=lift(points,keypoints)
    # Apply the same depth regularization before deriving every body/limb pivot.
    joints[:,0]=np.median(points[:,0])*.65+joints[:,0]*.35
    height=float(np.ptp(points[:,2]));shoulder=(joints[5]+joints[6])/2;hip=(joints[11]+joints[12])/2
    if height<.1 or shoulder[2]<=hip[2] or np.linalg.norm(joints[5]-joints[6])<height*.08:
        raise ValueError('Unsupported pose')
    # Place joints inside the limbs rather than on the front texture surface.
    neck=shoulder.copy();neck[2]+=height*.035
    head=(joints[1]+joints[2])/2
    bones=[(neck,head),(hip,neck)]
    names=['head','body']
    for shoulder_i,elbow_i,wrist_i,hip_i,knee_i,ankle_i,label in ((5,7,9,11,13,15,'left'),(6,8,10,12,14,16,'right')):
        s,e,w,h,k,a=joints[[shoulder_i,elbow_i,wrist_i,hip_i,knee_i,ankle_i]]
        if min(s[2]-w[2],h[2]-a[2])<height*.08:
            raise ValueError('Hidden or crossed limbs')
        toe=a+np.array([height*.075,0,-height*.015])
        bones += [(s,e),(e,w),(h,k),(k,a),(a,toe)]
        names += [label+'_'+x for x in ('arm','forearm','thigh','shin','foot')]
    bones=np.asarray(bones,np.float32)
    lengths=np.linalg.norm(bones[:,1]-bones[:,0],axis=1)
    if not np.isfinite(bones).all() or lengths.min()<height*.025:
        raise ValueError('Uncertain joints')
    distances=[]
    for a,b in bones:
        t=np.clip(((points-a)@(b-a))/np.dot(b-a,b-a),0,1)
        distances.append(np.linalg.norm(points-(a+t[:,None]*(b-a)),axis=1))
    distances=np.stack(distances,1)
    weights=np.exp(-((distances-distances.min(1,keepdims=True))/(height*.045))**2)
    # Rigid head, with a smooth neck seam; prevents hair being assigned to arms.
    head_weight=smooth(neck[2]-height*.015,neck[2]+height*.045,points[:,2])
    weights[:,0]=0;weights/=np.maximum(weights.sum(1,keepdims=True),1e-9)
    weights*=1-head_weight[:,None];weights[:,0]=head_weight
    weights/=weights.sum(1,keepdims=True)
    mouth=lift(points,[mouth_uv])[0]
    mouth[0]=np.percentile(points[(abs(points[:,1]-mouth[1])<height*.025)&(abs(points[:,2]-mouth[2])<height*.02),0],95)
    return bones,weights.astype(np.float32),joints,mouth


def knee_at(hip,ankle,l1,l2):
    delta=ankle-hip;dy=delta[1]
    distance=math.hypot(delta[0],delta[2]);limit=l1+l2
    if distance>limit+1e-4:
        raise ValueError('Unreachable leg target')
    distance=max(1e-6,min(distance,limit-1e-6))
    direction=np.array([delta[0],0,delta[2]])/max(1e-6,math.hypot(delta[0],delta[2]))
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    p=hip+direction*along+np.array([-direction[2],0,direction[0]])*math.sqrt(max(0,l1*l1-along*along))
    p[1]+=dy*.5
    return p


def pose(bones, phase=0., gait=0., crouch=0., tucked=0., bite=0., wave=0., height=1.):
    targets=bones.copy();stride=42*.8/(4*144*.9)*height
    # Single-image reconstruction often leans the torso backwards. Repose the
    # upper body around the shared pelvis, preserving lengths and connections.
    pelvis=bones[1,0]
    spine=bones[1,1]-pelvis
    rest_lean=math.atan2(float(spine[0]),float(spine[2]))
    upright=float(np.clip(math.radians(2)-rest_lean,-math.radians(20),math.radians(20)))
    upper=ry(upright)
    drop=0.
    for i in (4,9):
        hip=bones[i,0];ankle=bones[i+1,1];length=sum(np.linalg.norm(bones[j,1]-bones[j,0]) for j in (i,i+1))
        reach=math.sqrt(max(.001,length*length-(abs(ankle[0]-hip[0])+stride)**2))*.98
        drop=min(drop,ankle[2]+reach-hip[2])
    shift=np.array([0,0,drop*gait-height*.05*crouch])
    targets[:2]=(bones[:2]-pelvis)@upper.T+pelvis+shift
    for offset,start in ((0,2),(.5,7)):
        u=(phase+offset)%1
        swing=math.radians(25*math.sin(u*2*math.pi)*gait-30*tucked-18*bite-45*wave*(1 if start==7 else 0))
        targets[start,0]=(bones[start,0]-pelvis)@upper.T+pelvis+shift
        targets[start,1]=targets[start,0]+ry(swing+upright)@(bones[start,1]-bones[start,0])
        targets[start+1,0]=targets[start,1]
        targets[start+1,1]=targets[start+1,0]+ry(swing+upright-math.radians(12*gait+35*tucked))@(bones[start+1,1]-bones[start+1,0])
        hip=bones[start+2,0]+shift;ankle=bones[start+3,1].copy()
        if u<.5:dx=stride*(1-4*u);lift_z=0
        else:
            f=(u-.5)*2;dx=-stride*math.cos(math.pi*f);lift_z=height*.045*math.sin(math.pi*f)
        ankle+=np.array([gait*dx,0,gait*lift_z+tucked*height*.06])
        l1=np.linalg.norm(bones[start+2,1]-bones[start+2,0]);l2=np.linalg.norm(bones[start+3,1]-bones[start+3,0])
        knee=knee_at(hip,ankle,l1,l2)
        targets[start+2]=(hip,knee);targets[start+3]=(knee,ankle)
        targets[start+4]=(ankle,ankle+ry(math.radians(12*tucked))@(bones[start+4,1]-bones[start+4,0]))
    matrices=[]
    for index,((a,b),(pa,pb)) in enumerate(zip(bones,targets)):
        v=b-a;nv=pb-pa
        angle=math.atan2(-nv[0],-nv[2])-math.atan2(-v[0],-v[2])
        if index==0:angle=upright-math.radians(7*bite)
        r=ry(angle);matrices.append((r,pa-r@a))
    return matrices,targets
