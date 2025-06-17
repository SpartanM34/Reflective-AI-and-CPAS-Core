#!/usr/bin/env python3
"""Cross-Instance Divergence Heatmap
================================

Usage:
  python tools/divergence_heatmap.py instance1.json instance2.json [instance3.json ...]

Each JSON file should contain metaphor interpretations from a single instance.
The format may be either a list of interpretation strings or a mapping from
metaphor identifiers to lists of interpretations. The filename (without
extension) is used as the instance label.

The script computes the average cosine distance between interpretations of each
pair of instances using ``sentence-transformers``. Results are printed as a
matrix, visualized as a heatmap, and logged to ``docs/examples/divergence_log.json`` for
further analysis.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer, util
import torch


def load_interpretations(path: Path) -> dict[str, list[str]]:
    """Return a mapping of metaphor keys to lists of interpretations."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"all": [str(t) for t in data]}
    if isinstance(data, dict):
        if "interpretations" in data and isinstance(data["interpretations"], list):
            return {"all": [str(t) for t in data["interpretations"]]}
        result = {}
        for key, value in data.items():
            if isinstance(value, list):
                result[key] = [str(t) for t in value]
        if result:
            return result
    raise ValueError(f"Unrecognized format in {path}")


def embed_groups(groups: dict[str, list[str]], model: SentenceTransformer) -> dict[str, torch.Tensor]:
    """Encode interpretations for each metaphor key."""
    embeddings = {}
    for key, texts in groups.items():
        embeddings[key] = model.encode(texts, convert_to_tensor=True)
    return embeddings


def pair_distance(a: dict[str, torch.Tensor], b: dict[str, torch.Tensor]) -> float:
    """Average cosine distance across overlapping metaphor keys."""
    keys = set(a) & set(b)
    if not keys:
        keys = set(a) | set(b)
    distances = []
    for key in keys:
        e1 = a.get(key)
        e2 = b.get(key)
        if e1 is None or e2 is None:
            continue
        sim = util.cos_sim(e1, e2)
        distances.append(1 - sim.mean().item())
    return float(sum(distances) / len(distances)) if distances else 0.0


def save_log(labels: list[str], matrix: list[list[float]], path: Path) -> None:
    """Append divergence data to log."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "labels": labels,
        "matrix": matrix,
    }
    data = []
    if path.exists():
        try:
            with path.open() as f:
                data = json.load(f)
        except Exception:
            data = []
    data.append(entry)
    with path.open("w") as f:
        json.dump(data, f, indent=2)


def show_heatmap(labels: list[str], matrix: list[list[float]]) -> None:
    plt.figure(figsize=(6, 5))
    plt.imshow(matrix, cmap="magma", interpolation="nearest")
    plt.colorbar(label="Cosine Distance")
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right")
    plt.yticks(range(len(labels)), labels)
    plt.title("Cross-Instance Divergence")
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cross-instance divergence heatmap")
    parser.add_argument("files", nargs="+", help="JSON interpretation files")
    parser.add_argument("--model", default="all-MiniLM-L6-v2", help="SentenceTransformer model")
    parser.add_argument("--log", default="docs/examples/divergence_log.json", help="Path to divergence log")
    parser.add_argument("--no-plot", action="store_true", help="Skip heatmap display")
    args = parser.parse_args()

    model = SentenceTransformer(args.model)
    labels = [Path(p).stem for p in args.files]
    datasets = [load_interpretations(Path(p)) for p in args.files]
    embeds = [embed_groups(d, model) for d in datasets]

    n = len(embeds)
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            dist = pair_distance(embeds[i], embeds[j])
            matrix[i][j] = matrix[j][i] = dist

    save_log(labels, matrix, Path(args.log))
    print("Divergence matrix:")
    for row in matrix:
        print(" ".join(f"{v:.3f}" for v in row))

    if not args.no_plot:
        show_heatmap(labels, matrix)


if __name__ == "__main__":
    main()
