[English](../en/ADVANCED-MODELS.md) | [한국어](../ko/ADVANCED-MODELS.md) · [문서 목록](../README.ko.md)

# 고급 모델과 메모리

**Ollama를 실행하고, 선택한 모델을 먼저 내려받고, 충분한 가용 시스템 RAM과 GPU VRAM을 확보하세요.** 앱 실행·임의/직접 선택 외형·캐릭터 애니메이션에는 모델이 필요 없습니다. 모델은 설명을 기존 벡터 특징으로 해석하며 새 그림·의상·머리카락을 그리지 않습니다. 큰 모델이나 높은 정밀도가 설명 해석에 도움이 될 수 있지만 더 예쁜 외형이나 완벽한 반영을 보장하지 않습니다.

## 모델 선택

1. **고급 → 고급 캐릭터 모델 사용**을 켭니다.
2. GPU의 VRAM 용량 **2·4·6·8GB**를 고릅니다. 모르면 **CPU / 모름**과 기본 모델을 유지하세요.
3. **캐릭터 → 외형 설계 모델**에서 선택합니다. 고급을 켰다고 큰 모델을 자동 선택하지 않습니다.
4. 모델 선택 옆 **명령 복사**를 누릅니다. **PowerShell**을 열고(시작 버튼 우클릭 → Windows PowerShell 또는 터미널) 붙여넣은 뒤 Enter를 누르세요. `success`까지 기다렸다 앱으로 돌아옵니다. 읽기 전용 명령과 용량은 저장 전이라도 현재 선택을 따릅니다. 캐릭터·고급의 **모델 준비 안내**에서 다섯 모델 명령을 모두 볼 수 있습니다.
5. Ollama를 켜둔 채 생성하고 미리보기를 확인한 뒤 **설정 저장**을 누릅니다. 모델·고급 설정은 업무/여가 허용 목록과 별도로 보관합니다. VRAM 기준을 낮춰 선택한 모델이 빠지면 1.5B로 선택이 돌아가며 현재 캐릭터는 유지됩니다.

| 직접 선택하는 VRAM 기준 | 권장 후보 | 모델 파일 약 | 라이선스 |
| --- | --- | --- | --- |
| CPU / 모름 | Qwen2.5 0.5B 또는 1.5B Instruct · Q4_K_M | 0.49 / 1.12GB | Apache-2.0 |
| 2GB | Qwen2.5 1.5B Instruct · Q4_K_M | 1.12GB | Apache-2.0 |
| 4GB | Qwen3 4B · Q4_K_M | 2.50GB | Apache-2.0 |
| 6GB | Qwen3 4B · Q8_0 (같은 매개변수 수, 높은 정밀도) | 4.28GB | Apache-2.0 |
| 8GB | Qwen3 8B · Q4_K_M | 5.03GB | Apache-2.0 |

## 모든 용량 기준의 정확한 다운로드 명령

선택한 모델의 명령 하나만 실행하세요. 모델별로 별도 다운로드하며 VRAM 기준만 고른다고 설치되지 않습니다. 이미 설치한 모델은 다시 받을 필요 없습니다.

### CPU / 모름: 가벼운 0.5B (약 0.49GB)

```powershell
ollama pull hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M
```

### 2GB / CPU: 1.5B (약 1.12GB)

```powershell
ollama pull hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
```

### 4GB: Qwen3 4B Q4_K_M (약 2.50GB)

```powershell
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```

### 6GB: Qwen3 4B Q8_0 (약 4.28GB)

```powershell
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q8_0
```

### 8GB: Qwen3 8B Q4_K_M (약 5.03GB)

```powershell
ollama pull hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
```

`success`가 뜬 뒤 `ollama list`에 **정확한 식별자**가 있어야 합니다. `hf.co/…` 이름과 양자화 접미사까지 같아야 합니다. 비슷한 이름의 모델·다른 양자화·다른 폴더에 직접 받은 GGUF가 앱이 요청하는 모델로 자동 대체되지는 않습니다. 앱에서 **Qwen으로 생성 → 미리보기 확인 → 설정 저장**을 진행하세요. PowerShell에서 `ollama`를 찾지 못하면 Ollama 설치·실행 후 PowerShell을 새로 여세요. 다운로드에는 인터넷·디스크 공간이 필요하고, 실행 메모리와는 별개입니다.

## 장착 용량과 남은 메모리

**시스템 RAM 8GB와 GPU VRAM 8GB는 다릅니다.** 고급에는 GPU의 전용 VRAM 기준을 넣으세요. 모르면 CPU / 모름을 고르고, Windows RAM이 8GB라는 이유로 8GB 모델 기준을 선택하지 마세요.

이는 보수적인 선택 가이드이며 **실측 최소 VRAM이나 기기별 검증 결과가 아닙니다.** 장착 용량과 남은 VRAM은 다릅니다. 파일 크기 외에 실행 버퍼·컨텍스트/KV 캐시·화면/드라이버·다른 작업의 메모리가 필요합니다. CPU 분산에는 시스템 RAM이 필요하며 속도가 크게 느려질 수 있습니다. 내장/공유 메모리는 전용 GPU VRAM과 같지 않습니다. 앱이 하드웨어를 감지하거나 메모리를 예약하거나 GPU 실행을 강제하지 않습니다. Ollama 지원 여부는 GPU·드라이버·백엔드에 따라 다릅니다. [GPU 안내](https://docs.ollama.com/gpu)를 참고하세요.

`ollama ps`로 실제 로드 크기와 CPU/GPU 배치를 확인하세요. 작은 모델부터 시작하고 무거운 GPU 작업을 줄이며, 부족하면 더 작은 모델을 고르세요. 시스템 RAM과 CPU 성능이 충분하면 GPU는 필수가 아닙니다. 고급 요청은 컨텍스트 4,096토큰·비사고 JSON 생성·180초 제한을 사용하며 완료 후 사용 모델을 내립니다(`keep_alive: 0`). 다른 모델은 종료하지 않습니다. 시간 초과·로드 실패 시 현재 캐릭터를 유지합니다. [Ollama 메모리·배치 설명](https://docs.ollama.com/faq), [사고 모드 제어](https://docs.ollama.com/capabilities/thinking)를 참고하세요.

## 모델과 라이선스

추가 지원 식별자는 다음과 같습니다.

```text
hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
hf.co/Qwen/Qwen3-4B-GGUF:Q8_0
hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
```

공식 출처: [Qwen3 4B 파일](https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/main), [Qwen3 8B 파일](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/main), [Hugging Face의 Ollama 연동](https://huggingface.co/docs/hub/en/ollama). 리비전·정확한 바이트 수·업스트림 SHA-256은 [모델 목록](../../artifacts/model-catalog.json)에 있습니다. 수정하지 않은 라이선스 원문: [4B](../../licenses/upstream/Qwen3-4B-LICENSE.txt), [8B](../../licenses/upstream/Qwen3-8B-LICENSE.txt), [제3자 고지](THIRD-PARTY-NOTICES.md). 미세조정·가중치 재배포는 하지 않습니다.

## 생성 실패 시

- **연결 실패 / 시간 초과:** Ollama를 실행·업데이트하세요. 표시된 모델 다운로드 명령을 실행하고 CPU 생성이 오래 걸리면 더 작은 모델로 시도하세요.
- **모델 없음 / 지원하지 않음:** 이제 오류에 요청 모델과 전체 다운로드 명령을 표시합니다. 해당 모델 옆 **명령 복사**로 받아 `success`를 확인한 뒤 다시 생성하세요. 이미 설치했다면 정확한 이름과 Qwen3 지원 Ollama 버전을 확인하세요. 앱은 `127.0.0.1:11434`를 사용하므로 CLI가 다른 Ollama 호스트나 다른 계정에서 실행되면 모델 목록이 다를 수 있습니다. 다른 모델로 몰래 대체하지 않습니다.
- **메모리 부족:** 작은 모델을 고르거나 RAM·VRAM을 확보하세요. 용량 기준은 메모리 검사가 아닙니다.
- **특징 누락:** 직접 고르는 색·특징 옵션으로 강제하세요. 모든 결과는 기존 제한된 형식 검사를 거칩니다.

추가 모델 식별자·JSON 요청·메모리/오류 처리·설정 저장은 자동 검사로 확인합니다. 이것은 모든 2·4·6·8GB GPU의 실제 추론 속도·정확도·메모리 적합성 검증을 뜻하지 않습니다. 신규 모델 가중치를 내려받아 기기 추론 검사를 하지는 않았습니다. 기존 0.5B/1.5B 로컬 추론 결과는 [검증 기록](VALIDATION.md)에 남아 있습니다.
