import streamlit as st

# ==================================================
# PAGE CONFIG — MUST BE FIRST AND ONLY TIME
# ==================================================
st.set_page_config(
    page_title="S.Y.N.Cvoice™",
    page_icon="🧠",
    layout="centered",
)

# ==================================================
# SAFE IMPORTS (AFTER PAGE CONFIG)
# ==================================================
from src.predict import predict

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
# MAIN APP
# ==================================================
def main():
    # Header
    st.title(APP_TITLE)
    st.caption(APP_TAGLINE)
    st.markdown(f"**Tone rule:** {TONE_RULE}")

    st.divider()

    # Input
    st.subheader("Review copy")
    text = st.text_area(
        "Paste your draft copy here",
        height=200,
        placeholder="Paste a caption, email, landing page copy, or system message…",
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
            "Higher sensitivity speaks only when signals are very clear.\n\n"
            "Guardrails always apply."
        ),
    )

    run = st.button("Run S.Y.N.Cvoice™ Review", type="primary")

    if not run:
        return

    if not text.strip():
        st.warning("Paste some copy first.")
        return

    # ==================================================
    # RUN ANALYSIS
    # ==================================================
    try:
        out = predict(text, threshold=threshold)
    except Exception as e:
        st.error("Something went wrong while running the review.")
        st.code(str(e))
        return

    # ==================================================
    # RESULTS
    # ==================================================
    st.divider()
    st.subheader("Result")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Confidence bucket", out.get("confidence_bucket", "—"))
    with c2:
        st.metric(
            "Confidence score",
            f"{out.get('confidence_score', 0):.2f}",
        )

    st.write("**Routing**")
    st.info(out.get("routing", "—"))

    # ==================================================
    # TONE SIGNALS
    # ==================================================
    st.write("**Tone signals detected**")
    tones = out.get("tone_tags", [])
    if tones:
        for name, score in tones:
            st.write(f"- {name} ({score:.2f})")
    else:
        st.caption("No strong tone signals surfaced.")

    # ==================================================
    # RISK FLAGS
    # ==================================================
    risks = out.get("risk_flags", [])
    if risks:
        st.error("Potential risks detected (review before publishing).")
        for name, _ in risks:
            st.write(f"- {name}")
    else:
        st.success("No rule-based risks detected.")

    # ==================================================
    # GUIDANCE
    # ==================================================
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
        st.write("**Gentler language alternatives**")
        st.info(subs)

    # ==================================================
    # FINAL GATE
    # ==================================================
    st.divider()
    st.markdown(
        f"> **Final gate:** {out.get('final_gate_question', 'Does this copy help someone listen to themselves without pressure?')}"
    )


# ==================================================
# ENTRY POINT
# ==================================================
if __name__ == "__main__":
    main()
