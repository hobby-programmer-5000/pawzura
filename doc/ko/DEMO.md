[English](../en/DEMO.md) | [한국어](../ko/DEMO.md) · [문서 목록](../README.ko.md)

# README 동작 데모

[영어 MP4](../../artifacts/demo/pawzura-demo-en.mp4) · [한국어 MP4](../../artifacts/demo/pawzura-demo-ko.mp4). 각각 16초의 무음 영상이며, README에는 반복 재생하는 GIF 미리보기를 넣었습니다.

창·작업 표시줄·사이트·브라우저 탭은 직접 만든 가상 화면입니다. 캐릭터에는 Pawzura의 기존 `Pet.bite`, `Pet.tick`, `draw_character`, 균열 효과와 별도 탭 표적을 사용합니다. 물기 콜백은 메모리 안의 장면 상태만 바꿉니다. 가상 프로그램이 먼저 사라지고, 이어서 가상 탭 하나만 사라지며 허용한 탭과 브라우저는 유지됩니다. 동작 방식을 보여주는 연출이며, 실제 창 종료나 확장 프로그램 통합을 녹화한 증거는 아닙니다.

렌더러는 Qt를 **offscreen**으로 강제하고 렌더링 전에 확인합니다. guardian·브리지를 시작하거나 네이티브 창 종료를 호출하지 않고, 브라우저 연결·사용자 프로필 읽기·바탕화면 캡처·시작 프로그램 및 설정 변경도 하지 않습니다. 영상은 앱의 기능에 집중하며, 가상 창과 장면의 제작 방식은 이 문서에서 설명합니다. 앱 기본값은 감시 OFF·미리보기 ON·사이트 제어 OFF를 유지합니다.

## Windows에서 재현

기존 표준 CPython 프로젝트 환경과 PySide6, PATH에서 사용할 수 있는 별도 FFmpeg를 사용하세요. 시스템의 Segoe UI·맑은 고딕 글꼴을 읽을 수 있어야 합니다. 글꼴을 찾지 못하면 깨진 글자를 결과로 남기지 않고 중단합니다. 모델이나 영상 생성 서비스는 사용하지 않습니다.

**새로운** 프레임 폴더와 출력 파일을 지정하세요. 렌더러와 아래 명령은 덮어쓰기를 거부합니다. 한국어는 언어 인자와 모든 경로의 `en`을 `ko`로 바꾸세요.

```powershell
.\.venv-standard\Scripts\python.exe scripts/render_demo.py --language en --output .cache/demo-en
ffmpeg -nostdin -n -framerate 24 -i .cache/demo-en/frame-%04d.png -an -c:v libx264 -crf 19 -pix_fmt yuv420p -movflags +faststart demo-en.mp4
ffmpeg -nostdin -n -framerate 24 -i .cache/demo-en/frame-%04d.png -filter_complex "fps=12,scale=896:560:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff:max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" -loop 0 demo-en.gif
```

`render.json`에는 1120×700 프레임 384개, 가상 종료 콜백 두 번, 허용한 탭의 유지가 기록됩니다. MP4는 24 fps, GIF는 896×560에서 약 12 fps입니다. 커밋 대상 [매니페스트](../../artifacts/demo/manifest.json)는 정확한 출력 해시·구성 요소 버전·출처를 기록합니다. [미디어 고지](../../artifacts/demo/NOTICE.md)에는 권리와 기여 역할을 기록합니다. 향후 앱 빌드에는 명시한 공개 데모 파일 6개만 복사하며 작업 프레임과 진단 자료는 제외합니다.

## 권리와 확인 범위

직접 만든 장면·자막·스크립트와 기존 기본 캐릭터는 저장소의 MIT 조건을 유지하며, 새 비상업적 이용 제한을 지정하지 않습니다. 제품 기획은 제작자가 맡고 코드·화면 구성·검증은 ChatGPT (Codex)가 지원했습니다. 외부 사이트·로고·음악·모델 출력·글꼴 파일은 포함하지 않습니다. Windows 글꼴은 픽셀로만 렌더링하며 [Microsoft 글꼴 출력 FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)를 따릅니다. FFmpeg 9.0.2는 별도 개발용 인코더로 사용했고, 설치된 빌드는 GPL-3.0-or-later로 표시되며 재배포하지 않습니다. [FFmpeg 라이선스](https://ffmpeg.org/legal.html)는 직접 만든 장면의 조건과 별개입니다.

두 언어의 점프·물기·가상 종료·표적·마지막 프레임을 살펴봤으며 MP4/GIF 전체 디코딩과 스트림 정보도 확인했습니다. 이 연출로 실제 앱·브라우저 통합, Windows 11, GPU, 선택형 모델의 호환성 검증 범위를 확대하지 않습니다. 실제 통합 검사 범위는 [검증 기록](VALIDATION.md)을 참고하세요.
