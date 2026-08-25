# Editorial planning

Use this workflow to discover a presentation worth building. Save the resulting Agent-authored artifacts in the shared project folder for discussion, continuation, and web-app display.

## Build a project interpretation

Read the request and sources before allocating slides. Synthesize the project as a system.

```json
{
  "project_purpose": "What the project enables",
  "distinctive_mechanism": "What is unusual or consequential about how it works",
  "central_tension": "The competing needs or constraints it resolves",
  "demonstrated_evidence": ["Specific facts, artifacts, results, or examples"],
  "boundaries": ["What is incomplete, optional, or outside the current claim"],
  "audience_relevance": ["Why the evidence matters to the likely audience"]
}
```

Synthesize beyond source summaries and identify the center of gravity that makes the project interesting.

## Define the audience transformation

Describe the movement in understanding the presentation should create.

```json
{
  "audience": "Who will use the presentation",
  "starting_view": "What they probably believe or understand now",
  "desired_view": "What they should understand afterward",
  "decision_or_action": "What the presentation should enable",
  "questions": ["Questions that naturally arise during the journey"],
  "proof_requirements": ["Evidence needed to earn confidence"],
  "likely_resistance": ["Sources of confusion or skepticism"]
}
```

Ask questions whose answers could materially change this transformation. Infer visual direction separately from the audience decision.

## Use research deliberately

Classify each useful research finding by its role.

```json
{
  "finding": "Source-grounded research result",
  "role": "visible_evidence | background_context | design_guidance | claim_verification",
  "implication": "How it changes the deck",
  "source": "Stable source locator"
}
```

Reserve slide space for visible evidence. Keep research that improves the Agent's understanding in background context or design guidance.

## Compare narrative hypotheses

Create two or three genuinely different ways to move the audience from its starting view to the desired view. Vary the governing answer, opening move, sequence of realizations, use of evidence, or ending.

For each option, state:

- Governing answer
- Opening move
- Sequence of audience realizations
- Role of evidence or demonstration
- Ending
- Main strength and risk for this audience

Choose the option that makes the project easiest to understand and hardest to misunderstand. Select a market argument, product journey, mechanism explanation, demonstration-led story, or another structure according to the audience transformation.

## Author the storyboard

Allocate slides only after choosing the narrative. Each slide is one necessary movement in the audience's understanding.

```json
{
  "recommended_slide_count": 0,
  "governing_answer": "The complete argument in one sentence",
  "phases": [
    {
      "purpose": "What this phase changes in the audience's understanding",
      "slides": [
        {
          "slide_id": "slide-01",
          "audience_question": "The question arising at this moment",
          "message": "The project-specific answer",
          "evidence": ["Facts, examples, or demonstrations"],
          "consequence": "Why the answer matters",
          "visual_job": "The relationship the visual must make clear",
          "transition": "Why the next slide follows"
        }
      ]
    }
  ],
  "assumptions": [],
  "exclusions": []
}
```

Derive message titles from these communication contracts. Make every message specific enough to identify this project and its consequence.

Treat required topics as evidence obligations. Integrate them where they prove feasibility, economics, risk, mechanism, or implications. Give a topic a dedicated slide when that movement is necessary to the audience journey.

## Review the proposed deck

For collaborative work, show the user:

- Research and source synthesis
- Audience transformation
- Selected narrative and rationale
- Recommended length
- One message and evidence allocation per slide
- Assumptions and exclusions

Invite correction before image generation. When the user delegates uninterrupted execution, perform the same reasoning and continue.

Before generation, read the slide messages as one sequence. They should recover the full project-specific argument. Test each slide's contribution to the audience journey and consolidate pages whose purpose overlaps.
