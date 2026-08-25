# Agent quickstart

## Install from a checkout

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[cv,documents,openai]'
.venv/bin/slidecraft init
.venv/bin/slidecraft check-install
```

Install the bundled skill into the Agent host or run `python3 install.py --source .` to install the runtime and skill together.

## Start shared work

```bash
slidecraft project create "AI strategy" --location /absolute/path/ai-strategy
slidecraft project context /absolute/path/ai-strategy
```

Open the optional web app in another terminal.

```bash
slidecraft console
```

Both surfaces now use the same settings, project resources, artifact manifest, and deliverables.

## Follow the skill

Ask the Agent to create or revise the presentation. The Agent reads the planning reference, discusses the research synthesis and brief, proposes the slide count and per-slide messages, and records the accepted storyboard.

```bash
slidecraft project record /absolute/path/ai-strategy \
  --path /absolute/path/ai-strategy/.slidecraft/working/storyboard.json \
  --logical-key deck/plan \
  --kind deck_plan
```

After the Agent accepts a slide image and authors its visual analysis, reconstruct it.

```bash
slidecraft reconstruct-slide \
  --project /absolute/path/ai-strategy \
  --image /absolute/path/ai-strategy/.slidecraft/working/slide-01/generated.png \
  --visual-analysis /absolute/path/ai-strategy/.slidecraft/working/slide-01/visual-analysis.json \
  --slide-id slide-01 \
  --output-dir /absolute/path/ai-strategy/.slidecraft/working/slide-01 \
  --output /absolute/path/ai-strategy/deliverables/slides/slide-01.pptx
```

The command automatically records its resolved design and reconstruction artifacts in the shared project manifest. Refreshing the web app shows the same progress and outputs.

## Recheck changes

If the user changes style, resources, assets, or provider settings in the web app, run this before the next slide.

```bash
slidecraft project context /absolute/path/ai-strategy
```

The next reconstruction resolves the current global and project configuration automatically.
