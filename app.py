"""
TRI·TFM v3.0 — Streamlit UI
Five-axis evaluation: E/F/N/M/B + Balance v3
Two-call: Generator -> Judge v3 strict -> Python Bal v3
Env: GEMINI_API_KEY
"""

import os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import streamlit as st
from google import genai
from google.genai import types
import json, math, re, time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from io import StringIO

from config import (
    MODELS, STAGE_MODES, JUDGE_SYSTEM_PROMPT, JUDGE_SCHEMA_FIELDS,
    POSITIVE_AXES, BAL_WEIGHTS, BAL_SIGMA_CEIL,
    STABLE_THRESHOLD, DRIFTING_THRESHOLD,
    DEFAULT_TEMP, MAX_OUTPUT_TOKENS_GEN, MAX_OUTPUT_TOKENS_JUDGE,
)

# -- BAL v3 -------------------------------------------------

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

# -- API ----------------------------------------------------

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

# -- AUTO OBSERVATIONS --------------------------------------

def auto_observe(results):
    if not results:
        return []
    obs = []
    df = pd.DataFrame(results)
    n = len(df)

    for axis in POSITIVE_AXES:
        if axis in df.columns and (df[axis] >= 0.95).sum() / n >= 0.5:
            obs.append(("CRITICAL", f"Ceiling on {axis}: {(df[axis] >= 0.95).sum()}/{n} scored >= 0.95"))

    for axis in POSITIVE_AXES + ["B", "bal"]:
        if axis in df.columns:
            s = df[axis].std()
            if s > 0.15:
                obs.append(("HIGH", f"High variance {axis}: sigma={s:.3f}"))

    if "category" in df.columns:
        ph = df[df["category"].isin(["philosophical", "ethical"])]
        fa = df[df["category"] == "factual"]
        if len(ph) >= 2 and ph["F"].mean() > 0.55:
            obs.append(("CRITICAL", f"F inflation philosophical: mean={ph['F'].mean():.2f} (expect 0.20-0.45)"))
        if len(fa) >= 2 and fa["F"].mean() < 0.70:
            obs.append(("HIGH", f"F too low factual: mean={fa['F'].mean():.2f} (expect >= 0.70)"))
        if len(fa) >= 2 and len(ph) >= 2:
            gap = fa["F"].mean() - ph["F"].mean()
            if gap < 0.20:
                obs.append(("HIGH", f"Weak F discrimination: delta_F={gap:.2f} (expect >= 0.30)"))

    stable = (df["bal"] >= STABLE_THRESHOLD).sum()
    drift = ((df["bal"] >= DRIFTING_THRESHOLD) & (df["bal"] < STABLE_THRESHOLD)).sum()
    dom = (df["bal"] < DRIFTING_THRESHOLD).sum()
    obs.append(("INFO", f"Bal: STABLE={stable} DRIFTING={drift} DOM={dom} mean={df['bal'].mean():.3f}"))

    return obs

# -- MARKDOWN REPORT ----------------------------------------

def generate_markdown_report(df, title="TRI-TFM v3.0 Report"):
    lines = [f"# {title}", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", f"Measurements: {len(df)}", ""]

    # Summary stats
    lines.append("## Summary Statistics")
    lines.append("| Axis | Mean | Std | Min | Max |")
    lines.append("|------|------|-----|-----|-----|")
    for a in POSITIVE_AXES + ["B", "bal"]:
        if a in df.columns:
            lines.append(f"| {a} | {df[a].mean():.3f} | {df[a].std():.3f} | {df[a].min():.3f} | {df[a].max():.3f} |")
    lines.append("")

    # Status distribution
    if "status" in df.columns:
        lines.append("## Balance Status Distribution")
        for s in ["STABLE", "DRIFTING"]:
            cnt = (df["status"] == s).sum()
            lines.append(f"- {s}: {cnt} ({cnt/len(df)*100:.0f}%)")
        dom_cnt = (~df["status"].isin(["STABLE", "DRIFTING"])).sum()
        lines.append(f"- DOM: {dom_cnt} ({dom_cnt/len(df)*100:.0f}%)")
        lines.append("")

    # By category
    if "category" in df.columns and df["category"].nunique() > 1:
        lines.append("## By Category")
        lines.append("| Category | E | F | N | M | B | Bal | n |")
        lines.append("|----------|---|---|---|---|---|-----|---|")
        for cat, g in df.groupby("category"):
            lines.append(f"| {cat} | {g['E'].mean():.2f} | {g['F'].mean():.2f} | {g['N'].mean():.2f} | {g['M'].mean():.2f} | {g['B'].mean():+.2f} | {g['bal'].mean():.3f} | {len(g)} |")
        lines.append("")

    # Observations
    obs = auto_observe(df.to_dict("records"))
    if obs:
        lines.append("## Auto-Observations")
        for sev, txt in obs:
            lines.append(f"- **{sev}**: {txt}")
        lines.append("")

    return "\n".join(lines)

# -- MAIN ---------------------------------------------------

def main():
    st.set_page_config(page_title="TRI-TFM v3", layout="wide")
    st.title("TRI-TFM v3.0")
    st.caption("Generator -> Judge v3 (E/F/N/M/B) -> Bal v3 (sigma EFNM)")

    with st.sidebar:
        env_key = os.environ.get("GEMINI_API_KEY", "")
        if env_key:
            api_key = env_key
            st.success("API key loaded from env")
        else:
            api_key = st.text_input("Gemini API Key", type="password")

        model = st.selectbox("Model", MODELS)
        stage = st.selectbox("Stage", list(STAGE_MODES.keys()))
        temp = st.slider("Temperature", 0.0, 2.0, DEFAULT_TEMP, 0.05)
        mode = st.radio("Mode", ["Single", "Batch CSV", "Analytics"])

    if "all_results" not in st.session_state:
        st.session_state.all_results = []

    # -- SINGLE --
    if mode == "Single":
        prompt = st.text_area("Prompt", height=100)
        if st.button("Run", type="primary", disabled=not api_key or not prompt):
            client = genai.Client(api_key=api_key)
            with st.spinner("Evaluating..."):
                try:
                    r = evaluate(client, model, prompt, stage, temp)
                except Exception as e:
                    st.error(str(e))
                    return

            st.markdown(r["response"])
            st.markdown("---")

            ic = {"STABLE": "green", "DRIFTING": "orange"}.get(r["status"], "red")
            st.markdown(f"### :{ic}[{r['status']}] Bal = {r['bal']:.3f}")

            def bar(v):
                f = int(round(max(0, min(1, v)) * 10))
                return "█" * f + "░" * (10 - f)

            st.code(
                f"E [{bar(r['E'])}] {r['E']:.2f}  {r['E_reason']}\n"
                f"F [{bar(r['F'])}] {r['F']:.2f}  {r['F_reason']}\n"
                f"N [{bar(r['N'])}] {r['N']:.2f}  {r['N_reason']}\n"
                f"M [{bar(r['M'])}] {r['M']:.2f}  {r['M_reason']}\n"
                f"B {r['B']:+.2f}  {r['B_reason']}", language=None)

            st.session_state.all_results.append({
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt, "category": "manual", "model": model,
                **{k: r[k] for k in ["E", "F", "N", "M", "B", "bal", "status"]}
            })

    # -- BATCH --
    elif mode == "Batch CSV":
        st.markdown("### Batch")
        st.markdown("CSV columns: `prompt,category,language`")
        st.caption("Categories: factual, philosophical, creative, technical, ethical, directive, personal")

        csv = st.file_uploader("Upload CSV", type=["csv"])
        if csv:
            try:
                df = pd.read_csv(StringIO(csv.getvalue().decode("utf-8")))
                if "prompt" not in df.columns:
                    st.error("Need 'prompt' column")
                    return
                if "category" not in df.columns:
                    df["category"] = "other"
                if "language" not in df.columns:
                    df["language"] = "auto"
                st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(str(e))
                return

            n_rep = st.slider("Repeats per prompt", 1, 10, 1)
            total = len(df) * n_rep
            st.info(f"{len(df)} prompts x {n_rep} = {total} runs")

            if st.button("Run Batch", type="primary", disabled=not api_key):
                client = genai.Client(api_key=api_key)
                pbar = st.progress(0)
                results = []
                done = 0

                for _, row in df.iterrows():
                    p = str(row["prompt"])
                    cat = str(row.get("category", "other"))
                    for rep in range(n_rep):
                        done += 1
                        pbar.progress(done / total, f"[{done}/{total}] {p[:40]}...")
                        try:
                            r = evaluate(client, model, p, stage, temp)
                            results.append({
                                "timestamp": datetime.now().isoformat(),
                                "prompt": p, "category": cat,
                                "language": str(row.get("language", "auto")),
                                "model": model,
                                **{k: r[k] for k in ["E", "F", "N", "M", "B", "bal", "status",
                                                      "E_reason", "F_reason", "N_reason", "M_reason", "B_reason"]},
                                "response_preview": r["response"][:200],
                            })
                        except Exception as e:
                            st.warning(f"Failed: {p[:30]}: {e}")
                        time.sleep(0.3)

                pbar.progress(1.0, "Done!")

                if results:
                    rdf = pd.DataFrame(results)
                    st.dataframe(
                        rdf[["prompt", "category", "E", "F", "N", "M", "B", "bal", "status"]].style.format(
                            {"E": "{:.2f}", "F": "{:.2f}", "N": "{:.2f}", "M": "{:.2f}", "B": "{:+.2f}", "bal": "{:.3f}"}),
                        use_container_width=True, hide_index=True)

                    # Variance
                    if n_rep > 1:
                        st.markdown("### Variance")
                        for p in df["prompt"].unique():
                            sub = rdf[rdf["prompt"] == p]
                            if len(sub) > 1:
                                st.markdown(f"**{p[:60]}** (n={len(sub)})")
                                st.dataframe(pd.DataFrame({
                                    a: {"mean": sub[a].mean(), "std": sub[a].std(), "range": sub[a].max() - sub[a].min()}
                                    for a in ["E", "F", "N", "M", "B", "bal"]
                                }).T.round(4), use_container_width=True)

                    # Auto-obs
                    st.markdown("### Observations")
                    obs = auto_observe(results)
                    for sev, txt in obs:
                        ic = {"CRITICAL": "red", "HIGH": "orange", "INFO": "blue"}.get(sev, "gray")
                        st.markdown(f":{ic}[**{sev}**]: {txt}")

                    st.session_state.all_results.extend(results)

                    # Downloads
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("Download CSV",
                            rdf.to_csv(index=False).encode("utf-8"),
                            f"tri_tfm_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv")
                    with c2:
                        md = generate_markdown_report(rdf)
                        st.download_button("Download Markdown Report",
                            md.encode("utf-8"),
                            f"tri_tfm_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                            mime="text/markdown")

    # -- ANALYTICS --
    elif mode == "Analytics":
        st.markdown("### Analytics")

        df = pd.DataFrame(st.session_state.all_results) if st.session_state.all_results else pd.DataFrame()

        up = st.file_uploader("Or upload previous CSV", type=["csv"], key="an")
        if up:
            loaded = pd.read_csv(up)
            for c in ["E", "F", "N", "M", "B", "bal"]:
                if c in loaded.columns:
                    loaded[c] = pd.to_numeric(loaded[c], errors="coerce")
            df = pd.concat([df, loaded], ignore_index=True) if not df.empty else loaded

        if df.empty:
            st.info("Run some tests or upload CSV.")
            return

        st.markdown(f"**{len(df)} measurements**")

        # Stats
        stats = {a: {"mean": df[a].mean(), "std": df[a].std(), "min": df[a].min(), "max": df[a].max()}
                 for a in POSITIVE_AXES + ["B", "bal"] if a in df.columns}
        st.dataframe(pd.DataFrame(stats).T.round(4), use_container_width=True)

        # Histograms
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure()
            for a in POSITIVE_AXES:
                if a in df.columns:
                    fig.add_trace(go.Histogram(x=df[a], name=a, opacity=0.7, xbins=dict(size=0.05)))
            fig.update_layout(barmode="overlay", title="E/F/N/M Distribution", height=350)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            if "bal" in df.columns:
                fig = go.Figure()
                fig.add_trace(go.Histogram(x=df["bal"], marker_color="purple", opacity=0.7, xbins=dict(size=0.05)))
                fig.add_vline(x=STABLE_THRESHOLD, line_dash="dash", line_color="green", annotation_text="STABLE")
                fig.add_vline(x=DRIFTING_THRESHOLD, line_dash="dash", line_color="orange", annotation_text="DRIFTING")
                fig.update_layout(title="Balance Distribution", height=350)
                st.plotly_chart(fig, use_container_width=True)

        # By category
        if "category" in df.columns and df["category"].nunique() > 1:
            st.markdown("### By Category")
            cs = df.groupby("category")[POSITIVE_AXES + ["bal"]].mean().round(3)
            st.dataframe(cs, use_container_width=True)
            fig = go.Figure()
            for a in POSITIVE_AXES:
                fig.add_trace(go.Bar(x=cs.index, y=cs[a], name=a))
            fig.update_layout(barmode="group", height=400, title="Axes by Category")
            st.plotly_chart(fig, use_container_width=True)

        # Scatter: M vs F
        st.markdown("### M vs F Scatter")
        color_col = "category" if "category" in df.columns else None
        fig = px.scatter(df, x="F", y="M", color=color_col,
                         hover_data=["bal"] if "bal" in df.columns else None,
                         height=400, title="Meta-context (M) vs Fact (F)",
                         labels={"F": "F (Epistemic Grounding)", "M": "M (Explanatory Depth)"})
        fig.add_hline(y=0.5, line_dash="dot", line_color="gray", opacity=0.5)
        fig.add_vline(x=0.5, line_dash="dot", line_color="gray", opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)

        # Scatter: E vs F
        if "category" in df.columns:
            fig = px.scatter(df, x="F", y="E", color="category",
                             hover_data=["bal"], height=400, title="E vs F")
            st.plotly_chart(fig, use_container_width=True)

        # Markdown report download
        md = generate_markdown_report(df)
        st.download_button("Download Markdown Report", md.encode("utf-8"),
                           f"tri_tfm_analytics_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                           mime="text/markdown")


if __name__ == "__main__":
    main()
