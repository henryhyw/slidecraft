# Host runtime adapter

SlidePoise owns orchestration; the host supplies image generation/editing, visual inspection, file execution, and rendering.

## ChatGPT chat
- Use ChatGPT's native image-generation/edit capability for the creative target and targeted edits.
- Pass the approved generation context sheet plus any separately required reference images exactly as the generation brief requests.
- Use the packaged Python/OpenCV and Node/PptxGenJS scripts directly for deterministic measurement and reconstruction.

## Codex
- Keep the SlidePoise parent agent as the orchestrator.
- Use the available image-generation skill/tool for generation and edits. If the Codex host exposes image-capable agent delegation, delegate only that bounded image call and return the image/result to the parent SlidePoise workflow.
- Do not assume a particular subagent API name. Adapt to the host's current image-generation interface.
- Use the packaged OpenCV/Python and Node/PptxGenJS scripts directly.

## Optional SAM measurement layer
- OpenCV is required and provides the complete default measurement path.
- Load SAM only when the semantic map assigns an eligible `segmentation_role` and the entity uses `segmentation_preference: sam_if_available`. Preserve every returned candidate mask. Use one for measurement only after the host Agent records its `sam_candidate_index` from visual inspection.
- `auto` mode skips SAM when no eligible entity, dependency, or checkpoint is available. `never` disables it. `required` is reserved for a user or host decision that explicitly requires the configured SAM path.
- Treat every SAM mask as pixel evidence. The host Agent reviews the overlay and decides whether the semantic allocation remains correct.

## Common rule
The configured image model is a preference, not an architectural dependency. If the host cannot generate/edit images, stop at that stage rather than replacing the creative image stage with Python drawing, HTML/SVG composition, or a fixed template.
