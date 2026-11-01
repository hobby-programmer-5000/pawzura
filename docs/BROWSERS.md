# 브라우저 확장과 로컬 연결

## 설치

Chrome: `chrome://extensions`, Edge: `edge://extensions`, Brave: `brave://extensions`에서 개발자 모드 → 압축 해제된 확장 로드 → `extensions/chromium` 선택. Opera/Vivaldi 등 Chromium 브라우저도 같은 방식으로 개발용 확장을 설치할 수 있으나 브라우저 버전별 검증이 필요합니다.

Firefox: `about:debugging#/runtime/this-firefox` → 임시 부가 기능 로드 → `extensions/firefox/manifest.json`. **임시 설치는 Firefox 재시작 시 해제됩니다.** 지속 배포에는 Mozilla의 부가 기능 서명(비공개/unlisted 서명 포함)이 필요하며 이 저장소는 서명된 XPI를 포함하지 않습니다. Zen도 Firefox 확장 호환 상태에 따라 별도 확인하세요.

Firefox 파일은 `scripts/sync_extensions.py`로 Chromium의 공유 JS/HTML/CSS를 복사하고 Firefox용 manifest를 생성합니다. 공유 파일을 수정하면 다시 실행하세요.

## 연결과 설정

앱에서 올바른 브라우저 식별자(chrome/edge/firefox/brave/opera/vivaldi/arc/zen)를 선택하고 연결 JSON을 복사합니다. 확장 옵션 화면에 붙여넣고 저장합니다. 토큰은 해당 Windows 사용자만 알고 있어야 하며 Git에 커밋하거나 공개하지 않습니다. 앱 설정 파일의 token을 교체하고 확장을 다시 연결하면 이전 연결을 폐기할 수 있습니다.

앱에서 브라우저별 감시와 전체 감시를 모두 활성화해야 정책이 적용됩니다. `preview_only`면 애니메이션만 동작합니다. 확장 배지: ON = 실제 감시, PRE = 미리보기, OFF = 연결 실패, 빈 배지 = 연결됐지만 감시 비활성.

각 브라우저 창의 활성 여부와 관계없이 열린 탭을 검사합니다. 200개를 넘는 탭은 한 차례에 200개만 처리하므로 닫힌 탭이 빠진 다음 남은 탭이 검사됩니다. Chromium worker는 중단 후 alarm으로 재시작되어 최대 약 30초의 복구 지연이 있을 수 있습니다. 백그라운드 탭의 깨물기는 바탕화면 우측 위에 표시합니다. 창이나 실제 탭의 버튼을 마우스로 클릭하지 않으며, 확장이 대상 탭 URL을 재확인한 뒤 `tabs.remove`를 호출합니다.

## 기본 페이지와 사이트 규칙

브라우저 기본 홈/새 탭 페이지는 `pawzura/policy.py`의 명시적 내부 URL 목록으로 허용합니다. 설정된 사용자 홈 URL을 읽는 권한은 요청하지 않으므로 **사용자 지정 시작 URL은 직접 허용**해야 합니다. `about:blank`와 새 탭 화면의 내부 리디렉션은 처리하지만 브라우저 버전에서 새 내부 URL을 쓰면 목록 업데이트가 필요할 수 있습니다.

`example.com`은 `https://example.com`으로 저장합니다. 경로 제한을 지원하지 않으므로 경로·query·fragment를 넣으면 오류를 표시합니다. `*.example.com`은 HTTPS 하위 도메인만 허용하며 루트 도메인은 별도 추가해야 합니다. 기본 포트는 정규화합니다. IDN 호스트는 ASCII IDNA로 비교합니다. `example.com.evil.test`나 사용자정보를 이용한 우회는 허용하지 않습니다.

## 보안 성격과 데이터

브리지는 `127.0.0.1`에만 바인딩하며 무작위 256비트 토큰을 헤더로 확인합니다. 예상 Host, 요청 크기, payload 형태, 브라우저 식별자를 검사합니다. 일반 웹 페이지에는 CORS 권한을 주지 않고, 확장 origin만 응답합니다. 쿠키를 쓰지 않고 URL/토큰을 로그에 남기지 않습니다. 열린 URL은 로컬 메모리의 유효기간 20초 티켓으로만 취급합니다. 브라우저별 allowlist와 extension pairing token은 각각 앱 설정과 확장의 local storage에 저장합니다.

탭 목록은 모델에 전달하지 않습니다. 탭 감시는 앱의 정책이고 모델은 색상·형태 생성만 담당합니다. 등록되지 않은 확장/브라우저, 시크릿 모드에서 권한을 주지 않은 확장, 앱을 종료한 상태는 제어할 수 없습니다. 로컬 사용자가 토큰과 설정을 수정하거나 앱을 종료하는 것을 막지 않습니다. 사용자의 집중 보조 용도입니다.

브라우저 확장 권한 문서: https://developer.chrome.com/docs/extensions/reference/api/tabs

Firefox 설치·서명 안내: https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/
