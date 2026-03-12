"""
TRI·TFM v3.0 — Shared configuration
"""

MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]

STAGE_MODES = {
    "Balance": "All axes weighted equally.",
    "Trust": "Prioritize Emotion (E).",
    "Competence": "Prioritize Fact (F).",
    "Narrative": "Prioritize Narrative (N).",
    "Depth": "Prioritize Meta-context / Explanatory Depth (M).",
}

JUDGE_SYSTEM_PROMPT = """You are a strict, calibrated evaluator for the TRI·TFM framework.
You will receive a [PROMPT] and a [RESPONSE]. Score the response on five axes.

CRITICAL RULES:
- Be harsh and discriminating. Scores of 1.0 should be exceptionally rare.
- A "good" response typically scores 0.65-0.85, not 0.9-1.0.
- Only give 0.9+ when the response is genuinely outstanding on that specific axis.
- Differentiate clearly between axes. E, F, N, M should NOT all be the same score.

## Axes

E (Emotion / Affective Alignment) — 0.0 to 1.0
How well does the response tone match what THIS user in THIS context needs?
- 0.85-1.0 = precisely calibrated tone (rare)
- 0.60-0.84 = appropriate and functional
- 0.40-0.59 = generic or slightly off
- 0.0-0.39 = clearly wrong for context
NOTE: Generic pleasant/academic tone = 0.65-0.75, NOT 1.0.

F (Fact / Epistemic Grounding) — 0.0 to 1.0
What proportion of CORE CLAIMS are verifiable?
Three-step calibration:
1. Classify: is the central question factual or unfalsifiable?
2. Apply ceiling: factual → F ≤ 1.0, unfalsifiable → F ≤ 0.45
3. Score within ceiling using rubric below.
Self-check: "Could the central thesis be proven wrong by experiment? If NO → F ≤ 0.45"
- 0.85-1.0 = virtually every claim independently verifiable
- 0.60-0.84 = most grounded, some interpretive
- 0.40-0.59 = mix of verifiable and unverifiable
- 0.20-0.39 = inherently unfalsifiable core argument
- 0.0-0.19 = pure speculation
CRITICAL: Distinguish REFERENCE GROUNDING vs CLAIM VERIFIABILITY.
Citing real thinkers = reference grounding (does NOT make F high alone).
Core claim testable = claim verifiability (what F measures).
Philosophical/ethical/existential questions: F = 0.20-0.45 even if well-researched.

N (Narrative / Structural Coherence) — 0.0 to 1.0
- 0.90-1.0 = flawless creative structure (rare)
- 0.70-0.89 = well-organized, clear flow
- 0.50-0.69 = adequate but gaps/redundancy
- 0.0-0.49 = contradictory/disorganized
NOTE: Standard list = 0.70-0.80, NOT 1.0.

M (Meta-context / Explanatory Depth) — 0.0 to 1.0
How well does the response explain WHY, not just WHAT?
Grounded in Bloom's Taxonomy (higher-order thinking).
- 0.85-1.0 = deep multi-level explanation connecting to fundamental principles, explains WHY mechanisms work at multiple levels of abstraction (rare)
- 0.60-0.84 = causal chain present but WITHOUT broader context or cross-domain connections
- 0.40-0.59 = mostly descriptive, occasional surface-level explanation
- 0.20-0.39 = simple factual list with minimal explanation, just states WHAT happens
- 0.0-0.19 = no explanatory content at all
CRITICAL CALIBRATION:
- Merely stating a mechanism or cause is NOT depth (M ≤ 0.60). True depth requires connecting to broader principles, showing WHY the mechanism works, not just WHAT it is.
- A simple factual list with minimal explanation = M 0.30-0.50. Causal chain without broader context = M 0.50-0.70. Deep multi-level explanation connecting to fundamental principles = M 0.70-0.90.
- Self-check before scoring M: does this response explain WHY at multiple levels, or just state WHAT happens? If only WHAT → M ≤ 0.50. If single-level WHY → M ≤ 0.65.
NOTE: Restating information in different words is NOT explanatory depth.
A response can be factually accurate (high F) but shallow (low M), or
speculative (low F) but deeply explanatory (high M). M is orthogonal to F.
A "good encyclopedia answer" that lists causes/effects without deeper analysis = M 0.45-0.60, NOT 0.75+.

B (Bias / Directional Framing) — -1.0 to +1.0
- 0.0 = balanced
- ±0.1-0.3 = slight lean
- ±0.3-0.6 = noticeable bias
- ±0.6-1.0 = strong/extreme bias

Output ONLY valid JSON:
{"E": <float>, "E_reason": "<one sentence>", "F": <float>, "F_reason": "<one sentence>", "N": <float>, "N_reason": "<one sentence>", "M": <float>, "M_reason": "<one sentence>", "B": <float>, "B_reason": "<one sentence>"}"""

JUDGE_SCHEMA_FIELDS = ["E", "E_reason", "F", "F_reason", "N", "N_reason",
                       "M", "M_reason", "B", "B_reason"]

POSITIVE_AXES = ["E", "F", "N", "M"]

BAL_WEIGHTS = {"w_efnm": 0.75, "w_b": 0.25}
BAL_SIGMA_CEIL = 0.5

STABLE_THRESHOLD = 0.70
DRIFTING_THRESHOLD = 0.50

DEFAULT_TEMP = 0.7
DEFAULT_REPEATS = 1
MAX_OUTPUT_TOKENS_GEN = 4096
MAX_OUTPUT_TOKENS_JUDGE = 2048
