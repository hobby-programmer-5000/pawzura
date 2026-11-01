# 모델과 캐릭터 생성

## 사용하는 모델

| 역할 | 식별자 | 라이선스 | 사용 방식 |
| --- | --- | --- | --- |
| 외형 설계 sLLM | `Qwen/Qwen2.5-0.5B-Instruct` | Apache-2.0 | 원본 모델의 계보·고지. 직접 Transformers를 설치하지 않음 |
| 실제 추론 가중치 | `Qwen/Qwen2.5-0.5B-Instruct-GGUF`, `qwen2.5-0.5b-instruct-q4_k_m.gguf` | Apache-2.0 | Hugging Face 공식 Qwen 저장소에서 Ollama로 내려받음 |
| 추론 서버 | Ollama (사용자 별도 설치) | MIT (본체; 개별 포함 구성요소는 별도) | `127.0.0.1:11434/api/generate` |
| 모션 모델 | 없음 | 해당 없음 | 자체 절차적 애니메이션 |
| 이미지/배경 제거 모델 | 없음 | 해당 없음 | 자체 벡터 도형, 투명 Qt 창 |

모델 카드: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF

원본 카드: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct

GGUF 사용 안내: https://huggingface.co/docs/hub/en/ollama

Ollama API: https://docs.ollama.com/api/generate

## 처리 흐름

1. OS 난수로 seed와 추상적 분위기를 선택합니다.
2. 이름, 프랜차이즈, 상표를 사용하지 않는 고정 영문 프롬프트로 JSON 생성을 요청합니다.
3. `body`, `accent`는 `#RRGGBB` 색상만, `ears`는 rabbit/cat/bear, `accessory`는 scarf/star/leaf만 허용합니다.
4. 모델 출력은 실행·eval·동적 SVG/HTML로 해석하지 않습니다. 부적절한 필드는 해당 seed의 로컬 난수 값으로 보정합니다. JSON 자체가 손상되거나 필수 키가 없으면 오류를 표시하고 기존 캐릭터를 유지합니다.
5. 원래 설계는 프로그램 고유 QPainter 도형에 반영됩니다. 머리/몸통 비율과 귀·장식의 제한된 선택지로 정체성을 유지합니다. 따라서 사용자가 상상하는 임의의 세밀한 일러스트를 생성하는 기능과는 다릅니다.
6. 설정에 seed, 색상, 형태, 모델 식별자를 보관합니다. 최근 캐릭터 20개를 복원할 수 있습니다.

다운로드는 사용자가 명령으로 명시적으로 수행합니다. 앱은 모델을 자동 설치하지 않고, 모델 가중치를 EXE에 포함하지 않습니다. 최초 다운로드 이후 추론에는 인터넷이 필요하지 않습니다. 생성 오류가 발생해도 기존 캐릭터와 감시는 계속 동작합니다. UI 스레드와 추론 스레드를 분리하며 생성 중에는 프로세스 종료를 잠시 보류합니다.

## 왜 별도 모션 모델을 쓰지 않는가

144×146 논리 픽셀 크기의 캐릭터는 머리·귀·발·장식을 앱이 각각 그립니다. 발과 귀는 sin/cos, 이동은 시간차 기반 보간, 점프는 포물선에 가까운 곡선으로 표현합니다. 프레임 간 외형 일관성이 보장되고 비디오 생성 모델의 VRAM·지연·라이선스 부담이 없습니다. `draw_character`, `Pet`, `Crack`이 구현 위치입니다. 모션 모델을 추가하는 경우 모델 카드·라이선스·다운로드 크기·사용 방식·고지를 이 문서와 THIRD-PARTY-NOTICES에 먼저 추가해야 합니다.

## 권리 및 버전 관리

오픈 모델의 Apache-2.0은 가중치의 사용 조건입니다. 생성물의 독창성, 저작권 성립 또는 비침해를 보증하지 않습니다. 고유 도형과 제한된 프롬프트로 알려진 캐릭터를 의도적으로 복제하는 흐름을 피합니다. 외부 이미지나 사용자 제공 IP는 현재 지원하지 않습니다.

모델 태그는 upstream 변경 가능성이 있으므로 재현성이 필요한 배포는 `ollama show --modelfile` 및 `ollama list`의 digest도 별도 기록해야 합니다. 모델은 제품 소스 라이선스인 MIT로 재라이선스하지 않습니다. 원문은 `licenses/upstream/Qwen-LICENSE.txt`에 보관합니다.
