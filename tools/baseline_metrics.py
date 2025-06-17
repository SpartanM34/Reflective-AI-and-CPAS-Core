import json
from pathlib import Path
from datetime import datetime

import spacy
import torch
from sentence_transformers import util


def load_metaphor_texts(base_dir: Path) -> list[str]:
    texts = []
    for path in base_dir.glob('*.json'):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for entry in data.get('metaphors', []):
            if isinstance(entry, dict) and 'metaphor' in entry:
                texts.append(entry['metaphor'])
    for name in ('README.md', 'index.md'):
        fp = base_dir / name
        if fp.exists():
            texts.append(fp.read_text(encoding='utf-8'))
    return texts


def lexical_diversity(texts: list[str], nlp) -> float:
    tokens = [tok.text.lower() for text in texts for tok in nlp(text)]
    return len(set(tokens)) / len(tokens) if tokens else 0.0


def symbolic_density(texts: list[str], nlp) -> float:
    tokens = [tok for text in texts for tok in nlp(text)]
    if not tokens:
        return 0.0
    symbolic = [t for t in tokens if t.is_punct or (not t.is_alpha and not t.like_num)]
    return len(symbolic) / len(tokens)


def divergence_space(texts: list[str], nlp) -> float:
    if len(texts) < 2:
        return 0.0
    vecs = torch.tensor([nlp(t).vector for t in texts])
    sim = util.cos_sim(vecs, vecs).cpu().numpy()
    triu = np.triu_indices_from(sim, k=1)
    distances = 1 - sim[triu]
    return float(distances.mean())


def main():
    base = Path('metaphor-library/DKA-E')
    texts = load_metaphor_texts(base)
    nlp = spacy.load('en_core_web_sm')

    metrics = {
        'lexical_diversity': lexical_diversity(texts, nlp),
        'symbolic_density': symbolic_density(texts, nlp),
        'divergence_space': divergence_space(texts, nlp),
    }

    examples_dir = Path(__file__).resolve().parents[1] / 'docs' / 'examples'
    examples_dir.mkdir(parents=True, exist_ok=True)
    out_file = examples_dir / 'baseline_metrics.json'
    data = {}
    if out_file.exists():
        with open(out_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[datetime.utcnow().isoformat()] = metrics
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


if __name__ == '__main__':
    import numpy as np
    main()
