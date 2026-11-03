"""Deletion tests use disposable synthetic storage, never the personal library."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QEvent,QTimer,QLockFile
from pawzura import artwork,motion_pack,character_library as lib,library_delete as deletion
from pawzura.config import safe_character,Settings,default_character
from pawzura.library_ui import LibraryDialog,confirm_delete,TEXT
from test_motion_pack import png,fixture


class LibraryDeleteTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.patches=[patch('pawzura.artwork.asset_root',return_value=self.root/'artwork'),patch('pawzura.motion_pack.asset_root',return_value=self.root/'motion')]
  for p in self.patches:p.start()
  self.art=artwork.store_artwork(png('#8899aa'));self.spec=safe_character({'kind':'artwork','art_id':self.art,'art_model':'sdxl','mouth_x':.5,'mouth_y':.4})
  self.motion=motion_pack.store_pack(fixture(self.art),self.art);self.animated=safe_character({**self.spec,'animation_id':self.motion})
  self.source=self.root/'artwork'/(self.art+'.png');self.clip=self.root/'motion'/(self.motion+'.zip');self.dialogs=[]
 def tearDown(self):
  for d in self.dialogs:d.preview.timer.stop();d.deleteLater()
  QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
  for p in self.patches:p.stop()
  artwork._IMAGES.clear();motion_pack._PACKS.clear();motion_pack._FRAMES.clear();self.temp.cleanup()
 def cache(self,status='ready'):
  folder=self.root/'motion-jobs'/(self.art+'-staged-'+'a'*16);folder.mkdir(parents=True)
  (folder/'state.json').write_text(json.dumps({'status':status}));(folder/'rig.npz').write_bytes(b'synthetic')
  return folder
 def entrypath(self,entry):return lib.root()/(entry['id']+lib.SUFFIX)
 def test_last_reference_removes_assets_known_cache_and_entry_only(self):
  entry=lib.save(self.animated,'Synthetic');cache=self.cache();other=self.root/'keep.txt';other.write_text('keep')
  plan=deletion.plan_delete(entry['id']);result=deletion.delete(plan)
  self.assertEqual(result['removed_bytes'],plan['bytes']);self.assertEqual(result['removed_files'],plan['files'])
  for path in (self.source,self.clip,cache,self.entrypath(entry)):self.assertFalse(path.exists(),str(path))
  self.assertEqual(other.read_text(),'keep')
 def test_entry_only_keeps_every_asset(self):
  entry=lib.save(self.animated,'Synthetic');cache=self.cache()
  result=deletion.delete(deletion.plan_delete(entry['id'],include_files=False))
  self.assertTrue(self.source.exists() and self.clip.exists() and cache.exists());self.assertEqual(result['removed_files'],1)
 def test_other_version_keeps_source_and_cache_but_unused_clip_is_removed(self):
  entry=lib.save(self.animated,'Motion');other=lib.save(self.spec,'Drawing');cache=self.cache()
  deletion.delete(deletion.plan_delete(entry['id']))
  self.assertTrue(self.source.exists() and cache.exists());self.assertFalse(self.clip.exists());self.assertEqual(lib.load(other['id'])['character'],self.spec)
 def test_history_and_active_or_pending_protect_files(self):
  entry=lib.save(self.animated,'Synthetic');cache=self.cache()
  for refs in ({'active':[self.animated]}, {'active':[self.spec,self.animated]}):
   with self.assertRaisesRegex(deletion.DeleteError,'delete_active'):deletion.plan_delete(entry['id'],reference_provider=lambda:refs)
  settings=Settings(self.root/'settings.json');settings.save({'character_history':[self.animated]})
  deletion.delete(deletion.plan_delete(entry['id']))
  self.assertTrue(self.source.exists() and self.clip.exists() and cache.exists())
 def test_shared_motion_and_changed_pending_reference_are_protected(self):
  entry=lib.save(self.animated,'Motion');other=lib.save({**self.animated,'mouth_x':.6},'Alternate mouth')
  refs={'active':[],'history':[]};provider=lambda:refs
  plan=deletion.plan_delete(entry['id'],reference_provider=provider)
  refs['history']=[self.animated]
  with self.assertRaisesRegex(deletion.DeleteError,'delete_changed'):deletion.delete(plan,reference_provider=provider)
  deletion.delete(deletion.plan_delete(entry['id']))
  self.assertTrue(self.source.exists() and self.clip.exists());self.assertEqual(lib.load(other['id'])['character']['mouth_x'],.6)
 def test_disk_active_setting_blocks_and_invalid_setting_fails_open(self):
  entry=lib.save(self.spec,'Synthetic');settings=Settings(self.root/'settings.json');settings.save({'character':self.spec})
  with self.assertRaisesRegex(deletion.DeleteError,'delete_active'):deletion.plan_delete(entry['id'])
  settings.path.write_text('broken')
  with self.assertRaisesRegex(deletion.DeleteError,'delete_references'):deletion.plan_delete(entry['id'])
  self.assertTrue(self.source.exists() and self.entrypath(entry).exists())
 def test_changed_references_file_or_label_rejects_stale_confirmation(self):
  entry=lib.save(self.animated,'Synthetic');plan=deletion.plan_delete(entry['id'])
  other=lib.save(self.spec,'New reference')
  with self.assertRaisesRegex(deletion.DeleteError,'delete_changed'):deletion.delete(plan)
  plan=deletion.plan_delete(entry['id']);lib.save(self.animated,'Renamed')
  with self.assertRaisesRegex(deletion.DeleteError,'delete_changed'):deletion.delete(plan)
  plan=deletion.plan_delete(entry['id']);self.clip.write_bytes(b'changed')
  with self.assertRaisesRegex(deletion.DeleteError,'delete_changed'):deletion.delete(plan)
  self.assertTrue(self.source.exists() and self.clip.exists() and self.entrypath(other).exists())
 def test_unknown_preparing_or_bad_metadata_keeps_assets(self):
  entry=lib.save(self.animated,'Synthetic');cache=self.cache('preparing')
  plan=deletion.plan_delete(entry['id']);self.assertTrue(plan['cleanup_limited'])
  deletion.delete(plan);self.assertTrue(self.source.exists() and self.clip.exists() and cache.exists())
  entry=lib.save(self.animated,'Again');(cache/'state.json').write_text('{"status":"ready"}')
  (lib.root()/('f'*64+lib.SUFFIX)).write_text('broken')
  plan=deletion.plan_delete(entry['id']);self.assertTrue(plan['cleanup_limited']);deletion.delete(plan)
  self.assertTrue(self.source.exists() and self.clip.exists() and cache.exists())
 def test_unknown_cache_file_and_external_symlink_are_kept(self):
  entry=lib.save(self.animated,'Synthetic');cache=self.cache();unknown=cache/'unknown.dat';unknown.write_bytes(b'keep')
  deletion.delete(deletion.plan_delete(entry['id']));self.assertTrue(unknown.exists())
  # A symlink, when the OS permits creating it, must never delete its target.
  external=self.root/'outside';external.mkdir();target=external/'keep';target.write_bytes(b'keep')
  link=lib.root()/'link'
  try:link.symlink_to(external,target_is_directory=True)
  except OSError:return  # Symlink privilege is optional; reparse handling has a separate deterministic test.
  with self.assertRaisesRegex(deletion.DeleteError,'delete_unsafe'):deletion._file(link/'keep',lib.root())
  self.assertEqual(target.read_bytes(),b'keep');link.unlink()
 def test_reparse_attribute_is_rejected(self):
  from types import SimpleNamespace
  with patch.object(Path,'lstat',return_value=SimpleNamespace(st_mode=0o100644,st_file_attributes=0x400)):
   with self.assertRaisesRegex(deletion.DeleteError,'delete_unsafe'):deletion._regular(self.source,self.root)
 def test_partial_failure_keeps_entry_for_retry_and_reports_bytes(self):
  entry=lib.save(self.animated,'Synthetic');plan=deletion.plan_delete(entry['id']);unlink=Path.unlink
  def fail_source(path,*args,**kwargs):
   if path==self.source:raise PermissionError('synthetic locked file')
   return unlink(path,*args,**kwargs)
  with patch.object(Path,'unlink',fail_source):
   with self.assertRaisesRegex(deletion.DeleteError,'delete_partial') as caught:deletion.delete(plan)
  self.assertGreater(caught.exception.removed_bytes,0);self.assertTrue(self.entrypath(entry).exists());self.assertTrue(self.source.exists())
  deletion.delete(deletion.plan_delete(entry['id']));self.assertFalse(self.entrypath(entry).exists())
 def test_locked_store_and_busy_provider_do_not_delete(self):
  entry=lib.save(self.spec,'Synthetic');lock=QLockFile(str(self.root/'.character-storage.lock'));self.assertTrue(lock.tryLock(0))
  try:
   with self.assertRaises(OSError):deletion.plan_delete(entry['id'])
  finally:lock.unlock()
  with self.assertRaisesRegex(deletion.DeleteError,'delete_busy'):deletion.plan_delete(entry['id'],reference_provider=lambda:{'busy':True})
  self.assertTrue(self.source.exists())
 def test_deleted_artwork_cannot_be_saved_as_new_current_character(self):
  settings=Settings(self.root/'settings.json');entry=lib.save(self.spec,'Synthetic');deletion.delete(deletion.plan_delete(entry['id']))
  with self.assertRaises((OSError,ValueError)):settings.save({'character':self.spec})
  self.assertEqual(settings.snapshot()['character'],default_character())
 def test_ui_cancel_delete_active_and_missing_assets_in_both_languages(self):
  for lang in ('en','ko'):
   entry=lib.save(self.spec,'Synthetic');d=LibraryDialog(lang,current_spec=self.spec);self.dialogs.append(d)
   self.assertFalse(d.remove.isEnabled());d.initial_spec=None;d.select(0);self.assertTrue(d.remove.isEnabled())
   with patch('pawzura.library_ui.confirm_delete',return_value=False):d.delete_selected()
   self.assertTrue(self.entrypath(entry).exists());self.source.unlink(missing_ok=True);d.select(0)
   self.assertFalse(d.use.isEnabled());self.assertTrue(d.remove.isEnabled())
   with patch('pawzura.library_ui.confirm_delete',return_value=True):d.delete_selected()
   self.assertEqual(d.rows,[]);self.assertFalse(d.remove.isEnabled());self.assertFalse(d.use.isEnabled())
   self.art=artwork.store_artwork(png('#8899aa'))
 def test_real_confirmation_defaults_to_cancel_and_uses_plain_text(self):
  entry=lib.save(self.spec,'<b>Synthetic</b>');plan=deletion.plan_delete(entry['id'])
  for lang in ('en','ko'):
   observed=[]
   def cancel():
    box=QApplication.activeModalWidget();observed.append(box.defaultButton()==box.button(QMessageBox.StandardButton.No));box.reject()
   QTimer.singleShot(0,cancel);self.assertFalse(confirm_delete(None,TEXT[lang],plan));self.assertEqual(observed,[True])
  self.assertTrue(self.entrypath(entry).exists())

if __name__=='__main__':unittest.main()
