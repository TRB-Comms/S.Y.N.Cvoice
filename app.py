import json
import streamlit as st

from src.predict import predict
from src.utils import abs_path


# ----------------------------
# S.Y.N.Cvoice™ — Streamlit App
# ----------------------------

APP_TITLE = "S.Y.N.Cvoice™"
APP_TAGLINE = "A tone-and-safety layer that helps language stay state-based, shame-free and choice-led."
TONE_FOOTER = "Invitational. Non-urgent. Body-led. Shame-free."


def load_guardrails_yaml() -> str:
    """
    Loads your guardrails YAML so you can display it in-app.
    If the file isn't found, returns a helpful message.
    """
    try:
        p = abs_path("guardrails", "trb_guardrails.yaml")
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"(Guardrails YAML not found or unreadable: {e})"


def render_kv_flags(title: str, flags: dict, icon_ok="✅", icon_bad="⚠️"):
    """
    Renders boolean flags cleanly.
    """
    st.write(f"**{title}**")
    if not flags:
        st.caption("No flags available.")
        return

    cols = st.columns(2)
    items = list(flags.items())

    half = (len(items) + 1) // 2
    left_items = items[:half]
    right_items = items[half:]

    with cols[0]:
        for k, v in left_items:
            st.write(f"{icon_bad if v else icon_ok} `{k}`")

    with cols[1]:
        for k, v in right_items:
            st.write(f"{icon_bad if v else icon_ok} `{k}`")


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🧠", layout="centered")

    st.title(f"🧠 {APP_TITLE}")
    st.caption(APP_TAGLINE)
    st.markdown(f"**Tone Rule:** {TONE_FOOTER}")

    # Guardrails viewer
    with st.expander("View TRB Guardrails (YAML)"):
        st.code(load_guardrails_yaml(), language="yaml")

    # Input
    st.subheader("Review copy")
    text = st.text_area(
        "Paste your draft copy here",
        height=220,
        placeholder="Paste a caption, landing page section, email copy, or system message…",
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        threshold = st.slider("Model threshold", 0.20, 0.90, 0.50, 0.05)
    with c2:
        show_raw = st.checkbox("Show raw JSON", value=False)
    with c3:
        run = st.button("Run S.Y.N.Cvoice Review", type="primary")

    if not run:
        st.stop()

    if not text.strip():
        st.warning("Paste some copy first.")
        st.stop()

    # Predict
    try:
        out = predict(text, threshold=threshold)
    except Exception as e:
        st.error("Error running prediction.")
        st.code(str(e))
        st.stop()

    # Summary
    st.subheader("Result")

    colA, colB = st.columns(2)
    with colA:
        st.metric("Confidence bucket", out.get("confidence_bucket", "n/a"))
    with colB:
        conf = out.get("confidence_score", None)
        if conf is not None:
            st.metric("Confidence score", f"{conf:.2f}")
        else:
            st.metric("Confidence score", "n/a")

    # Routing
    st.write("**Routing**")
    st.info(out.get("routing", "n/a"))

    # Tone tags
    st.write("**Tone behaviors + tags**")
    tone_tags = out.get("tone_tags", [])
    if tone_tags:
        st.json(tone_tags)
    else:
        st.caption("No tone tags above threshold.")

    # Risks
    st.write("**Risk flags**")
    risk_flags = out.get("risk_flags", [])
    if risk_flags:
        st.error("Potential risks detected (review before publishing).")
        st.json(risk_flags)
    else:
        st.success("No rule-based risks detected.")

    # Flags (rule + behavior)
    st.divider()

    rf = out.get("rule_flags", {})
    bf = out.get("behavior_flags", {})

    render_kv_flags("Rule flags (deterministic checks)", rf)
    st.write("")
    render_kv_flags("Behavior flags (TRB principles detected)", bf, icon_ok="✅", icon_bad="➕")

    # Guidance
    st.divider()
    guidance = out.get("rewrite_guidance", [])
    if guidance:
        st.write("**Rewrite guidance (non-directive suggestions)**")
        for g in guidance:
            st.write(f"- {g}")
    else:
        st.caption("No guidance returned.")

    # Final gate
    st.write("**Final gate question**")
    st.markdown(f"> {out.get('final_gate_question', 'Does this copy help someone listen to themselves without pressure?')}")

    # Optional raw JSON
    if show_raw:
        st.divider()
        st.write("**Raw output (JSON)**")
        st.code(json.dumps(out, indent=2), language="json")


if __name__ == "__main__":
    main()
