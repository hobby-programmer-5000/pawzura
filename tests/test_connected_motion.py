import json
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from pawzura import art_client, artwork, motion_client, motion_pack, model_jobs
from pawzura.characters import GenerationError
from pawzura.art_ui import ArtworkDialog, MotionWorker
from test_motion_pack import png, fixture


class ConnectedMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.patches=[patch('pawzura.artwork.asset_root',return_value=self.root/'art'),
                      patch('pawzura.motion_pack.asset_root',return_value=self.root/'motion')]
        for p in self.patches:p.start()
        self.source=artwork.store_artwork(png('#bd9922'))
        self.spec={'kind':'artwork','art_id':self.source,'mouth_x':.5,'mouth_y':.4,'art_model':'sdxl'}
        self.runtime=self.root/'runtime';p=art_client.runtime_python(self.runtime);p.parent.mkdir(parents=True);p.touch()
        (self.runtime/'uv.exe').touch(); self.cache=self.root/'jobs'
        self.calls=[]

    def tearDown(self):
        for p in self.patches:p.stop()
        motion_pack._PACKS.clear();motion_pack._FRAMES.clear();artwork._IMAGES.clear()
        self.temp.cleanup()

    def fake_worker(self,stage,job,root,payload,progress,cancel):
        self.calls.append(stage)
        if stage=='prepare':return {'stage':stage}
        for name in motion_client.STAGE_FILES[stage]:
            (job/name).write_bytes(fixture(self.source) if name=='motion.zip' else b'accepted synthetic stage')
        return {'stage':stage,'files':[{'name':n,'sha256':__import__('hashlib').sha256((job/n).read_bytes()).hexdigest(),'bytes':(job/n).stat().st_size} for n in motion_client.STAGE_FILES[stage]]}

    def prepare(self,spec=None,cancel=None,worker=None):
        with patch('pawzura.motion_client._worker',side_effect=worker or self.fake_worker), patch('pawzura.art_client._run',return_value=b'{}'):
            return motion_client.prepare_animation(spec or self.spec,root=self.runtime,cache=self.cache,cancel=cancel)

    def test_cache_checks_actual_bytes_and_mouth_invalidates_downstream_only(self):
        result=self.prepare();self.assertIn('animation_id',result)
        self.assertEqual(self.calls,['prepare','reconstruct','rig','bake'])
        self.calls.clear();self.assertEqual(self.prepare()['animation_id'],result['animation_id']);self.assertEqual(self.calls,[])
        self.prepare({**self.spec,'mouth_x':.6});self.assertEqual(self.calls,['rig','bake'])
        self.calls.clear();job=next(self.cache.iterdir());(job/'surface.npz').write_bytes(b'corrupt')
        self.prepare({**self.spec,'mouth_x':.6});self.assertEqual(self.calls[0],'reconstruct')
        state=json.loads((job/'state.json').read_text());self.assertEqual(state['status'],'ready')

    def test_motion_only_code_change_reuses_reconstruction_and_rig(self):
        import shutil
        source=self.root/'source';source.mkdir()
        for name in ('three_d.py','motion_geometry.py','motion_bake.py','motion_catalog.json','triposr-sources.json','requirements.txt','runner.py','motion_cache_legacy.json','catalog.json'):
            shutil.copy2(art_client.source_dir()/name,source/name)
        with patch('pawzura.art_client.source_dir',return_value=source):
            self.prepare();self.calls.clear();before=motion_client.stage_signatures()
            file=source/'motion_geometry.py';text=file.read_text();self.assertIn('math.radians(2)-rest_lean',text)
            file.write_text(text.replace('math.radians(2)-rest_lean','math.radians(3)-rest_lean'))
            after=motion_client.stage_signatures()
            self.assertEqual(before['reconstruct'],after['reconstruct']);self.assertEqual(before['rig'],after['rig'])
            self.assertNotEqual(before['bake'],after['bake'])
            self.prepare();self.assertEqual(self.calls,['bake'])
            self.calls.clear();catalog=json.loads((source/'catalog.json').read_text());catalog['pose']['revision']='0'*40
            (source/'catalog.json').write_text(json.dumps(catalog));changed=motion_client.stage_signatures()
            self.assertEqual(changed['reconstruct'],after['reconstruct']);self.assertNotEqual(changed['rig'],after['rig'])
            self.prepare();self.assertEqual(self.calls,['prepare','rig','bake'])

    def test_pinned_legacy_reconstruction_is_adopted_without_gpu_worker(self):
        import hashlib
        legacy=json.loads((art_client.source_dir()/'motion_cache_legacy.json').read_text())
        revision=next(iter(legacy['backends']));job=self.cache/(self.source+'-'+revision[:16]);job.mkdir(parents=True)
        files=self.fake_worker('reconstruct',job,self.runtime,{},lambda e:None,threading.Event())['files']
        record={'input':hashlib.sha256(json.dumps([self.source,revision,[]]).encode()).hexdigest(),'files':files}
        (job/'state.json').write_text(json.dumps({'revision':revision,'stages':{'reconstruct':record}}))
        self.calls.clear();self.prepare();self.assertNotIn('reconstruct',self.calls);self.assertIn('rig',self.calls)

    def test_cancellation_retains_verified_stage_and_never_returns_candidate(self):
        cancel=threading.Event()
        def worker(*args):
            result=self.fake_worker(*args)
            if args[0]=='rig':cancel.set()
            return result
        with self.assertRaisesRegex(GenerationError,'art_cancelled'):self.prepare(cancel=cancel,worker=worker)
        job=next(self.cache.iterdir());state=json.loads((job/'state.json').read_text())
        self.assertEqual(state['status'],'cancelled');self.assertEqual(set(state['stages']),{'reconstruct'})
        self.assertFalse((job/'motion.zip').exists())
        self.calls.clear();self.prepare();self.assertEqual(self.calls,['rig','bake'])

    def test_bad_stage_records_and_second_job_are_rejected(self):
        job=self.root/'outputs';job.mkdir()
        for records in ([],[{'name':'../outside','bytes':3,'sha256':'a'*64}],None):
            self.assertFalse(motion_client._valid_outputs(job,'bake',records))
        errors=[]
        def competing():
            try:
                with model_jobs.model_job(): pass
            except GenerationError as e:errors.append(str(e))
        with model_jobs.model_job():
            t=threading.Thread(target=competing);t.start();t.join(2)
        self.assertEqual(errors,['art_model_busy'])

    def test_dialog_rejects_late_cancelled_wrong_source_and_can_restore_original(self):
        result=self.prepare()
        for language in ('en','ko'):
            d=ArtworkDialog(language,initial_spec=self.spec);w=MotionWorker(self.spec,d);d.worker=w
            w.cancel_event.set();d.motion_succeeded(result);self.assertNotIn('animation_id',d.result_spec)
            w.cancel_event.clear();d.motion_succeeded({**result,'art_id':'a'*64});self.assertNotIn('animation_id',d.result_spec)
            d.motion_succeeded(result);self.assertEqual(d.preview.spec['animation_id'],result['animation_id'])
            d.worker=None;d.controls();self.assertFalse(d.motion_button.isEnabled());self.assertTrue(d.motion_view.isEnabled())
            chosen=[];d.chosen.connect(chosen.append);self.assertEqual(chosen,[])
            d.restore_original();self.assertNotIn('animation_id',d.result_spec);self.assertEqual(d.result_spec['art_id'],self.source)
            d.preview.timer.stop();d.deleteLater()

    @unittest.skipUnless(os.name=='nt','Windows process containment')
    def test_cancellation_reaps_owned_descendant_before_releasing_model_slot(self):
        pidfile=self.root/'child.pid';cancel=threading.Event()
        script="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path(sys.argv[1]).write_text(str(p.pid));print('PAWZURA_PROGRESS {\\\"stage\\\":\\\"motion_rigging\\\"}',file=sys.stderr,flush=True);time.sleep(30)"
        # Keep protocol JSON literal; no shell is involved.
        script=script.replace('\\\"','"')
        start=time.monotonic()
        with self.assertRaisesRegex(GenerationError,'art_cancelled'):
            art_client._run([sys.executable,'-c',script,str(pidfile)],progress=lambda e:cancel.set(),cancel=cancel,contain=True,timeout=5)
        self.assertLess(time.monotonic()-start,4)
        import ctypes
        api=ctypes.WinDLL('kernel32',use_last_error=True);api.OpenProcess.restype=ctypes.c_void_p
        handle=api.OpenProcess(0x100000,False,int(pidfile.read_text()))
        if handle:
            api.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32];api.CloseHandle.argtypes=[ctypes.c_void_p]
            try:self.assertEqual(api.WaitForSingleObject(handle,0),0)
            finally:api.CloseHandle(handle)
        self.assertEqual(json.loads(art_client._run([sys.executable,'-c','print("{}")'],contain=True,timeout=5)),{})


if __name__=='__main__':unittest.main()
