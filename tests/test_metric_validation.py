import pytest
pytest.importorskip("spacy")

import spacy
from tools import baseline_metrics as bm

nlp = spacy.blank("en")

TEXTS = [
    "alpha beta gamma",
    "delta epsilon zeta",
    "eta theta iota",
    "kappa lambda mu",
    "nu xi omicron",
]


def test_reliability_scores():
    stats = bm.metric_correlations(TEXTS, nlp, iterations=3)
    assert all(-1.0 <= v <= 1.0 for v in stats.values())
    reli = bm.reliability_score(bm.lexical_diversity, TEXTS, nlp, iterations=3)
    assert -1.0 <= reli <= 1.0
