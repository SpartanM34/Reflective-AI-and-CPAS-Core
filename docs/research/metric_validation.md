# Metric Validation Methods

This document summarizes how lexical diversity, symbolic density, and divergence space metrics are validated in CPAS-Core.

## Sample Size
The validation suite uses 13 metaphor entries drawn from the DKA-E library along with README and index text. Random subsets of these texts are sampled during each iteration.

## Statistical Methods
- **Correlation tests:** Pearson correlation coefficients are computed across five random subsets to examine interdependence of metrics.
- **Reliability:** Split-half reliability is estimated by shuffling texts and comparing metric scores between halves.

## Significance Thresholds
Correlations exceeding |0.5| are considered notable. Reliability scores above 0.7 indicate acceptable stability.
