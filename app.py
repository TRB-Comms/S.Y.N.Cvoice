import json
import streamlit as st
from pathlib import Path

# ==================================================
# PAGE CONFIG — MUST BE FIRST
# ==================================================
st.set_page_config(
    page_title="S.Y.N.Cvoice™",
    page_icon="syncvoice-logo.png",
    layout="centered",
)

# ==================================================
# SAFE IMPORTS (AFTER PAGE CONFIG)
# ==================================================
from src.predict import predict
from src.utils import abs_path

# ==================================================
# PATHS
# ==================================================
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "syncvoice-logo.png"

# ==================================================
# APP COPY
# ==================================================
APP_TITLE = "S.Y.N.Cvoice™"
APP_TAGLINE = (
    "A tone-and-safety layer that helps language stay "
    "state-based, shame-free, and choice-led."
)
TONE_RULE = "Invitational · Non-urgent · Body-led · Shame-free"

# ==================================================
# HELPERS
# ==================================================
def load_guardrails_yaml() -> str:
    """
    Load guardrails YAML for transparency.
    Shown in expandable section.
    """
    try:
        p = abs_path("guardrails", "trb_guardrails.yaml")
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"(Guardrails YAML not found: {e})"


def render_bool_flags(title: str, flags: dict):
    st.write(f"**{title}**")
    if not flags:
        st.caption("No flags returned.")
        return

    items = sorted(flags.items(), key=lambda x: (not x[1], x[0]))
    cols = st.columns(2)
    half = (len(items) + 1) // 2

    for col, chunk in zip(cols, [items[:half], items[half:]]):
        with col:
            for k, v in chunk:
                st.write(f"{'✅' if v else '▫️'} `{k}`")


def render_pairs(title: str, pairs: list, empty_msg: str):
    st.write(f"**{title}**")
    if not pairs:
        st.caption(empty_msg)
        return
    for name, score in pairs:
        st.write(f"- {name} ({score:.2f})")


# ==================================================
# MAIN APP
# ==================================================
def main():
    # ------------------------------
    # HEADER
    # ------------------------------
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=96)

    st.title(APP_TITLE)
    st.caption(APP_TAGLINE)
    st.markdown(f"**Tone rule:** {TONE_RULE}")

    # ------------------------------
    # GUARDRAILS (EXPANDABLE)
    # ------------------------------
    with st.expander("View language guardrails (YAML)"):
        st.code(load_guardrails_yaml(), language="yaml")

    st.divider()

    # ------------------------------
    # INPUT
    # ------------------------------
    st.subheader("Review copy")

    text = st.text_area(
        "Paste your draft copy here",
        height=220,
        placeholder="Paste a caption, landing page section, email copy, or system message…",
    )

    threshold = st.slider(
        "Signal sensitivity",
        0.20,
        0.90,
        0.50,
        0.05,
        help=(
            "Controls how much evidence S.Y.N.Cvoice™ requires before surfacing tone signals.\n\n"
            "Lower sensitivity surfaces subtle signals.\n"
            "Higher sensitivity speaks less and only when signals are very clear.\n\n"
            "Guardrails always apply."
        ),
    )

    show_raw = st.checkbox("Show raw output (JSON)", value=False)
    run = st.button("Run S.Y.N.Cvoice™ Review", type="primary")

    if not run:
        return

    if not text.strip():
        st.warning("Paste some copy first.")
        return

    # ------------------------------
    # RUN ANALYSIS
    # ------------------------------
    try:
        out = predict(text, threshold=threshold)
    except Exception as e:
        st.error("Error running review.")
        st.code(str(e))
        return

    # ------------------------------
    # RESULTS
    # ------------------------------
    st.divider()
    st.subheader("Result")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Confidence bucket", out.get("confidence_bucket", "—"))
    with c2:
        st.metric("Confidence score", f"{out.get('confidence_score', 0):.2f}")

    st.write("**Routing**")
    st.info(out.get("routing", "—"))

    # ------------------------------
    # SIGNALS & FLAGS
    # ------------------------------
    render_pairs(
        "Tone behaviors + signals",
        out.get("tone_tags", []),
        "No strong tone signals surfaced.",
    )

    risks = out.get("risk_flags", [])
    if risks:
        st.error("Potential risks detected (review before publishing).")
        for r, _ in risks:
            st.write(f"- {r}")
    else:
        st.success("No rule-based risks detected.")

    st.divider()

    render_bool_flags("Rule flags (deterministic checks)", out.get("rule_flags", {}))
    st.write("")
    render_bool_flags("Behavior flags (pressure / urgency signals)", out.get("behavior_flags", {}))

    # ------------------------------
    # GUIDANCE
    # ------------------------------
    st.divider()
    st.subheader("Rewrite guidance")

    guidance = out.get("rewrite_guidance", [])
    if guidance:
        for g in guidance:
            st.write(f"- {g}")
    else:
        st.caption("Language appears aligned with S.Y.N.Cvoice™ guardrails.")

    subs = out.get("substitution_suggestions", "")
    if subs:
        st.write("**Gentler language substitutions**")
        st.info(subs)

    # ------------------------------
    # FINAL GATE
    # ------------------------------
    st.divider()
    st.markdown(
        f"> **Final gate:** {out.get('final_gate_question', 'Does this copy help someone listen to themselves without pressure?')}"
    )

    # ------------------------------
    # RAW OUTPUT (OPTIONAL)
    # ------------------------------
    if show_raw:
        st.divider()
        st.code(json.dumps(out, indent=2), language="json")


# ==================================================
# ENTRY POINT
# ==================================================
if __name__ == "__main__":
    main()
