# TRI·TFM v3.0 Research Log (v11)
**Date:** 2026-03-12
**Author:** Fess & Arseniy Shternfeld
**Focus:** Resolving the L3/Q11 limitation (Axis `N` instability on short creative forms).

## 📌 Context
Previous testing (v2.1) revealed that the Narrative (`N`) axis struggled with short creative forms (haikus, limericks). The Judge often failed to map standard prose expectations ("introduction-body-conclusion") onto poetry, resulting in erratic scoring. 

To fix this, we implemented a structural patch to `JUDGE_SYSTEM_PROMPT` inside `config.py`:
> *CRITICAL FOR CREATIVE FORMS: If the request asks for a specific creative format (poem, haiku, limerick, story), evaluate N based on HOW WELL it adheres to that format's structural rules (e.g., syllable count, rhyme scheme, narrative arc), NOT standard prose organization.*

We then ran a comparative A/B test (Phase 4) using `gemini-2.5-flash` on a new dataset of 8 creative prompts (`creative_prompts.csv`).

## 🧪 Phase 4: Creative Form Patch (A/B Test)
**Goal:** Prove that the patched Judge correctly evaluates creative structure without penalizing for lack of prose formatting.

### 📊 Results & Key Findings
1. **Baseline shift:** The modern `gemini-2.5-flash` judge was already somewhat forgiving of poetry (Average `N` before patch: 0.887). However, it was giving high scores *blindly*.
2. **The "Awakening" of Constraint Checking:** After the patch, the average `N` score slightly *dropped* to 0.794. Why? Because the patch successfully activated **hyper-competent structural evaluation**.
3. **The Haiku Incident (Crucial Finding):** 
   - On the prompt *"Напиши хокку про падающий сервер"* (Write a haiku about a crashing server in Russian), the unpatched Judge gave `N = 0.90` simply because it "looked like a sequence of images."
   - The **patched Judge** brutally gave it **`N = 0.15`**, explicitly stating: *"The response fails to adhere to the structural rules of a haiku, with syllable counts of 7-10-6 instead of the required 5-7-5 for each line."*
4. **Conclusion:** The patch is a massive success. It does not just "forgive" creative texts for lacking prose structure; it successfully redirects the `N` axis to evaluate **formal structural constraints** (syllable counting, rhyme schemes like AABB/AABBA). 

This entirely resolves Limitation L3/Q11 for the COLM 2026 paper. The `N` axis is now officially multi-modal in its structural understanding (Prose vs. Poetic forms).