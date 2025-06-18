import json
from pathlib import Path
from datetime import datetime
import random

import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


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
    """Return the mean pairwise distance between texts using TF-IDF vectors."""
    if len(texts) < 2:
        return 0.0
    tfidf = TfidfVectorizer().fit_transform(texts).toarray()
    sim = cosine_similarity(tfidf)
    triu = np.triu_indices_from(sim, k=1)
    distances = 1 - sim[triu]
    return float(np.mean(distances))


def reliability_score(metric_func, texts: list[str], nlp, iterations: int = 5) -> float:
    """Estimate split-half reliability for ``metric_func``."""
    if len(texts) < 2:
        return 0.0
    scores_a, scores_b = [], []
    for _ in range(iterations):
        random.shuffle(texts)
        mid = len(texts) // 2
        first, second = texts[:mid], texts[mid:]
        if not first or not second:
            continue
        scores_a.append(metric_func(first, nlp))
        scores_b.append(metric_func(second, nlp))
    if len(scores_a) < 2:
        return 0.0
    val = np.corrcoef(scores_a, scores_b)[0, 1]
    if np.isnan(val):
        return 0.0
    return float(val)


def metric_correlations(texts: list[str], nlp, iterations: int = 5) -> dict[str, float]:
    """Return pairwise correlations between metric values across random subsets."""
    metrics = [lexical_diversity, symbolic_density, divergence_space]
    vals = []
    for _ in range(iterations):
        subset = random.sample(texts, k=max(2, len(texts) - 1))
        vals.append([m(subset, nlp) for m in metrics])
    arr = np.array(vals)
    corr = np.corrcoef(arr, rowvar=False)
    names = ["lexical_diversity", "symbolic_density", "divergence_space"]
    result = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            val = corr[i, j]
            if np.isnan(val):
                val = 0.0
            result[f"{names[i]}_{names[j]}"] = float(val)
    return result


def validation_statistics(texts: list[str], nlp, iterations: int = 5) -> dict:
    """Compute reliability and correlation statistics for the metrics."""
    reliability = {
        "lexical_diversity": reliability_score(lexical_diversity, texts, nlp, iterations),
        "symbolic_density": reliability_score(symbolic_density, texts, nlp, iterations),
        "divergence_space": reliability_score(divergence_space, texts, nlp, iterations),
    }
    return {
        "reliability": reliability,
        "correlations": metric_correlations(texts, nlp, iterations),
    }


def main():
    base = Path('metaphor-library/DKA-E')
    texts = load_metaphor_texts(base)
    try:
        nlp = spacy.load('en_core_web_sm')
    except Exception:
        nlp = spacy.blank('en')

    metrics = {
        'lexical_diversity': lexical_diversity(texts, nlp),
        'symbolic_density': symbolic_density(texts, nlp),
        'divergence_space': divergence_space(texts, nlp),
    }
    validation = validation_statistics(texts, nlp)

    examples_dir = Path(__file__).resolve().parents[1] / 'docs' / 'examples'
    examples_dir.mkdir(parents=True, exist_ok=True)
    out_file = examples_dir / 'baseline_metrics.json'
    data = {}
    if out_file.exists():
        with open(out_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data[datetime.utcnow().isoformat()] = {
        **metrics,
        'validation': validation,
    }
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


if __name__ == '__main__':
    main()
