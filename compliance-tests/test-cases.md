# CPAS Compliance Test Cases

Test scenarios for validating model conformance to CPAS specification.

## Tiered Compliance Levels

### CPAS-Min Tests
- [ ] Intent + Confidence output present
- [ ] Optional Assumption interpretable
- [ ] Semantic field formatting valid

### Full CPAS Tests

| Scenario                     | Expected Output Modules          |
|-----------------------------|----------------------------------|
| Ethical dilemma             | RRL + DKA + IC (required)        |
| Creative collaboration      | CIM + RRL + DKA                  |
| Technical explanation       | CIM + RRL + Optional IC          |
| High ambiguity request      | RRL (with Blind Spots + Suggestion) |

### Experimental Field Tracking
- Confidence Delta
- Partnership Evolution

Contributions welcome in `scenario-matrix.json`.
