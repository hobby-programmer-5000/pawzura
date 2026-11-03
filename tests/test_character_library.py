import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent
from pawzura import artwork,motion_pack,character_library as lib
from pawzura.config import safe_character,Settings
from pawzura.library_ui import LibraryDialog
from pawzura.art_ui import ArtworkDialog
from scripts.check_distribution import check_distribution
from test_motion_pack import png,fixture

class CharacterLibraryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.patches=[patch('pawzura.artwork.asset_root',return_value=self.root/'artwork'),patch('pawzura.motion_pack.asset_root',return_value=self.root/'motion')]
  for p in self.patches:p.start()
  self.source=artwork.store_artwork(png('#aaccdd'));self.spec=safe_character({'kind':'artwork','art_id':self.source,'art_model':'sdxl','mouth_x':.5,'mouth_y':.4})
  self.digest=motion_pack.store_pack(fixture(self.source),self.source);self.animated={**self.spec,'animation_id':self.digest};self.dialogs=[]
 def tearDown(self):
  for d in self.dialogs:d.preview.timer.stop();d.deleteLater()
  QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
  for p in self.patches:p.stop()
  motion_pack._PACKS.clear();motion_pack._FRAMES.clear();artwork._IMAGES.clear();self.temp.cleanup()
 def test_named_versions_deduplicate_and_restore_without_models(self):
  first=lib.save({**self.spec,'prompt':'DO NOT STORE THIS','profiles':{'private':{}}},'Example 2D')
  second=lib.save(self.animated,'Example 3D');lib.save(self.animated)
  self.assertEqual(len(lib.entries()),2);self.assertEqual(lib.load(second['id'])['name'],'Example 3D')
  text=(lib.root()/(first['id']+lib.SUFFIX)).read_text();self.assertNotIn('DO NOT STORE',text);self.assertNotIn('profiles',text)
  for lang in ('en','ko'):
   with patch('pawzura.art_client.generate_artwork') as generate,patch('pawzura.motion_client.prepare_animation') as prepare:
    d=LibraryDialog(lang);self.dialogs.append(d);d.items.setCurrentRow(next(i for i,e in enumerate(d.rows) if e['id']==second['id']))
    self.assertTrue(d.use.isEnabled());chosen=[];d.chosen.connect(chosen.append);d.choose();self.assertEqual(chosen,[safe_character(self.animated)])
    generate.assert_not_called();prepare.assert_not_called()
 def test_missing_assets_and_tampered_metadata_are_rejected_before_apply(self):
  saved=lib.save(self.animated,'Example');d=LibraryDialog();self.dialogs.append(d)
  (self.root/'motion'/(self.digest+'.zip')).write_bytes(b'corrupt')
  chosen=[];d.chosen.connect(chosen.append);d.choose();self.assertEqual(chosen,[]);self.assertFalse(d.use.isEnabled())
  path=lib.root()/(saved['id']+lib.SUFFIX);raw=json.loads(path.read_text());raw['character']['art_id']='a'*64;path.write_text(json.dumps(raw))
  self.assertEqual(lib.entries(),[])
  for invalid in ('', 'x'*65, 'line\nbreak'):
   with self.assertRaises(ValueError):lib.save(self.spec,invalid)
 def test_older_metadata_can_gain_safe_defaults_without_losing_its_identity(self):
  entry=lib.save(self.spec,'Example');path=lib.root()/(entry['id']+lib.SUFFIX)
  raw=json.loads(path.read_text());raw['character'].pop('wings');raw['id']=lib.identity(raw['character'])
  path.unlink();path=lib.root()/(raw['id']+lib.SUFFIX);path.write_text(json.dumps(raw))
  loaded=lib.load(raw['id']);self.assertEqual(loaded['id'],raw['id']);self.assertEqual(loaded['character']['art_id'],self.source)
  self.assertIn('wings',loaded['character'])

 def test_art_dialog_auto_saves_before_apply_and_manual_name_is_kept(self):
  for lang in ('en','ko'):
   d=ArtworkDialog(lang);self.dialogs.append(d);d.started_at=d.stage_started_at=d.last_report_at=0
   d.succeeded(self.spec);self.assertEqual(len(lib.entries()),1);self.assertIsNotNone(d.result_spec)
   with patch('pawzura.library_ui.QInputDialog.getText',return_value=('Named example',True)):d.save_character_locally()
   self.assertEqual(lib.entries()[0]['name'],'Named example')
   lib.save(self.spec);self.assertEqual(lib.entries()[0]['name'],'Named example')
 def test_git_and_distribution_exclude_local_library_and_stage_data(self):
  for name in ('character-library/example.json','elsewhere/example.pawzura-character.json','motion/example.zip','motion-jobs/rig.npz','weights.ckpt','.character-storage.lock'):
   result=subprocess.run(['git','check-ignore','--no-index','-q',name],capture_output=True)
   self.assertEqual(result.returncode,0,name)
  lib.save(self.spec,'Example')
  with self.assertRaises(ValueError):check_distribution(self.root)
  export=self.root/'export';export.mkdir();(export/'renamed.json').write_text(json.dumps({'format':lib.FORMAT,'character':self.spec}))
  with self.assertRaises(ValueError):check_distribution(export)
  lock_export=self.root/'lock-export';lock_export.mkdir();(lock_export/'.character-storage.lock').write_text('synthetic lock')
  with self.assertRaises(ValueError):check_distribution(lock_export)

if __name__=='__main__':unittest.main()
