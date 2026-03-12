# TRI·TFM v3.0 — Project Context

**Author:** Arseny Perel
**Goal:** Research paper for COLM/NeurIPS/EMNLP 2026
**Topic:** LLM response evaluation framework with 5 axes (E/F/N/M/B) + Balance score

## Project Structure

```
tri_tfm_v3/
├── config.py                  # Shared configuration: axes, rubric, weights, thresholds
├── experiment_runner.py       # Headless experiment runner (generate + judge)
├── analyzer.py                # Results analyzer (stats, plots, reports)
├── app.py                     # Streamlit UI (interactive mode)
├── scripts/
│   └── judge_only.py          # Judge-only evaluator (no generation step)
├── prompts/
│   ├── full_100.csv           # 100 bilingual prompts for final validation (NOT YET RUN)
│   └── m_axis_fixed.csv       # 5 topics × shallow/deep fixed responses for M validation
├── prompts_p1_domain.csv      # 10 EN prompts (5 factual + 3 philosophical + 2 ethical)
├── prompts_p2_maxis.csv       # 20 prompts (10 shallow/deep pairs) for M-axis testing
├── domain_prompts_p1.csv      # 10 RU domain prompts (med, law, fin, edu, marketing, ...)
├── docs/
│   └── paper_section3_method.md  # Draft of Section 3 (Method) for paper
├── reports/                   # Organized by experiment
│   ├── P1_domain_generalization/
│   ├── P2_m_axis_validation/     # v1: baseline (3/10 PASS)
│   ├── P2v2_m_axis_revalidation/ # v2: tightened rubric (3/10 PASS)
│   ├── P2v3_fixed_responses/     # v3: judge-only, fixed responses (5/5 PASS)
│   ├── P2v4_longer_output/       # v4: gen=4096 (7/10 PASS)
│   ├── P3_sensitivity_analysis/
│   ├── P4_literature_review/
│   └── P5_cross_model/
├── results/                   # Raw CSV data from experiments
├── requirements.txt
├── .env                       # GEMINI_API_KEY (gitignored)
├── HEARTBEAT.md
├── RESEARCH_PROTOCOL.md
└── USER.md
```

## Experiment Status

| ID | Experiment | Status | Key Result |
|----|-----------|--------|------------|
| P1 | Domain Generalization | **PASS** | F-hierarchy holds in 5 domains, delta_F 0.45-0.53 |
| P2v1 | M-Axis Validation (baseline) | FAIL | 3/10 PASS, mean delta_M=0.073, 14/60 JSON failures |
| P2v2 | M-Axis (tightened rubric) | FAIL | 3/10 PASS, mean delta_M=0.067, 1/60 JSON failures |
| P2v3 | M-Axis (fixed responses) | **PASS** | 5/5 PASS, mean delta_M=0.384, rubric validated |
| P2v4 | M-Axis (gen=4096) | **PASS** | 7/10 PASS, mean delta_M=0.263 |
| P3 | Sensitivity Analysis | **PASS** | Spearman rho > 0.97 all weight configs |
| P4 | Literature Review | **DONE** | Key works 2025-2026 catalogued |
| P5 | Cross-Model (Flash vs Pro) | **PASS** | F r=0.963, bal r=0.942 |

## Known Issues & Solutions

| Issue | Status | Solution |
|-------|--------|----------|
| M-rubric too lenient | **FIXED** | Tightened rubric with self-checks and calibration anchors |
| JSON parse failures (23%) | **FIXED** | MAX_OUTPUT_TOKENS_JUDGE 1024→2048 (now 1-2% failures) |
| Deep response truncation | **FIXED** | MAX_OUTPUT_TOKENS_GEN 2048→4096 |
| Generator compensation (shallow M=0.75+) | **KNOWN** | Inherent to powerful LLMs; documented as limitation |
| Earthquakes/CRISPR shallow M still high | **KNOWN** | 3/10 residual FAIL from generator compensation |

## Current Priorities

1. **Run full_100.csv experiment** — final validation with 100 bilingual prompts
2. **Expand paper draft** — Sections 1 (Intro), 2 (Related Work), 4 (Experiments), 5 (Discussion)
3. **Inter-annotator agreement** — compare LLM judge vs human scores on subset
4. **Additional models** — test with Claude, GPT-4o as generators
5. **LaTeX conversion** — convert markdown drafts to conference template

## Key Configuration (config.py)

- **Axes:** E (Emotion), F (Fact), N (Narrative), M (Meta-context), B (Bias)
- **Balance:** w_EFNM=0.75, w_B=0.25, sigma_ceil=0.5
- **Thresholds:** STABLE≥0.70, DRIFTING≥0.50
- **Tokens:** GEN=4096, JUDGE=2048
- **Temp:** Generation=0.7, Judge=0.0

## Commands

```bash
# Run experiment
GEMINI_API_KEY="key" python experiment_runner.py --csv prompts/full_100.csv --model gemini-2.5-flash --repeats 2

# Judge-only (fixed responses)
GEMINI_API_KEY="key" python scripts/judge_only.py --csv prompts/m_axis_fixed.csv --model gemini-2.5-flash --repeats 5

# Analyze results
python analyzer.py --csv results/FILENAME.csv

# Streamlit UI
GEMINI_API_KEY="key" streamlit run app.py
```

## Style Notes

- Reports: Russian
- Paper: Academic English
- Code: Python 3.11+, google-genai SDK
- API: Gemini (gemini-2.5-flash, gemini-2.5-pro)
