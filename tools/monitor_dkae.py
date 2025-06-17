import json
import logging
from pathlib import Path
from datetime import datetime
import subprocess

import spacy
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import AgglomerativeClustering

BASE_DIR = Path('metaphor-library/DKA-E')
from cpas_autogen.config import MONITOR_BASELINE, MONITOR_LOG

BASELINE_FILE = MONITOR_BASELINE
LOG_FILE = MONITOR_LOG
PAIRED_DIR = Path('paired-outputs')
MODEL_NAME = 'all-MiniLM-L6-v2'

logging.basicConfig(level=logging.INFO, format='%(message)s')


def load_modified_texts() -> list[str]:
    """Return texts from files changed in the last commit."""
    try:
        diff = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD~1'], text=True)
        files = diff.splitlines()
    except subprocess.CalledProcessError:
        files = []
    texts = []
    for file in files:
        path = Path(file)
        if not str(path).startswith(str(BASE_DIR)):
            continue
        if path.suffix == '.json':
            data = json.loads(path.read_text(encoding='utf-8'))
            for entry in data.get('metaphors', []):
                if isinstance(entry, dict) and 'metaphor' in entry:
                    texts.append(entry['metaphor'])
        elif path.suffix in {'.md', '.txt'}:
            texts.append(path.read_text(encoding='utf-8'))
    return texts


def interpretive_bandwidth(texts: list[str], model: SentenceTransformer) -> float:
    if not texts:
        return 0.0
    embeddings = model.encode(texts, convert_to_tensor=True)
    if len(texts) <= 1:
        return float(len(texts))
    clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=0.5, metric='cosine')
    labels = clustering.fit_predict(embeddings.cpu().numpy())
    return float(len(set(labels)))


def symbolic_density(texts: list[str], nlp) -> float:
    tokens = [tok for text in texts for tok in nlp(text)]
    if not tokens:
        return 0.0
    evocative = [t for t in tokens if t.pos_ in ('ADJ', 'ADV')]
    structural = [t for t in tokens if t.pos_ in ('NOUN', 'VERB')]
    return len(evocative) / len(structural) if structural else 0.0


def cross_instance_divergence(model: SentenceTransformer) -> float:
    outputs = []
    if not PAIRED_DIR.exists():
        return 0.0
    for file in sorted(PAIRED_DIR.glob('*.txt')):
        outputs.append(file.read_text(encoding='utf-8'))
    if len(outputs) < 2:
        return 0.0
    embs = model.encode(outputs, convert_to_tensor=True)
    sim = util.cos_sim(embs[0], embs[1])
    return float(1 - sim.item())


def load_baseline() -> dict:
    if BASELINE_FILE.exists():
        return json.loads(BASELINE_FILE.read_text())
    return {}


def save_baseline(metrics: dict) -> None:
    BASELINE_FILE.write_text(json.dumps(metrics, indent=2))


def log_results(metrics: dict) -> None:
    data = {}
    if LOG_FILE.exists():
        data = json.loads(LOG_FILE.read_text())
    data[datetime.utcnow().isoformat()] = metrics
    LOG_FILE.write_text(json.dumps(data, indent=2))


def rollback(reason: str) -> None:
    logging.error('Rollback triggered: %s', reason)
    try:
        subprocess.run(['git', 'revert', '--no-edit', 'HEAD'], check=True)
    except subprocess.CalledProcessError as exc:
        logging.error('Automatic revert failed: %s', exc)


def main() -> None:
    model = SentenceTransformer(MODEL_NAME)
    nlp = spacy.load('en_core_web_sm')
    texts = load_modified_texts()
    metrics = {
        'interpretive_bandwidth': interpretive_bandwidth(texts, model),
        'symbolic_density': symbolic_density(texts, nlp),
        'cross_instance_divergence': cross_instance_divergence(model),
    }

    baseline = load_baseline()
    if not baseline:
        save_baseline(metrics)
    else:
        band_drop = baseline.get('interpretive_bandwidth', 0) * 0.8
        dens_drop = baseline.get('symbolic_density', 0) * 0.8
        div_drop = baseline.get('cross_instance_divergence', 0) * 0.8
        if metrics['interpretive_bandwidth'] < band_drop:
            rollback('Interpretive Bandwidth Reduction >20%')
        if metrics['symbolic_density'] < dens_drop:
            rollback('Symbolic Density Collapse')
        if metrics['cross_instance_divergence'] < div_drop:
            rollback('Cross-Instance Divergence Loss')

    log_results(metrics)


if __name__ == '__main__':
    main()
