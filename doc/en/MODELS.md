[English](../en/MODELS.md) | [한국어](../ko/MODELS.md) · [Documentation](../README.md)

# Models and character generation

| Role | Model/component | License | How it is used |
| --- | --- | --- | --- |
| Original text sLLM | Qwen/Qwen2.5-0.5B-Instruct | Apache-2.0 | Model lineage; Transformers is not installed by the app |
| Actual inference weights | Qwen/Qwen2.5-0.5B-Instruct-GGUF, Q4_K_M | Apache-2.0 | Downloaded from the official Qwen Hugging Face repository through Ollama |
| Inference server | Separately installed Ollama | MIT for its main project; bundled components retain individual terms | Local 127.0.0.1:11434/api/generate |
| Motion/image/background-removal models | None | Not applicable | Original vector drawing and procedural motion |

## Use the optional designer

Install and start [Ollama](https://ollama.com/), then download once:

```powershell
ollama pull hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M
```

Open **Character → Generate with Qwen → Save settings**. The weights are about 491 MB. For model-free use, choose **Random character** instead.

The sLLM generates colors, ears and an accessory as bounded JSON. The app draws these values using original SD vector shapes. This does not generate an arbitrary detailed raster illustration. Walking, blinking, ear/foot movement, jumps, bites and cracks use procedural animation, without a GPU or PyTorch requirement.

## Processing

1. Select a random seed and an abstract mood. A fixed prompt excludes existing names, franchises and brands.
2. Ask Ollama for schema-constrained body/accent hex colors, rabbit/cat/bear ears and scarf/star/leaf accessory.
3. Validate the fields. Invalid individual fields use deterministic fallback values; broken JSON or missing keys leaves the current character unchanged and reports an error.
4. Render original QPainter geometry; never evaluate model code, HTML or SVG.
5. Store seed, selected appearance and model identifier locally. Keep up to 20 previous designs for restoration.

Downloads are explicit, not automatic. No weights or Ollama executable are bundled. Inference can run offline after download. Generation runs in a worker thread; normal exit waits until generation finishes.

## Rights and reproducibility

The [character policy and provenance](CHARACTER-RIGHTS.md) record the default design, source hashes and objection to exclusive appropriation. Existing MIT permissions remain unchanged; the policy cannot block third-party applications automatically.

The default character is original vector-drawing code produced with AI assistance; it is not a licensed third-party mascot. No formal trademark/image clearance has been completed. Independent drawing does not by itself guarantee that no existing protected design or similar trademark conflicts with it. Copyright and trademark rights are distinct, and exclusive copyright in AI-assisted output depends on the applicable rules and human creative contribution. Keep design provenance and obtain suitable rights checks before branding or commercialization. [Official Korean AI copyright guidance](https://www.kipo.go.kr/ko/kpoBultnDetail.do?aprchId=BUT0000029&menuCd=SCD0200618&ntatcSeq=21075&sysCd=SCD02), [trademark scope](https://www.kipo.go.kr/ko/kpoContentView.do?menuCd=SCD0200242).

Apache-2.0 covers the model's terms and does not guarantee originality or non-infringement of generated output. Restricted prompts and original drawing primitives avoid intentionally copying known characters. External reference images and arbitrary user prompts are not supported.

Tags can change upstream. The tested digest is recorded in [model provenance](../../artifacts/model-provenance.json), and [the sample appearance](../../artifacts/qwen-character.json) came from actual local inference. Retain the model's original license in [licenses](../../licenses/upstream/Qwen-LICENSE.txt); do not relicense its weights as the app's MIT code. Any future motion model must have its identity, license, download size and usage documented before adding it.

Sources: [official GGUF card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF), [original model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), [Hugging Face Ollama guide](https://huggingface.co/docs/hub/en/ollama), [Ollama generation API](https://docs.ollama.com/api/generate).
