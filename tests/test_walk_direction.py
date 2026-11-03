import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF,QEvent
from pawzura.config import Settings,default_character
from pawzura.ui import SettingsDialog
from pawzura.pet import Pet
from pawzura.app import Companion

class WalkDirectionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'settings.json';self.settings=Settings(self.path);self.widgets=[];self.pets=[]
 def tearDown(self):
  for w in self.widgets:w.connection_timer.stop();w.character_preview.timer.stop();w.deleteLater()
  for p in self.pets:p.dispose()
  QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.temp.cleanup()
 def pet(self,*args,**kwargs):
  p=Pet(*args,**kwargs);p.timer.stop();self.pets.append(p);return p
 def test_migration_invalid_input_and_persisted_preference(self):
  self.assertEqual(self.settings.snapshot()['walk_direction'],'right')
  saved=self.settings.snapshot();saved.pop('walk_direction');self.path.write_text(json.dumps(saved))
  self.assertEqual(Settings(self.path).snapshot()['walk_direction'],'right')
  for invalid in ('up',None,True,[],{}):
   with self.assertRaises(ValueError):self.settings.save({'walk_direction':invalid})
  self.settings.save({'walk_direction':'left'});self.assertEqual(Settings(self.path).snapshot()['walk_direction'],'left')
  saved['walk_direction']='invalid';self.path.write_text(json.dumps(saved));self.assertEqual(Settings(self.path).snapshot()['walk_direction'],'right')
 def test_localized_selection_applies_only_on_save_and_preserves_guard_profiles(self):
  for lang in ('en','ko'):
   self.settings.save({'language':lang,'walk_direction':'right'});before=self.settings.snapshot()
   d=SettingsDialog(self.settings);self.widgets.append(d);d.walk_direction.setCurrentIndex(d.walk_direction.findData('left'))
   self.assertEqual(d.character_preview.facing,-1)
   self.assertEqual(self.settings.snapshot()['walk_direction'],'right')
   p=self.pet(default_character());fake=SimpleNamespace(settings=self.settings,pet=p,bridge=Mock(),tray=Mock(),make_icon=Mock(),refresh_menu=Mock(),dialog=None,observed={},previewed=set())
   d.applied.connect(lambda:Companion.apply(fake));d.save()
   self.assertEqual((p.walk_direction,p.direction),(-1,-1));self.assertEqual(Settings(self.path).snapshot()['walk_direction'],'left')
   for key in ('profiles','allowed_apps','guard_enabled','browser_control_enabled','preview_only'):self.assertEqual(self.settings.snapshot()[key],before[key])
 def test_walk_left_moves_left_and_bite_return_and_cancellation_restore_preference(self):
  p=self.pet(default_character(),walk_direction='left');p.show();p.last_tick=100;p.next_idle=200
  start=p.px
  with patch('pawzura.pet.time.monotonic',return_value=100.1):p.tick()
  self.assertLess(p.px,start);called=[]
  with patch('pawzura.pet.time.monotonic',return_value=101):p.bite(QPointF(p.px+300,p.py-100),lambda:called.append(1))
  self.assertEqual((p.direction,p.walk_direction),(1,-1))
  with patch('pawzura.pet.time.monotonic',return_value=101.8):p.tick()
  with patch('pawzura.pet.time.monotonic',return_value=103):p.tick()
  self.assertEqual(called,[1]);self.assertEqual(p.direction,-1)
  p.bite(QPointF(p.px+300,p.py-100),lambda:called.append(2));p.cancel_bite();self.assertEqual(p.direction,-1)
  p.set_walk_direction('right');p.home();self.assertEqual(p.direction,1)
 def test_native_pet_recovery_uses_saved_direction(self):
  self.settings.save({'walk_direction':'left'})
  old=self.pet(default_character());self.pets.remove(old)
  fake=SimpleNamespace(settings=self.settings,pet=old,bridge=Mock(),show_settings=Mock(),refresh_menu=Mock(),dialog=None)
  Companion.recover_pet(fake);fake.pet.timer.stop();self.pets.append(fake.pet)
  self.assertEqual((fake.pet.direction,fake.pet.walk_direction),(-1,-1))

if __name__=='__main__':unittest.main()
