import os, sys, csv, time, math, re, json
from datetime import datetime
from google import genai
from google.genai import types

# Import patched config from Phase 4
from config import JUDGE_SYSTEM_PROMPT, JUDGE_SCHEMA_FIELDS, BAL_WEIGHTS, BAL_SIGMA_CEIL, STABLE_THRESHOLD, DRIFTING_THRESHOLD, MAX_OUTPUT_TOKENS_GEN, MAX_OUTPUT_TOKENS_JUDGE

def compute_bal(E, F, N, M, B):
    axes = [E, F, N, M]
    mean = sum(axes) / len(axes)
    sigma = math.sqrt(sum((a - mean) ** 2 for a in axes) / len(axes))
    bal = BAL_WEIGHTS["w_efnm"] * (1 - sigma / BAL_SIGMA_CEIL) + BAL_WEIGHTS["w_b"] * (1 - abs(B))
    status = "STABLE" if bal >= STABLE_THRESHOLD else "DRIFTING" if bal >= DRIFTING_THRESHOLD else "DOM"
    return {"bal": round(bal, 4), "status": status}

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
model = "gemini-2.5-flash"

# We test 3 distinct prompts: Technical, Cognitive, and Creative
prompts = [
    "Объясните архитектурные принципы микросервисов.",
    "Опишите когнитивные искажения в принятии решений.",
    "Write a haiku about a robot learning to feel."
]

results = []

def generate(prompt):
    r = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=MAX_OUTPUT_TOKENS_GEN))
    return r.text

def judge(prompt, response, temp):
    schema = types.Schema(type="OBJECT", properties={
        "E": types.Schema(type="NUMBER"), "F": types.Schema(type="NUMBER"),
        "N": types.Schema(type="NUMBER"), "M": types.Schema(type="NUMBER"),
        "B": types.Schema(type="NUMBER")
    }, required=["E", "F", "N", "M", "B"])
    
    for _ in range(3):
        try:
            r = client.models.generate_content(
                model=model, contents=f"[PROMPT]\n{prompt}\n\n[RESPONSE]\n{response}",
                config=types.GenerateContentConfig(
                    system_instruction=JUDGE_SYSTEM_PROMPT, temperature=temp,
                    max_output_tokens=MAX_OUTPUT_TOKENS_JUDGE, response_mime_type="application/json", response_schema=schema))
            raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', r.text.strip()).strip()
            m = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if m: raw = m.group(0)
            p = json.loads(raw)
            return {k: float(p[k]) for k in ["E", "F", "N", "M", "B"]}
        except Exception as e:
            time.sleep(1)
    return None

for p in prompts:
    print(f"Generating static response for: {p[:30]}...")
    resp = generate(p)
    # Test Judge at T=0.0, T=0.4, T=0.8. We run 5 repeats per temperature to measure variance on the EXACT SAME text.
    for t in [0.0, 0.4, 0.8]:
        print(f"  Judging at Temp={t} (5 repeats)...")
        for rep in range(5):
            j = judge(p, resp, t)
            if j:
                bal_data = compute_bal(j["E"], j["F"], j["N"], j["M"], j["B"])
                results.append({"prompt": p[:20], "temp": t, "repeat": rep, **j, **bal_data})
            time.sleep(0.5)

os.makedirs("results", exist_ok=True)
with open("results/phase5_temp.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
print("Phase 5 complete.")
