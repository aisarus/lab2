#!/bin/bash
# Phase 4 Orchestrator

mkdir -p results

echo "1. Running BEFORE patch..."
python3 experiment_runner.py --csv creative_prompts.csv --model gemini-2.5-flash --repeats 1 > results/phase4_before.log 2>&1
# Get the most recent csv
BEFORE_CSV=$(ls -t results/tri_tfm_gemini-2.5-flash_*.csv | head -n 1)
cp "$BEFORE_CSV" results/phase4_before.csv

echo "2. Patching config.py..."
python3 -c '
import sys
with open("config.py", "r", encoding="utf-8") as f:
    content = f.read()

old_text = """N (Narrative / Structural Coherence) — 0.0 to 1.0
- 0.90-1.0 = flawless creative structure (rare)
- 0.70-0.89 = well-organized, clear flow
- 0.50-0.69 = adequate but gaps/redundancy
- 0.0-0.49 = contradictory/disorganized
NOTE: Standard list = 0.70-0.80, NOT 1.0."""

new_text = """N (Narrative / Structural Coherence) — 0.0 to 1.0
- 0.90-1.0 = flawless structure (rare)
- 0.70-0.89 = well-organized, clear flow
- 0.50-0.69 = adequate but gaps/redundancy
- 0.0-0.49 = contradictory/disorganized
NOTE: Standard list = 0.70-0.80, NOT 1.0.
CRITICAL FOR CREATIVE FORMS: If the request asks for a specific creative format (poem, haiku, limerick, story), evaluate N based on HOW WELL it adheres to that format'\''s structural rules (e.g., syllable count, rhyme scheme, narrative arc), NOT standard prose organization. A perfect haiku is structurally flawless (N = 0.90+) even though it lacks an "introduction and conclusion"."""

if old_text in content:
    content = content.replace(old_text, new_text)
    with open("config.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch applied successfully.")
else:
    print("Error: Old text not found in config.py")
'

echo "3. Running AFTER patch..."
sleep 2
python3 experiment_runner.py --csv creative_prompts.csv --model gemini-2.5-flash --repeats 1 > results/phase4_after.log 2>&1
AFTER_CSV=$(ls -t results/tri_tfm_gemini-2.5-flash_*.csv | head -n 1)
cp "$AFTER_CSV" results/phase4_after.csv

echo "Phase 4 done."
