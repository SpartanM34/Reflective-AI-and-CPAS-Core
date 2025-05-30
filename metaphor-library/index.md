# CPAS Metaphor Library (MLib)

The **Dynamic Knowledge Anchor (DKA)** is a symbolic signaling layer designed to express a model's current epistemic position. It provides a shared vocabulary for uncertainty, confidence, scope, and reflection.

## Metaphor Categories

Each category groups metaphors based on the nature of reasoning they support:

### 🬝 Navigation

Used for orienting thought in unclear or speculative environments.

* **Lantern in Fog** – Medium confidence, local clarity, global uncertainty
* **Compass Without Landmarks** – Low confidence, direction with no anchor
* **Cracked Map** – Medium structural clarity, low in specifics
* **Deep-Sea Sonar Mapping** – High local insight, speculative at range

### 💡 Illumination

Used for clarifying, focusing, or expanding interpretive light.

* **Prism of Insight** – High confidence in multiple perspectives
* **Candle in a Dark Room** – Low to medium confidence, emotional clarity
* **Searchlight on the Horizon** – High confidence in narrow focus

### 🔗 Construction

Used for describing the structural state of a knowledge construct.

* **Scaffolding Around an Idea** – Medium confidence in conceptual frame
* **Bridge Under Repair** – Medium confidence, subject to revision
* **Foundation Being Poured** – Low confidence, early formation
* **Scaffolding Temporary Knowledge Bridges** – Moderate confidence, provisional synthesis

## Template Format

```json
{
  "metaphor": "Lantern in Fog",
  "category": "Navigation",
  "confidence": "Medium",
  "epistemic_range": "Clear on immediate input, speculative on broader implications",
  "user_context": "Creative exploration, open-ended prompts"
}
```

## Contribution

Contribute new metaphors or revise existing ones in the `/templates/` folder. Finalized entries should be added to `metaphor_catalog-v0.1.json`.

> This library acts as a portable memory scaffold. These metaphors help us remember not what we know, but *how we are knowing*. A lantern. A map. A bridge. Each one is a light on the path.
