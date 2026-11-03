"""Optional Windows mixed-DPI probe; only a test-owned vector pet, no guardian."""
import argparse
import ctypes
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'.cache/pet-dpi-probe.json')
    args=parser.parse_args()
    if sys.platform!='win32':
        print('NOT RUN: requires Windows and two monitors with different DPI');return 2
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from pawzura.config import default_character
    from pawzura.pet import Pet
    app=QApplication([]);app.setQuitOnLastWindowClosed(False)
    screens=sorted(app.screens(),key=lambda s:(s.geometry().x(),s.geometry().y()))
    pairs=[(i,(i+1)%len(screens)) for i in range(len(screens)) if screens[i].devicePixelRatio()!=screens[(i+1)%len(screens)].devicePixelRatio()]
    if not pairs:
        print('NOT RUN: needs at least two different monitor scale factors');return 2
    first,second=pairs[0];pet=Pet(default_character());pet.show()
    cases=[(first,second,1),(second,first,-1)]
    rows=[];case=0;started=None;outcome={};errors=[]
    def position():
        nonlocal started
        source,target,direction=cases[case];screen=screens[source];area=screen.availableGeometry()
        pet.cancel_bite();pet.set_walk_direction('right' if direction>0 else 'left');pet.use_screen(screen)
        pet.px=float(area.right()-72-14 if direction>0 else area.left()-72+14)
        pet.py=float(max(area.top(),area.bottom()-146+1));pet.move(round(pet.px),round(pet.py))
        pet.next_idle=pet.next_pause=time.monotonic()+1000;pet.hovered=False;started=time.monotonic()
    def finish():
        timer.stop();pet.timer.stop()
        for n,(_,target,_) in enumerate(cases):
            entries=[r for r in rows if r['case']==n]
            if not any(r['screen']==target for r in entries):errors.append(f'case{n}: target screen not reached')
        if any(r['size']!=[144,146] or not r['on_floor'] for r in rows):errors.append('logical size or work-area floor changed')
        outcome.update(status='FAIL' if errors else 'PASS',errors=errors,samples=rows)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(outcome,indent=2),encoding='utf-8')
        print(json.dumps({'status':outcome['status'],'samples':len(rows),'errors':errors,'output':str(args.output)}),flush=True)
        pet.dispose();app.quit()
    def sample():
        nonlocal case
        if started is None:position();return
        age=time.monotonic()-started
        if age>.15:
            screen=app.screenAt(pet.geometry().center())
            area=screen.availableGeometry() if screen else None
            rows.append({'case':case,'seconds':round(age,3),'screen':screens.index(screen) if screen in screens else None,
                         'dpr':pet.devicePixelRatioF(),'size':[pet.width(),pet.height()],
                         'on_floor':area is not None and abs(pet.py-max(area.top(),area.bottom()-146+1))<1})
        if age>2.5:
            case+=1
            if case==len(cases):finish()
            else:position()
    timer=QTimer();timer.timeout.connect(sample);timer.start(20)
    app.exec()
    return 0 if outcome.get('status')=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
