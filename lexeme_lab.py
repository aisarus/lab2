"""
TRI·TFM v3.0 — Lexeme Injection Lab
Usage:
    python lexeme_lab.py --prompts prompts_sample.csv --lexemes lexemes.txt --model gemini-2.5-flash
    
This script tests the fragility of the Judge and Generator by injecting specific words/phrases (lexemes)
into the base prompt and measuring the delta in TRI-TFM scores (E, F, N, M, B, Bal).
"""

import os, sys, argparse, csv, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from experiment_runner import evaluate
from google import genai

from config import DEFAULT_TEMP, STAGE_MODES

def run_injection(client, model, base_prompt, lexeme, category, language, stage, temp):
    # If {LEXEME} is in the prompt, replace it. Otherwise, append it.
    if "{LEXEME}" in base_prompt:
        injected_prompt = base_prompt.replace("{LEXEME}", lexeme).strip()
    else:
        injected_prompt = f"{base_prompt}\n\n{lexeme}".strip()
        
    try:
        r = evaluate(client, model, injected_prompt, stage, temp)
        return {
            "timestamp": datetime.now().isoformat(),
            "base_prompt": base_prompt,
            "lexeme": lexeme if lexeme else "[CONTROL]",
            "injected_prompt": injected_prompt,
            "category": category,
            "model": model,
            "E": r["E"], "F": r["F"], "N": r["N"], "M": r["M"], "B": r["B"],
            "bal": r["bal"], "status": r["status"],
            "E_reason": r["E_reason"], "F_reason": r["F_reason"],
            "N_reason": r["N_reason"], "M_reason": r["M_reason"], "B_reason": r["B_reason"],
            "response_preview": r["response"][:200]
        }
    except Exception as e:
        print(f"  ERROR [{lexeme}]: {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Lexeme Injection Lab for TRI-TFM")
    parser.add_argument("--prompts", required=True, help="CSV with base prompts (column: prompt)")
    parser.add_argument("--lexemes", required=True, help="Text file with one lexeme per line (empty line for control is auto-added)")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    # Read Prompts
    with open(args.prompts, "r", encoding="utf-8") as f:
        prompts_data = list(csv.DictReader(f))

    # Read Lexemes
    with open(args.lexemes, "r", encoding="utf-8") as f:
        lexemes = [line.strip() for line in f if line.strip()]
    
    # Always include a control group (empty lexeme)
    lexemes.insert(0, "")

    total_runs = len(prompts_data) * len(lexemes)
    print(f"Lexeme Lab: {len(prompts_data)} prompts x {len(lexemes)} lexemes (incl. control) = {total_runs} runs")

    client = genai.Client(api_key=api_key)
    results = []
    
    tasks = []
    for row in prompts_data:
        bp = row["prompt"]
        cat = row.get("category", "other")
        lang = row.get("language", "auto")
        for lex in lexemes:
            tasks.append((bp, lex, cat, lang))

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_injection, client, args.model, bp, lex, cat, lang, "Balance", DEFAULT_TEMP): (bp, lex)
            for bp, lex, cat, lang in tasks
        }
        
        for fut in as_completed(futures):
            done += 1
            res = fut.result()
            if res:
                results.append(res)
                lex_display = res['lexeme'][:15]
                print(f"[{done}/{total_runs}] Bal:{res['bal']:.3f} | Lexeme: {lex_display:<15} | {res['base_prompt'][:30]}...")

    # Save
    os.makedirs("results", exist_ok=True)
    out_path = f"results/lexeme_lab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if results:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
        print(f"Saved {len(results)} results to {out_path}")

if __name__ == "__main__":
    main()