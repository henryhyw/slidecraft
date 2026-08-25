# Planning a new deck

Use this contract when creating or substantially replanning a deck.

## Agent-authored brief

Read every source before preparing the brief. Preserve each source path and author concise evidence records with stable locators.

```json
{
  "objective": "What the presentation must accomplish",
  "audience": {
    "description": "Primary audience",
    "decision_context": "What they should decide, understand, or do"
  },
  "desired_outcome": "Result of a successful presentation",
  "materials": [
    {
      "material_id": "SOURCE_001",
      "modality": "document",
      "path": "/absolute/path/to/source"
    }
  ],
  "source_atoms": [
    {
      "atom_id": "FACT_001",
      "material_id": "SOURCE_001",
      "locator": "page:4",
      "modality": "structured_text",
      "value": {"claim": "Source-grounded fact or exact content"},
      "authority": "authoritative",
      "required_usage": true,
      "provenance": "agent_source_analysis"
    }
  ],
  "visual_assets": [
    {
      "asset_id": "PROJECT_ABC123",
      "description": "A screenshot showing the source application with a nested table parsing result.",
      "semantic_role": "nested table extraction example",
      "usage_policy": "available"
    }
  ],
  "constraints": [
    {
      "text": "A classified instruction",
      "strength": "hard",
      "target": "deck",
      "classification_source": "agent_reasoning"
    }
  ]
}
```

Use `supporting_evidence` or `intent_evidence` when appropriate. Set `required_usage` only when the Agent decides that the fact must appear. Record exclusions with reasons when material is intentionally omitted. Slidecraft verifies references and required allocation. It does not decide what the sources mean or whether the evidence is sufficient.

## Collaborative planning proposal

Before slide generation, show the user one concise proposal containing these items.

- Primary audience and consequential question or decision
- Objective, desired outcome, and governing answer
- Material research findings and their implications
- Recommended slide count and storyline phases
- One conclusion-led message for every slide
- Principal evidence or source allocation for every slide
- Placement of required topics and assets
- Material assumptions and exclusions

Invite correction in collaborative work. Continue without waiting when the user explicitly delegates uninterrupted execution.

## Plan quality

The deck should feel authored for this audience and evidence set. Its message chain should recover the full argument. Each content slide should make a distinct claim, carry enough evidence for the configured density, and create a reason for the next slide. Consolidate overlapping claims. Integrate technical architecture, costs, infrastructure, models, and other required topics where they prove a larger point. Avoid organizing the deck around internal modules unless that is the audience's actual question.
