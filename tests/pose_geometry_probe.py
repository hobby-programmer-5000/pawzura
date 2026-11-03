"""Optional isolated-runtime math regressions; requires its existing NumPy/SciPy."""
import sys,unittest,math
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'art_runtime'))
import numpy as np
import motion_geometry as g

class PoseGeometryTests(unittest.TestCase):
 def fixture(self):
  joints=np.array([[.3,0,.35],[.28,.06,.4],[.28,-.06,.4],[.2,.12,.4],[.2,-.12,.4],
   [.12,.15,.2],[.12,-.15,.2],[.15,.24,-.05],[.15,-.24,-.05],[.2,.25,-.25],[.2,-.25,-.25],
   [.3,.1,-.15],[.3,-.1,-.15],[.22,.1,-.35],[.22,-.1,-.35],[.2,.1,-.56],[.2,-.1,-.56]],np.float32)
  points=np.random.default_rng(123).uniform([-.25,-.3,-.65],[.35,.3,.6],(6000,3)).astype(np.float32)
  points=np.concatenate([points,np.array([[.25,0,.32],[.26,.01,.32]],np.float32)])
  with patch.object(g,'lift',side_effect=[joints.copy(),np.array([[.25,0,.32]],np.float32)]):
   b,w,j,m=g.fit(points,np.zeros((17,2)),[.5,.4])
  return b,w,j,m,float(np.ptp(points[:,2]))
 def test_body_and_limb_pivots_share_regularized_joint_depths(self):
  b,w,j,m,h=self.fixture();np.testing.assert_allclose(b[1,0],(j[11]+j[12])/2,atol=1e-6)
  neck=(j[5]+j[6])/2;neck[2]+=h*.035;np.testing.assert_allclose(b[1,1],neck,atol=1e-6)
  np.testing.assert_allclose(b[0,0],b[1,1],atol=1e-6)
  self.assertTrue(np.isfinite(w).all());self.assertGreaterEqual(w.min(),0);np.testing.assert_allclose(w.sum(1),1,atol=1e-6)
 def test_upright_cycle_preserves_spine_head_and_leg_lengths(self):
  b,w,j,m,h=self.fixture();lengths=np.linalg.norm(b[:,1]-b[:,0],axis=1)
  for phase in np.linspace(0,1,25):
   matrices,t=g.pose(b,phase=phase,gait=1,height=h);v=t[1,1]-t[1,0]
   self.assertAlmostEqual(math.degrees(math.atan2(v[0],v[2])),2,places=4)
   np.testing.assert_allclose(np.linalg.norm(t[:,1]-t[:,0],axis=1),lengths,atol=1e-5)
   np.testing.assert_allclose(t[0,0],t[1,1],atol=1e-6)
   self.assertTrue(all(np.isfinite(r).all() and np.isfinite(p).all() for r,p in matrices))
 def test_ankle_stance_stays_planted_and_upper_body_fix_is_bounded(self):
  b,w,j,m,h=self.fixture()
  for phase in (0,.1,.25,.49):
   _,t=g.pose(b,phase=phase,gait=1,height=h);self.assertAlmostEqual(t[5,1,2],b[5,1,2],places=6)
  for gait in (0,1):
   _,t=g.pose(b,gait=gait,height=h)
   old=math.atan2(*(b[1,1]-b[1,0])[[0,2]]);new=math.atan2(*(t[1,1]-t[1,0])[[0,2]])
   self.assertLessEqual(abs(new-old),math.radians(20)+1e-6)

if __name__=='__main__':unittest.main()
