"""Local saved character selection; no inference or arbitrary file paths."""
from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QLabel,QPushButton,QInputDialog,QCheckBox,QMessageBox
from . import character_library as library
from .pet import CharacterPreview

TEXT={
 'en':{'save':'Save character…','open':'Saved characters…','title':'Saved characters · local only','name':'Character name (1–64 characters)','saved':'Character saved locally. Saved characters can restore it without generation.','failed':'Cannot save this character. Check local disk space and the artwork/motion files. The current character is retained.','auto_saved':'Saved automatically in Saved characters. You can load this version without generating again.','auto_failed':'Automatic library save failed. Use Save character to retry; the generated files are retained.','help':'Approved artwork and prepared motion are saved as separate versions automatically. Choose a version to preview, then Use this character → Save settings. No model is needed to load it. Local stage caches are retained for re-preparation.','empty':'No saved characters yet. Generate artwork or save the current character.','missing':'The source image or motion pack is missing/corrupt. Restore its local backup; this entry was not applied.','use':'Use this character','close':'Close'},
 'ko':{'save':'캐릭터 저장…','open':'저장한 캐릭터…','title':'저장한 캐릭터 · 로컬 전용','name':'캐릭터 이름 (1–64자)','saved':'캐릭터를 로컬에 저장했습니다. 저장한 캐릭터에서 생성 없이 다시 불러올 수 있습니다.','failed':'저장하지 못했습니다. 디스크 여유와 로컬 그림·모션 파일을 확인하세요. 현재 캐릭터는 유지합니다.','auto_saved':'저장한 캐릭터에 자동 보관했습니다. 다시 생성하지 않고 이 버전을 불러올 수 있습니다.','auto_failed':'보관함 자동 저장에 실패했습니다. 생성 파일은 유지하므로 캐릭터 저장으로 재시도하세요.','help':'승인한 그림과 준비한 모션을 각각 별도 버전으로 자동 보관합니다. 선택해 미리 본 뒤 이 캐릭터 사용 → 설정 저장을 누르세요. 불러올 때 모델은 필요 없습니다. 재준비용 중간 캐시도 유지합니다.','empty':'저장한 캐릭터가 없습니다. 그림을 생성하거나 현재 캐릭터를 저장하세요.','missing':'원본 그림 또는 모션 파일이 없거나 손상됐습니다. 로컬 백업을 복원하세요. 이 항목은 적용하지 않았습니다.','use':'이 캐릭터 사용','close':'닫기'}
}

TEXT['en'].update({
 'delete':'Delete…','delete_confirm_title':'Delete saved character',
 'cleanup':'Also delete files no longer in use',
 'cleanup_help':'Keeps files used by another saved version, current/pending characters, previous-character history, or unfinished preparation. Model downloads are kept.',
 'delete_confirm':'Permanently delete “{name}”?\n\nUp to {size} in {files} files will be removed. This does not use the Recycle Bin.',
 'kept':'Shared, in-use or unverified files will be kept.',
 'entry_only':'Only the saved entry will be removed. Original pictures, motion and caches will stay.',
 'delete_limited':'Some references or cache states could not be verified; those files will stay.',
 'delete_active':'This version is currently applied or pending. Choose another character and save settings first.',
 'delete_references':'Cannot verify current character references. Close active work or restore valid settings, then try again.',
 'delete_busy':'Character storage or preparation is busy. Wait for it to finish, then try again.',
 'delete_changed':'The selected version, files or references changed. Review the selection and confirm again.',
 'delete_unsafe':'The storage path could not be verified. No unverified path was deleted.',
 'delete_partial':'Cleanup could not finish. {size} was removed; the saved entry is kept when possible so you can retry.',
 'delete_failed':'Cannot delete this version. Check local permissions and close any preparation that uses it.',
 'delete_done':'Saved version deleted. Approximately {size} removed.',
 'cancel':'Cancel'})
TEXT['ko'].update({
 'delete':'삭제…','delete_confirm_title':'저장한 캐릭터 삭제',
 'cleanup':'다시 쓰지 않는 파일도 함께 삭제',
 'cleanup_help':'다른 저장본·현재/적용 대기 캐릭터·이전 외형 이력·완료되지 않은 준비 작업이 쓰는 파일은 유지합니다. 다운로드한 모델은 유지합니다.',
 'delete_confirm':'“{name}”을(를) 영구 삭제할까요?\n\n파일 {files}개, 최대 {size}를 정리합니다. 휴지통으로 보내지 않습니다.',
 'kept':'공유 중이거나 사용 중인 파일, 확인하지 못한 파일은 유지합니다.',
 'entry_only':'보관함 항목만 삭제합니다. 원본 그림·모션·캐시는 유지합니다.',
 'delete_limited':'일부 참조나 캐시 상태를 확인하지 못해 해당 파일은 유지합니다.',
 'delete_active':'현재 적용 중이거나 적용 대기 중인 버전입니다. 다른 캐릭터를 선택해 설정 저장한 뒤 삭제하세요.',
 'delete_references':'현재 캐릭터 참조를 확인하지 못했습니다. 진행 중인 작업을 마치거나 정상 설정을 복원한 뒤 재시도하세요.',
 'delete_busy':'캐릭터 저장소 또는 준비 작업을 사용 중입니다. 완료 후 재시도하세요.',
 'delete_changed':'선택한 버전·파일·참조가 바뀌었습니다. 목록을 확인하고 다시 승인하세요.',
 'delete_unsafe':'저장 경로를 확인하지 못했습니다. 확인하지 못한 경로는 삭제하지 않았습니다.',
 'delete_partial':'정리를 끝내지 못했습니다. {size}를 삭제했고, 가능하면 항목을 남겨 재시도할 수 있게 했습니다.',
 'delete_failed':'삭제하지 못했습니다. 파일 권한을 확인하고 관련 준비 작업을 마친 뒤 재시도하세요.',
 'delete_done':'저장한 버전을 삭제했습니다. 약 {size}를 정리했습니다.',
 'cancel':'취소'})


def size_text(size):
    return f'{size / 1024**2:.1f} MiB' if size>=1024**2 else f'{size / 1024:.1f} KiB'


def confirm_delete(parent,t,plan):
    box=QMessageBox(parent);box.setWindowTitle(t['delete_confirm_title']);box.setIcon(QMessageBox.Icon.Warning)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(t['delete_confirm'].format(name=plan['name'],size=size_text(plan['bytes']),files=plan['files']))
    info=t['kept'] if plan['include_files'] else t['entry_only']
    if plan['cleanup_limited']:info+='\n'+t['delete_limited']
    box.setInformativeText(info);box.setStandardButtons(QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
    box.button(QMessageBox.StandardButton.Yes).setText(t['delete']);box.button(QMessageBox.StandardButton.No).setText(t['cancel'])
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec()==QMessageBox.StandardButton.Yes


def save_named(spec,language,parent,folder=None):
    t=TEXT.get(language,TEXT['en']);name,accepted=QInputDialog.getText(parent,t['save'],t['name'])
    if not accepted:return None
    try:library.save(spec,name,folder);return t['saved']
    except (OSError,ValueError):return t['failed']


class LibraryDialog(QDialog):
    chosen=Signal(dict)

    def __init__(self,language='en',theme='dark',parent=None,folder=None,artwork_only=False,current_spec=None,reference_provider=None):
        super().__init__(parent)
        self.folder=folder;self.artwork_only=artwork_only;self.initial_spec=current_spec;self.reference_provider=reference_provider
        self.t=TEXT.get(language,TEXT['en']);self.setWindowTitle(self.t['title']);self.resize(640,540);self.setMinimumSize(480,480)
        layout=QVBoxLayout(self)
        help_label=QLabel(self.t['help']);help_label.setWordWrap(True);layout.addWidget(help_label)
        row=QHBoxLayout();self.items=QListWidget();row.addWidget(self.items,1)
        from .config import default_character
        self.preview=CharacterPreview(default_character());self.preview.setFixedSize(200,220);self.preview.theme=theme;row.addWidget(self.preview)
        layout.addLayout(row,1)
        self.status=QLabel('');self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        self.cleanup=QCheckBox(self.t['cleanup']);self.cleanup.setChecked(True);self.cleanup.setToolTip(self.t['cleanup_help']);layout.addWidget(self.cleanup)
        buttons=QHBoxLayout();self.remove=QPushButton(self.t['delete']);self.remove.clicked.connect(self.delete_selected);buttons.addWidget(self.remove)
        self.use=QPushButton(self.t['use']);self.use.clicked.connect(self.choose);buttons.addWidget(self.use)
        close=QPushButton(self.t['close']);close.clicked.connect(self.reject);buttons.addWidget(close);layout.addLayout(buttons)
        self.current=None;self.rows=[];self.items.currentRowChanged.connect(self.select)
        self.refresh(library.identity(current_spec) if current_spec else None)

    def references(self):
        if self.reference_provider is not None:return self.reference_provider()
        return {'active':[self.initial_spec] if self.initial_spec else [],'history':[]}

    def refresh(self,selected=None):
        self.items.blockSignals(True);self.items.clear()
        self.rows=[e for e in library.entries(self.folder) if not self.artwork_only or e['character'].get('kind')=='artwork']
        for row in self.rows:self.items.addItem(row['name'])
        index=next((i for i,e in enumerate(self.rows) if e['id']==selected),0) if self.rows else -1
        self.items.setCurrentRow(index);self.items.blockSignals(False);self.select(index)

    def select(self,index):
        from .config import default_character,safe_character
        self.current=None;self.use.setEnabled(False);self.remove.setEnabled(False)
        self.preview.spec=default_character();self.preview.update()
        if not 0<=index<len(self.rows):self.status.setText(self.t['empty']);return
        active=False
        try:
            refs=self.references()
            active=any(library.identity(safe_character(s))==library.identity(self.rows[index]['character']) for s in refs.get('active',[]))
            self.remove.setEnabled(not active and not refs.get('busy',False));self.remove.setToolTip(self.t['delete_active'] if active else self.t['cleanup_help'])
        except Exception:self.status.setText(self.t['delete_references']);return
        try:self.current=library.load(self.rows[index]['id'],self.folder)['character']
        except (OSError,ValueError,TypeError,KeyError):self.status.setText(self.t['missing']);return
        self.preview.spec=self.current;self.preview.update();self.status.setText(self.t['delete_active'] if active else '')
        self.use.setEnabled(True)

    def choose(self):
        if self.current is None:return
        try:spec=library.load(self.rows[self.items.currentRow()]['id'],self.folder)['character']
        except (OSError,ValueError,TypeError,KeyError):self.status.setText(self.t['missing']);self.use.setEnabled(False);return
        self.chosen.emit(spec);self.accept()

    def delete_selected(self):
        from . import library_delete
        index=self.items.currentRow()
        if not 0<=index<len(self.rows):return
        entry_id=self.rows[index]['id']
        try:
            plan=library_delete.plan_delete(entry_id,self.folder,self.cleanup.isChecked(),self.references)
            if not confirm_delete(self,self.t,plan):return
            result=library_delete.delete(plan,self.folder,self.references)
        except library_delete.DeleteError as error:
            self.refresh(entry_id)
            message=self.t.get(str(error),self.t['delete_failed'])
            self.status.setText(message.format(size=size_text(error.removed_bytes)));return
        except OSError:self.status.setText(self.t['delete_busy']);return
        self.refresh();self.status.setText(self.t['delete_done'].format(size=size_text(result['removed_bytes'])))
