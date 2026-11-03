import io
import json
import hashlib
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from PySide6.QtCore import QByteArray,QBuffer,QIODevice,QEvent,QPointF,QRect
from PySide6.QtGui import QImage,QColor,QPainter
from PySide6.QtWidgets import QApplication
from pawzura import artwork,motion_pack
from pawzura.config import safe_character
from pawzura.pet import Pet,draw_character


def png(color,side=256):
    image=QImage(side,side,QImage.Format.Format_ARGB32);image.fill(QColor(color))
    data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buffer,'PNG')
    return bytes(data)


def fixture(source_id,change=None,extra=None):
    manifest={'version':1,'source_art_id':source_id,'backend':'triposr-pose-v1','size':256,'fps':30,'clips':{}}
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for clip in motion_pack.CLIPS:
            manifest['clips'][clip]=[]
            for i in range(4):
                name=f'frames/{clip}-{i:03}.png';data=png('#119944' if 'left' in clip else '#dd3355')
                archive.writestr(name,data)
                manifest['clips'][clip].append({'file':name,'sha256':hashlib.sha256(data).hexdigest(),
                                                 'mouth':[.2 if 'left' in clip else .8,.3]})
        if change:change(manifest)
        archive.writestr('manifest.json',json.dumps(manifest))
        if extra:archive.writestr(*extra)
    return output.getvalue()


class MotionPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.asset_patch=patch('pawzura.artwork.asset_root',return_value=self.root/'art');self.asset_patch.start()
        self.motion_patch=patch('pawzura.motion_pack.asset_root',return_value=self.root/'motion');self.motion_patch.start()
        self.source=artwork.store_artwork(png('#ffaa44'))
        self.data=fixture(self.source);self.digest=motion_pack.store_pack(self.data,self.source)
        self.spec=safe_character({'kind':'artwork','art_id':self.source,'art_model':'sdxl','mouth_x':.5,'mouth_y':.4,'animation_id':self.digest})
        self.pets=[]

    def tearDown(self):
        for pet in self.pets:pet.dispose()
        QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        self.asset_patch.stop();self.motion_patch.stop();motion_pack._PACKS.clear();motion_pack._FRAMES.clear();artwork._IMAGES.clear();self.temp.cleanup()

    def test_pack_identity_paths_extra_code_and_nonfinite_anchors_are_rejected(self):
        for data,source in [(self.data,'a'*64),(fixture(self.source,lambda m:m['clips']['walk_left'][0].update(mouth=[float('nan'),.5])),self.source),
                            (fixture(self.source,lambda m:m['clips']['walk_left'][0].update(file='../outside.png')),self.source),
                            (fixture(self.source,extra=('generated.py','raise RuntimeError()')),self.source),
                            (fixture(self.source,lambda m:m['clips']['walk_left'][0].update(sha256='0'*64)),self.source)]:
            with self.assertRaises(ValueError):motion_pack.validate_pack(data,source)
        self.assertIsNone(motion_pack.load_pack(self.digest,'b'*64))

    def test_source_bound_pack_persists_and_draws_left_view_without_bitmap_mirroring(self):
        self.assertEqual(self.spec['animation_id'],self.digest)
        self.assertNotIn('animation_id',safe_character({**self.spec,'animation_id':'../untrusted'}))
        image=QImage(144,144,QImage.Format.Format_ARGB32);image.fill(0);p=QPainter(image)
        draw_character(p,self.spec,1,facing=-1);p.end()
        self.assertEqual(image.pixelColor(70,70).name(),'#119944')
        frame=motion_pack.frame(self.spec,'bite_left',.72)
        self.assertEqual(frame[1],[.2,.3])
        path=self.root/'motion'/(self.digest+'.zip');path.write_bytes(b'corrupt')
        motion_pack._PACKS.clear()
        self.assertIsNone(motion_pack.load_pack(self.digest,self.source))

    def test_turns_block_travel_and_stop_returns_front_before_reversal(self):
        player=motion_pack.MotionPlayer()
        self.assertEqual(player.update(True,1,'walk',0),('turn_right',0,False))
        self.assertFalse(player.update(True,1,'walk',.1)[2])
        self.assertEqual(player.update(True,1,'walk',.3)[0],'walk_right')
        self.assertTrue(player.update(True,1,'walk',.4)[2])
        self.assertEqual(player.update(False,1,'idle_front',.5)[0],'return_right')
        self.assertEqual(player.update(False,1,'idle_front',.8)[0],'idle_front')
        self.assertEqual(player.update(True,-1,'walk',.9)[0],'turn_left')
        self.assertEqual(player.update(True,-1,'walk',1.2)[0],'walk_left')

    def test_bite_uses_visible_clip_anchor_and_cancellation_never_replays_contact(self):
        pet=Pet(self.spec);pet.timer.stop();self.pets.append(pet);called=[]
        target=QPointF(pet.px+220,pet.py-90)
        with patch('pawzura.pet.time.monotonic',return_value=100):self.assertTrue(pet.bite(target,lambda:called.append(1)))
        with patch('pawzura.pet.time.monotonic',return_value=100.75):pet.tick()
        self.assertEqual(called,[1]);self.assertAlmostEqual(pet.px+.8*144,target.x());self.assertAlmostEqual(pet.py+.3*144,target.y())
        pet.cancel_bite()
        with patch('pawzura.pet.time.monotonic',return_value=102):pet.tick()
        self.assertEqual(called,[1]);self.assertIsNone(pet.action)

    def test_missing_pack_falls_back_and_recovery_can_reload_the_same_id(self):
        path=self.root/'motion'/(self.digest+'.zip');path.unlink();motion_pack._PACKS.clear()
        pet=Pet(self.spec);pet.timer.stop();self.pets.append(pet)
        self.assertFalse(pet.has_motion())
        motion_pack.store_pack(self.data,self.source)
        pet.cancel_bite()
        self.assertTrue(pet.has_motion())

    def test_left_walk_wraps_to_previous_negative_origin_work_area_in_logical_pixels(self):
        from types import SimpleNamespace
        left=SimpleNamespace(availableGeometry=lambda:QRect(-1280,-120,1280,984))
        right=SimpleNamespace(availableGeometry=lambda:QRect(0,0,1920,1040))
        pet=Pet(self.spec);pet.timer.stop();self.pets.append(pet);pet.show()
        pet.direction=-1;pet.px=-72;pet.py=894;pet.last_tick=100;pet.next_idle=200;pet.next_pause=200
        pet.has_motion()
        pet.motion_player.update(True,-1,'walk',99)
        with patch.object(pet,'use_screen') as use_screen,patch.object(pet,'screens',return_value=[left,right]),patch('pawzura.pet.QApplication.screenAt',return_value=right),patch('pawzura.pet.time.monotonic',return_value=100.1):
            pet.tick()
        use_screen.assert_called_once_with(left)
        self.assertEqual(pet.px,left.availableGeometry().right()-72)
        self.assertEqual(pet.py,left.availableGeometry().bottom()-pet.height()+1)


if __name__=='__main__':unittest.main()
