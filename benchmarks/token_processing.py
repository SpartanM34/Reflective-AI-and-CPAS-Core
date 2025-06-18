from __future__ import annotations

"""Benchmark script for measuring token processing speed."""

import time
import json
from pathlib import Path
import spacy


def load_texts(base: Path) -> list[str]:
    texts: list[str] = []
    for path in base.rglob('*.md'):
        texts.append(path.read_text(encoding='utf-8'))
    return texts


def benchmark(nlp, texts: list[str]) -> dict[str, float]:
    """Return tokens per second for processing ``texts``."""
    start = time.perf_counter()
    tokens = 0
    for doc in nlp.pipe(texts):
        tokens += len(doc)
    elapsed = time.perf_counter() - start
    tps = tokens / elapsed if elapsed else 0.0
    return {"tokens": tokens, "seconds": elapsed, "tokens_per_second": tps}


def main() -> None:
    base = Path(__file__).resolve().parents[1] / 'metaphor-library'
    texts = load_texts(base)
    try:
        nlp = spacy.load('en_core_web_sm')
    except Exception:
        nlp = spacy.blank('en')
    result = benchmark(nlp, texts)
    out = Path(__file__).with_name('results.log')
    with out.open('a', encoding='utf-8') as f:
        f.write(json.dumps({"token_processing": result}) + '\n')
    print(result)


if __name__ == '__main__':
    main()
