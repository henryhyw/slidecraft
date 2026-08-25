# Configurable Guidance Profiles

## Purpose

A guidance profile defines how a type of deck should reason and communicate. It is independent from the deck design system, resource libraries, density configuration, and reconstruction engine.

```text
Guidance profile
  how to reason and communicate

Deck design configuration
  how to look and how dense to be

Resource libraries
  what reusable material exists

Pipeline mechanics
  how to generate, understand, reconstruct, and validate
```

The same consulting guidance can operate with different visual brands. The same deck design system can support consulting, academic, educational, product, or investor guidance.

## Selection

The current deck design configuration selects:

```json
{
  "guidance_profile": {
    "profile_id": "consulting",
    "path": "src/slidecraft/guidance_profiles/consulting.json",
    "inheritance_root": "src/slidecraft/guidance_profiles"
  }
}
```

Future profiles can include `academic_explanatory`, `product_strategy`, `investor_pitch`, and `training_material` while preserving the construction contracts.

## Inheritance

[`base.json`](../src/slidecraft/guidance_profiles/base.json) contains communication-quality and design-freedom principles shared by all profiles.

[`consulting.json`](../src/slidecraft/guidance_profiles/consulting.json) extends the base profile. Recursive dictionaries merge. Lists append with de-duplication. The resolved profile records its lineage and merge policy.

The loader is [`guidance_profiles.py`](../src/slidecraft/orchestration/guidance_profiles.py). The schema is [`guidance_profile.schema.json`](../schemas/guidance_profile.schema.json).

## Consulting guidance

The consulting profile covers these concerns.

- Audience question and decision context
- Governing answer where evidence supports one
- Argument spine and message chain
- Slide role in the deck argument
- Dominant claim and evidence bindings
- Claims, evidence, context, qualifications, and recommendations
- Semantic relationships and hierarchy
- Conclusion-led writing where appropriate
- Consulting communication diagnostics and anti-patterns
- Visual obligations that express required meaning while leaving layout open

It includes a powerful deck diagnostic. Reading only the slide messages should recover the core argument.

## Visual obligations

Visual obligations describe what the generated design must make apparent while preserving visual freedom.

```json
{
  "visual_obligations": [
    "The two analyses are complementary peers and not sequential substeps.",
    "Both forms of understanding inform both reconstruction routes.",
    "The editable PPTX is the outcome of the entire architecture."
  ]
}
```

The image model chooses how to express these obligations. Coordinates, component counts, page topology, and specific chart or diagram forms remain composition decisions.

## Pipeline influence

### Deck planning

The profile supplies reasoning principles, diagnostics, optional storyline archetypes, recommended semantic outputs, writing policy, and deck review questions.

Density remains a separate deck design configuration resolved before storyline decomposition.

### Slide semantic planning

The semantic planner receives exact content, constraints, intake evidence, and the resolved guidance profile. Consulting plans can include audience question, dominant claim, role in the deck argument, argument structure, evidence bindings, and visual obligations.

### Image generation

Prompt assembly includes the selected profile's slide reasoning, visual communication, writing, design freedom, and the slide's visual obligations. These instructions guide communication quality while preserving composition freedom.

### Review

The reviewer applies profile questions and anti-patterns when judging communication quality. Deck design configuration remains authoritative for typography, color, dimensions, and visual conventions.

### Reconstruction handoff

The resolved profile is preserved for Slide understanding, Editable reconstruction, reporting, and cross-slide QA. Reconstruction continues to follow the ordinary semantic and geometric contracts.

## Ownership boundaries

Other workflow layers own these concerns.

- Fonts and colors
- Canvas, title anchor, header, and footer
- Density profile
- Visual Reference Library
- Icon Library
- Known Component Library
- User assets
- OpenCV and segmentation configuration
- PowerPoint object routes
- Geometry fitting
- Native rendering

Those remain configurable through their dedicated layers.

## Profile authoring rules

1. Express communication principles and diagnostics instead of rigid layouts.
2. Include explicit design-freedom safeguards.
3. Avoid encoding brand colors, fonts, and deck-layout geometry.
4. Avoid encoding library item IDs.
5. Avoid universal visual mappings such as sequence always means process diagram.
6. Keep profile-specific semantic output fields optional when they are not relevant.
7. Version every profile and preserve the resolved snapshot for each run.
