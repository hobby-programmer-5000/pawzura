"""Synthetic browser settings URLs; never touches a real browser/profile."""
import copy,json,os,tempfile,unittest
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtWidgets import QApplication
from pawzura.config import Settings,BROWSERS,defaults
from pawzura.policy import allowed_url,allowed_settings_page,BROWSER_SETTINGS_PAGES,site_rule
from pawzura.bridge import Bridge
from pawzura.ui import SettingsDialog


class InternalPagePolicyTests(unittest.TestCase):
    def test_registered_pages_and_settings_descendants_are_browser_specific(self):
        self.assertEqual(set(BROWSER_SETTINGS_PAGES),set(BROWSERS))
        for browser,addresses in BROWSER_SETTINGS_PAGES.items():
            for address in addresses:
                for url in (address,address+'?search=privacy#search',address+'#privacy'):
                    self.assertTrue(allowed_url(url,[],browser=browser,allow_settings=True),(browser,url))
                    self.assertFalse(allowed_url(url,[],browser=browser,allow_settings=False),(browser,url))
                if '://' in address:
                    self.assertTrue(allowed_settings_page(address+'/privacy',browser))
                    self.assertTrue(allowed_settings_page(address.upper()+'/privacy',browser))
        self.assertFalse(allowed_settings_page('about:preferences','chrome'))
        self.assertFalse(allowed_settings_page('chrome://settings','firefox'))
        self.assertFalse(allowed_settings_page('edge://settings','chrome'))

    def test_lookalikes_other_internal_pages_and_websites_remain_blocked(self):
        for browser in ('chrome','firefox'):
            for url in ('chrome://settings.evil','chrome://settings@evil','chrome://settings:123',
                        'chrome://flags','chrome://history','chrome://settings/../history',
                        'chrome://settings/%2f..%2fhistory','chrome://settings\\evil',
                        'about:preferences.evil','about:preferences/','about://preferences','about:config',
                        'https://settings','https://example.com','file:///settings','javascript:alert(1)',
                        ' chrome://settings','chrome://settings\n',None):
                self.assertFalse(allowed_settings_page(url,browser),(browser,url))
        self.assertTrue(allowed_url('https://example.com/course',[site_rule('example.com')],browser='chrome',allow_settings=True))
        self.assertFalse(allowed_url('https://unlisted.example',[],browser='chrome',allow_settings=True))
        self.assertFalse(allowed_url('chrome://settings',[],browser='chrome',allow_settings='true'))

    def test_existing_new_tab_and_extension_recovery_pages_are_preserved(self):
        for url in ('about:blank','chrome://newtab/','chrome://extensions/','about:addons'):
            self.assertTrue(allowed_url(url,[],browser='chrome',allow_settings=False))


class InternalPageSettingsTests(unittest.TestCase):
    def test_fresh_and_legacy_profiles_migrate_without_enabling_monitoring(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json';settings=Settings(path)
            self.assertTrue(all(entry['allow_settings_pages'] for entry in settings.snapshot()['browsers'].values()))
            legacy=defaults()
            for entry in legacy['browsers'].values():entry.pop('allow_settings_pages')
            legacy['browsers']['chrome']['allowed_sites']=['https://example.com']
            legacy['profiles']={'Work':{'allowed_apps':['work.exe'],'browsers':copy.deepcopy(legacy['browsers'])}}
            legacy['active_profile']='Work';path.write_text(json.dumps(legacy),encoding='utf-8');before=path.read_bytes()
            loaded=Settings(path);data=loaded.snapshot()
            self.assertEqual(path.read_bytes(),before)
            for entry in data['profiles']['Work']['browsers'].values():self.assertTrue(entry['allow_settings_pages'])
            self.assertEqual(data['browsers']['chrome']['allowed_sites'],['https://example.com'])
            self.assertFalse(data['guard_enabled']);self.assertTrue(data['preview_only']);self.assertFalse(data['browser_control_enabled'])
            loaded.save();self.assertTrue(Settings(path).snapshot()['browsers']['chrome']['allow_settings_pages'])

    def test_false_roundtrips_and_invalid_flags_cannot_replace_saved_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json';settings=Settings(path)
            rules=settings.snapshot()['browsers'];rules['chrome']['allow_settings_pages']=False;settings.save({'browsers':rules})
            self.assertFalse(Settings(path).snapshot()['browsers']['chrome']['allow_settings_pages']);before=path.read_bytes()
            for invalid in (None,1,'false',[]):
                rules['chrome']['allow_settings_pages']=invalid
                with self.assertRaises(ValueError):settings.save({'browsers':rules})
                self.assertEqual(path.read_bytes(),before)
            raw=json.loads(before);raw['profiles']['Work']=copy.deepcopy(raw['profiles']['Default'])
            raw['profiles']['Work']['browsers']['firefox']['allow_settings_pages']='false';path.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):Settings(path)


class InternalPageBridgeTests(unittest.TestCase):
    def test_status_observed_pause_invalidates_ready_close_before_resuming(self):
        with tempfile.TemporaryDirectory() as directory:
            settings=Settings(Path(directory)/'settings.json');settings.data.update(guard_enabled=True,browser_control_enabled=True,preview_only=False)
            settings.data['browsers']['chrome']['enabled']=True;bridge=Bridge(settings)
            data={'browser':'chrome','tabs':[{'id':1,'url':'https://unlisted.example'}]}
            bridge.evaluate(data);old=bridge.events.get_nowait()['ticket'];bridge.complete(old)
            settings.data['browser_control_enabled']=False;self.assertFalse(bridge.status({'browser':'chrome'})['enabled'])
            self.assertNotIn(old,bridge.tickets)
            settings.data['browser_control_enabled']=True;bridge.status({'browser':'chrome'});bridge.complete(old)
            self.assertFalse(bridge.evaluate(data)['decisions'][0]['close'])

    def test_toggle_invalidates_ready_close_and_keeps_normal_websites_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            settings=Settings(Path(directory)/'settings.json');settings.data.update(guard_enabled=True,browser_control_enabled=True,preview_only=False)
            settings.data['browsers']['chrome']['enabled']=True;bridge=Bridge(settings)
            data={'browser':'chrome','tabs':[{'id':1,'url':'chrome://settings/privacy','active':True}]}
            self.assertTrue(bridge.evaluate(data)['decisions'][0]['allowed']);self.assertTrue(bridge.events.empty())
            settings.data['browsers']['chrome']['allow_settings_pages']=False;bridge.evaluate(data)
            bridge.complete(bridge.events.get_nowait()['ticket']);self.assertTrue(bridge.evaluate(data)['decisions'][0]['close'])
            settings.data['browsers']['chrome']['allow_settings_pages']=True
            allowed=bridge.evaluate(data)['decisions'][0];self.assertTrue(allowed['allowed']);self.assertFalse(allowed['close'])
            settings.data['browsers']['chrome']['allow_settings_pages']=False
            self.assertFalse(bridge.evaluate(data)['decisions'][0]['close'])
            settings.data['browsers']['chrome']['allow_settings_pages']=True
            data['tabs'][0]['url']='https://unlisted.example';blocked=bridge.evaluate(data)['decisions'][0]
            self.assertFalse(blocked['allowed']);self.assertFalse(blocked['close'])
            settings.data['browser_control_enabled']=False;self.assertTrue(bridge.evaluate(data)['decisions'][0]['allowed'])


class InternalPageUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_browser_and_profile_switches_preserve_independent_flags_in_both_languages(self):
        for language in ('en','ko'):
            with tempfile.TemporaryDirectory() as directory:
                settings=Settings(Path(directory)/'settings.json');settings.data['language']=language;dialog=SettingsDialog(settings)
                try:
                    self.assertTrue(dialog.settings_pages_addresses.isReadOnly());self.assertEqual(dialog.settings_pages_addresses.text(),'chrome://settings')
                    self.assertTrue(dialog.allow_settings_pages.isChecked());dialog.allow_settings_pages.setChecked(False)
                    dialog.browser_select.setCurrentText('firefox');self.assertEqual(dialog.settings_pages_addresses.text(),'about:preferences')
                    self.assertTrue(dialog.allow_settings_pages.isChecked());dialog.sites.setPlainText('https://example.com')
                    with patch('pawzura.ui.QInputDialog.getText',return_value=('Work',True)):dialog.new_profile()
                    dialog.browser_select.setCurrentText('chrome');self.assertFalse(dialog.allow_settings_pages.isChecked())
                    dialog.allow_settings_pages.setChecked(True);dialog.profile_select.setCurrentText('Default')
                    self.assertFalse(dialog.allow_settings_pages.isChecked());dialog.save()
                    data=Settings(settings.path).snapshot()
                    self.assertFalse(data['profiles']['Default']['browsers']['chrome']['allow_settings_pages'])
                    self.assertTrue(data['profiles']['Work']['browsers']['chrome']['allow_settings_pages'])
                    self.assertEqual(data['browsers']['firefox']['allowed_sites'],['https://example.com'])
                    self.assertFalse(data['guard_enabled']);self.assertTrue(data['preview_only']);self.assertFalse(data['browser_control_enabled'])
                finally:
                    dialog.character_preview.timer.stop();dialog.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)

if __name__=='__main__':unittest.main()
