"""A small language model designs bounded visual parameters, never executable code."""
import json
import random
import re
from urllib.request import ProxyHandler, build_opener, Request

MODEL = "hf.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF:Q4_K_M"
MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF"
EARS = ("rabbit", "cat", "bear")
ACCESSORIES = ("scarf", "star", "leaf")
PALETTES = ("#b8a4ed", "#91d9c7", "#f0b2c9", "#9fc7ee", "#f3cd93", "#c2d394")


def random_character(seed: int | None = None) -> dict:
    seed = random.SystemRandom().randrange(2**31) if seed is None else seed
    rng = random.Random(seed)
    return {"seed": seed, "body": rng.choice(PALETTES), "accent": rng.choice(PALETTES),
            "ears": rng.choice(EARS), "accessory": rng.choice(ACCESSORIES), "source": "random"}


def validate_character(raw: dict, seed: int) -> dict:
    result = random_character(seed)
    for key in ("body", "accent"):
        if isinstance(raw.get(key), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", raw[key]):
            result[key] = raw[key]
    for key, choices in (("ears", EARS), ("accessory", ACCESSORIES)):
        if raw.get(key) in choices:
            result[key] = raw[key]
    return result


def generate_character() -> dict:
    seed = random.SystemRandom().randrange(2**31)
    # Fixed vocabulary intentionally excludes names, franchises, logos and external prompts.
    prompt = (
        f"Random seed {seed}. Design an original cute super-deformed fantasy creature. "
        'Return ONLY JSON with keys body and accent (hex colors), ears (rabbit/cat/bear), '
        'accessory (scarf/star/leaf). No existing characters, brands or names. '
        f"Inspiration: {random.Random(seed).choice(['moon garden', 'peach cloud', 'forest breeze', 'winter sunrise'])}."
    )
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"body": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
                             "accent": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"},
                             "ears": {"type": "string", "enum": list(EARS)},
                             "accessory": {"type": "string", "enum": list(ACCESSORIES)}},
              "required": ["body", "accent", "ears", "accessory"]}
    payload = {"model": MODEL, "stream": False, "format": schema, "prompt": prompt,
               "options": {"seed": seed, "temperature": 1.1, "num_predict": 100}}
    request = Request("http://127.0.0.1:11434/api/generate", json.dumps(payload).encode(),
                      {"Content-Type": "application/json"})
    # Explicit loopback only: do not send prompts through environment HTTP proxies.
    with build_opener(ProxyHandler({})).open(request, timeout=180) as response:
        output = json.load(response)
    raw = json.loads(output["response"])
    if not isinstance(raw, dict) or not all(key in raw for key in ("body", "accent", "ears", "accessory")):
        raise ValueError("Model returned incomplete character JSON; try again")
    result = validate_character(raw, seed)
    result.update(source="qwen", model=MODEL, model_card=MODEL_URL)
    return result
