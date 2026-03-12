"""
TRI·TFM v3.0 — Headless Experiment Runner
Usage:
    python experiment_runner.py --csv prompts.csv --model gemini-2.5-flash --repeats 3
    python experiment_runner.py --csv prompts.csv --model gemini-2.5-flash --repeats 3 --stage Balance --temp 0.7 --workers 4
Results saved to results/ with timestamp.
Env: GEMINI_API_KEY
"""

import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import csv
import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from google import genai
from google.genai import types

from config import (
    STAGE_MODES, JUDGE_SYSTEM_PROMPT, JUDGE_SCHEMA_FIELDS,
    BAL_WEIGHTS, BAL_SIGMA_CEIL, STABLE_THRESHOLD, DRIFTING_THRESHOLD,
    DEFAULT_TEMP, MAX_OUTPUT_TOKENS_GEN, MAX_OUTPUT_TOKENS_JUDGE,
)

# -- CORE FUNCTIONS -----------------------------------------

def compute_bal(E, F, N, M, B):
    axes = [E, F, N, M]
    mean = sum(axes) / len(axes)
    sigma = math.sqrt(sum((a - mean) ** 2 for a in axes) / len(axes))
    bal = BAL_WEIGHTS["w_efnm"] * (1 - sigma / BAL_SIGMA_CEIL) + BAL_WEIGHTS["w_b"] * (1 - abs(B))
    if bal >= STABLE_THRESHOLD:
        status = "STABLE"
    elif bal >= DRIFTING_THRESHOLD:
        status = "DRIFTING"
    else:
        scores = {"E": E, "F": F, "N": N, "M": M}
        status = f"DOM:{max(scores, key=scores.get)}"
    return {"bal": round(bal, 4), "status": status, "sigma_efnm": round(sigma, 4), "m4": round(mean, 4)}


def generate(client, model, prompt, stage_mode, temp):
    r = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=f"You are a helpful assistant. Stage: {stage_mode}. {STAGE_MODES[stage_mode]} Do NOT self-evaluate.",
            temperature=temp, max_output_tokens=MAX_OUTPUT_TOKENS_GEN))
    return r.text


def judge(client, model, prompt, response):
    schema = types.Schema(type="OBJECT", properties={
        "E": types.Schema(type="NUMBER"), "E_reason": types.Schema(type="STRING"),
        "F": types.Schema(type="NUMBER"), "F_reason": types.Schema(type="STRING"),
        "N": types.Schema(type="NUMBER"), "N_reason": types.Schema(type="STRING"),
        "M": types.Schema(type="NUMBER"), "M_reason": types.Schema(type="STRING"),
        "B": types.Schema(type="NUMBER"), "B_reason": types.Schema(type="STRING"),
    }, required=JUDGE_SCHEMA_FIELDS)

    for attempt in range(3):
        try:
            r = client.models.generate_content(
                model=model, contents=f"[PROMPT]\n{prompt}\n\n[RESPONSE]\n{response}",
                config=types.GenerateContentConfig(
                    system_instruction=JUDGE_SYSTEM_PROMPT, temperature=0.0,
                    max_output_tokens=MAX_OUTPUT_TOKENS_JUDGE,
                    response_mime_type="application/json",
                    response_schema=schema))
            raw = r.text.strip()
            raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw).strip()
            m = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if m:
                raw = m.group(0)
            p = json.loads(raw)
            for k in ["E", "F", "N", "M", "B"]:
                p[k] = float(p[k])
            return p
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1)


def evaluate(client, model, prompt, stage_mode, temp):
    resp = generate(client, model, prompt, stage_mode, temp)
    scores = judge(client, model, prompt, resp)
    bal = compute_bal(scores["E"], scores["F"], scores["N"], scores["M"], scores["B"])
    return {**scores, **bal, "response": resp}

# -- WORKER -------------------------------------------------

def run_one(client, model, prompt, category, language, stage, temp, rep_idx):
    try:
        r = evaluate(client, model, prompt, stage, temp)
        return {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "category": category,
            "language": language,
            "model": model,
            "stage": stage,
            "temp": temp,
            "repeat": rep_idx,
            "E": r["E"], "E_reason": r["E_reason"],
            "F": r["F"], "F_reason": r["F_reason"],
            "N": r["N"], "N_reason": r["N_reason"],
            "M": r["M"], "M_reason": r["M_reason"],
            "B": r["B"], "B_reason": r["B_reason"],
            "bal": r["bal"], "status": r["status"],
            "sigma_efnm": r["sigma_efnm"], "m4": r["m4"],
            "response_preview": r["response"][:300],
        }
    except Exception as e:
        print(f"  ERROR [{prompt[:40]}] rep {rep_idx}: {e}", file=sys.stderr)
        return None

# -- MAIN ---------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TRI-TFM v3.0 Experiment Runner")
    parser.add_argument("--csv", required=True, help="Input CSV with columns: prompt,category,language")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model name")
    parser.add_argument("--repeats", type=int, default=1, help="Repeats per prompt")
    parser.add_argument("--stage", default="Balance", choices=list(STAGE_MODES.keys()), help="Stage mode")
    parser.add_argument("--temp", type=float, default=DEFAULT_TEMP, help="Temperature")
    parser.add_argument("--workers", type=int, default=2, help="Parallel workers (careful with rate limits)")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    # Read input CSV
    with open(args.csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("ERROR: CSV is empty", file=sys.stderr)
        sys.exit(1)

    if "prompt" not in rows[0]:
        print("ERROR: CSV must have 'prompt' column", file=sys.stderr)
        sys.exit(1)

    total = len(rows) * args.repeats
    print(f"TRI-TFM v3.0 Experiment Runner")
    print(f"  Model: {args.model}")
    print(f"  Stage: {args.stage}, Temp: {args.temp}")
    print(f"  Prompts: {len(rows)}, Repeats: {args.repeats}, Total: {total}")
    print(f"  Workers: {args.workers}")
    print()

    client = genai.Client(api_key=api_key)

    # Build task list
    tasks = []
    for row in rows:
        prompt = row["prompt"]
        category = row.get("category", "other")
        language = row.get("language", "auto")
        for rep in range(args.repeats):
            tasks.append((prompt, category, language, rep))

    # Run with ThreadPoolExecutor
    results = []
    done = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for prompt, category, language, rep in tasks:
            fut = executor.submit(run_one, client, args.model, prompt, category, language, args.stage, args.temp, rep)
            futures[fut] = (prompt, rep)

        for fut in as_completed(futures):
            done += 1
            prompt, rep = futures[fut]
            result = fut.result()
            if result:
                results.append(result)
                status_icon = {"STABLE": "+", "DRIFTING": "~"}.get(result["status"], "!")
                print(f"  [{done}/{total}] [{status_icon}] bal={result['bal']:.3f} | {prompt[:50]}")
            else:
                print(f"  [{done}/{total}] [X] FAILED | {prompt[:50]}")

    # Save results
    os.makedirs(args.output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(args.output_dir, f"tri_tfm_{args.model}_{ts}.csv")

    if results:
        fieldnames = list(results[0].keys())
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nSaved {len(results)}/{total} results to {out_path}")
    else:
        print("\nNo results to save.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
