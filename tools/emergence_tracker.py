#!/usr/bin/env python3
"""Emergence Tracker
===================

Usage:
  python tools/emergence_tracker.py instance1.json instance2.json [...]
    [--baseline BASELINE] [--output PATH] [--model MODEL] [--plot]

Each JSON file should contain metaphor interpretations from a single
instance. The format is a mapping of metaphor identifiers to lists of
interpretation strings. The filename (without extension) is used as the
instance label.

The script detects new interpretive clusters that do not appear in the
baseline library, using sentence embeddings and agglomerative clustering.
Metaphors with divergent yet convergent interpretations across instances
are logged to ``docs/examples/emergence_log.json`` with semantic distance metrics.
Optionally a heatmap visualises emergent interpretive intersections.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import AgglomerativeClustering
import torch


def load_log(path: Path) -> Dict[str, List[str]]:
    """Return mapping of metaphor IDs to interpretation strings."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, List[str]] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                result[key] = [str(v) for v in value]
            elif isinstance(value, str):
                result[key] = [value]
    return result


def aggregate_logs(paths: List[Path]) -> Dict[str, Dict[str, List[str]]]:
    """Combine logs from multiple instances."""
    aggregated: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for path in paths:
        instance = path.stem
        entries = load_log(path)
        for m_id, interpretations in entries.items():
            aggregated[m_id][instance].extend(interpretations)
    return aggregated


def load_baseline(path: Path, model: SentenceTransformer) -> torch.Tensor:
    """Return sentence embeddings for baseline interpretations."""
    if not path or not path.exists():
        return torch.empty(0)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    texts: List[str] = []
    if isinstance(data, dict):
        for val in data.values():
            if isinstance(val, list):
                texts.extend([str(v) for v in val])
            elif isinstance(val, str):
                texts.append(val)
    elif isinstance(data, list):
        for val in data:
            if isinstance(val, str):
                texts.append(val)
    return model.encode(texts, convert_to_tensor=True) if texts else torch.empty(0)


def detect_emergence(
    data: Dict[str, Dict[str, List[str]]],
    baseline_embeds: torch.Tensor,
    model: SentenceTransformer,
    base_threshold: float = 0.7,
    div_threshold: float = 0.4,
) -> Tuple[List[dict], Dict[Tuple[str, str], int]]:
    """Return emergent clusters and pairwise intersection counts."""
    results: List[dict] = []
    pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    for metaphor, inst_map in data.items():
        texts: List[str] = []
        labels: List[str] = []
        for inst, vals in inst_map.items():
            for t in vals:
                texts.append(t)
                labels.append(inst)
        if len(texts) < 2:
            continue

        embeds = model.encode(texts, convert_to_tensor=True)
        clustering = AgglomerativeClustering(
            n_clusters=None, distance_threshold=0.5, metric="cosine"
        )
        cluster_ids = clustering.fit_predict(embeds.cpu().numpy())

        for cid in set(cluster_ids):
            idxs = [i for i, c in enumerate(cluster_ids) if c == cid]
            insts = sorted({labels[i] for i in idxs})
            if len(insts) < 2:
                continue
            cluster_emb = embeds[idxs].mean(dim=0, keepdim=True)
            sim = (
                util.cos_sim(cluster_emb, baseline_embeds).max().item()
                if baseline_embeds.numel() > 0
                else 0.0
            )
            if sim >= base_threshold:
                continue
            if len(idxs) > 1:
                dists = 1 - util.cos_sim(embeds[idxs], embeds[idxs])
                triu = torch.triu_indices(len(idxs), len(idxs), offset=1)
                divergence = dists[triu[0], triu[1]].mean().item()
            else:
                divergence = 0.0
            if divergence < div_threshold:
                continue
            desc = texts[idxs[0]]
            results.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "metaphor": metaphor,
                    "instances": insts,
                    "description": desc,
                    "divergence": divergence,
                    "baseline_similarity": sim,
                }
            )
            for a, b in combinations(insts, 2):
                pair = tuple(sorted((a, b)))
                pair_counts[pair] += 1
    return results, pair_counts


def save_log(entries: List[dict], path: Path) -> None:
    """Append emergence entries to the log."""
    data: List[dict] = []
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    data.extend(entries)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def plot_heatmap(pair_counts: Dict[Tuple[str, str], int], labels: List[str]) -> None:
    """Display heatmap of emergent intersections."""
    n = len(labels)
    matrix = [[0 for _ in range(n)] for _ in range(n)]
    index = {label: i for i, label in enumerate(labels)}
    for (a, b), count in pair_counts.items():
        i = index[a]
        j = index[b]
        matrix[i][j] = matrix[j][i] = count

    plt.figure(figsize=(6, 5))
    plt.imshow(matrix, cmap="viridis", interpolation="nearest")
    plt.colorbar(label="Emergent Intersections")
    plt.xticks(range(n), labels, rotation=45, ha="right")
    plt.yticks(range(n), labels)
    plt.title("Emergent Interpretive Intersections")
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Track emergent interpretive signals")
    parser.add_argument("files", nargs="+", help="Instance interpretation logs")
    parser.add_argument("--baseline", help="Baseline library JSON")
    parser.add_argument("--output", default="docs/examples/emergence_log.json", help="Output log path")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="SentenceTransformer model")
    parser.add_argument("--plot", action="store_true", help="Display heatmap summary")
    args = parser.parse_args()

    paths = [Path(p) for p in args.files]
    model = SentenceTransformer(args.model)
    data = aggregate_logs(paths)
    baseline_embeds = load_baseline(Path(args.baseline), model) if args.baseline else torch.empty(0)

    entries, pair_counts = detect_emergence(data, baseline_embeds, model)

    if entries:
        save_log(entries, Path(args.output))
        print(f"{len(entries)} emergent clusters logged to {args.output}")
    else:
        print("No emergent clusters detected")

    if args.plot:
        labels = sorted({inst for m in data.values() for inst in m})
        if labels:
            plot_heatmap(pair_counts, labels)


if __name__ == "__main__":
    main()
