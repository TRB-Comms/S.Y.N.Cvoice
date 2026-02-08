st.set_page_config(
    page_title="S.Y.N.Cvoice™",
    page_icon="🧠",
    layout="wide"
)
import streamlit as st

st.set_page_config(
    page_title="SYNCvoice",
    layout="wide"
)

st.title("S.Y.N.Cvoice™")
st.subheader("A tone-and-safety layer for state-based, shame-free language")

st.write("""
This is a live test render.
If you can see this, the app is loading correctly.
""")

import json
from src.predict import predict
from src.utils import abs_path

import json
import streamlit as st

from src.predict import predict
from src.utils import abs_path


# ----------------------------
# S.Y.N.Cvoice™ — Streamlit App
# ----------------------------

APP_TITLE = "S.Y.N.Cvoice™"
APP_TAGLINE = "Tomera Rodgers created a tone-and-safety layer that helps language stay state-based, shame-free and choice-led."
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


def render_bool_flags(title: str, flags: dict, true_icon="✅", false_icon="▫️"):
    """
    Renders boolean flags cleanly.
    Shows ✅ for True (flag triggered), ▫️ for False.
    """
    st.write(f"**{title}**")
    if not flags:
        st.caption("No flags available.")
        return

    items = list(flags.items())
    items.sort(key=lambda kv: (not bool(kv[1]), kv[0]))  # True first

    cols = st.columns(2)
    half = (len(items) + 1) // 2
    left_items = items[:half]
    right_items = items[half:]

    with cols[0]:
        for k, v in left_items:
            st.write(f"{true_icon if v else false_icon} `{k}`")

    with cols[1]:
        for k, v in right_items:
            st.write(f"{true_icon if v else false_icon} `{k}`")


def render_top_pairs(title: str, pairs: list, k: int = 6, empty_msg: str = "None detected."):
    """
    Renders a list of (name, score) as neat bullets.
    """
    st.write(f"**{title}**")
    if not pairs:
        st.caption(empty_msg)
        return

    for name, score in pairs[:k]:
        try:
            st.write(f"- {name} ({float(score):.2f})")
        except Exception:
            st.write(f"- {name}")


def main():
    # --- Favicon / page icon (must be first Streamlit call) ---
    logo_path = abs_path("assets", "syncvoice-logo.png")
    page_icon = str(logo_path) if logo_path.exists() else "🧠"

    st.set_page_config(page_title=APP_TITLE, page_icon=page_icon, layout="centered")

    # --- Header ---
    if logo_path.exists():
        st.image(str(logo_path), width=80)

    st.title(APP_TITLE)
    st.caption(APP_TAGLINE)
    st.markdown(f"**Tone Rule:** {TONE_FOOTER}")

    # --- Guardrails viewer ---
    with st.expander("View TRB Guardrails (YAML)"):
        st.code(load_guardrails_yaml(), language="yaml")

    st.divider()

    # --- Input ---
    st.subheader("Review copy")
    text = st.text_area(
        "Paste your draft copy here",
        height=220,
        placeholder="Paste a caption, landing page section, email copy, or system message…",
    )

    # --- Controls ---
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        threshold = st.slider(
            "Signal sensitivity",
            0.20,
            0.90,
            0.50,
            0.05,
            help=(
                "Controls how much evidence S.Y.N.Cvoice™ requires before surfacing tone signals or guidance. "
                "Lower sensitivity surfaces subtle signals. Higher sensitivity means the system speaks less "
                "and only when signals are very clear. Guardrails always apply."
            ),
        )
        st.caption(
            "Higher sensitivity does not relax rules. "
            "It simply requires clearer signals before S.Y.N.Cvoice™ offers guidance."
        )

    with c2:
        show_raw = st.checkbox("Show raw JSON", value=False)

    with c3:
        run = st.button("Reflect on this copy", type="primary")

    if not run:
        st.stop()

    if not text.strip():
        st.warning("Paste some copy first.")
        st.stop()

    # --- Predict ---
    try:
        out = predict(text, threshold=threshold)
    except Exception as e:
        st.error("Error running prediction.")
        st.code(str(e))
        st.stop()

    # --- Result summary ---
    st.subheader("Result")
    st.caption(
        "S.Y.N.Cvoice™ does not judge quality or intent. "
        "It reflects tone signals, pressure markers, and choice availability. "
        "When confidence is low, it intentionally pauses rather than forcing guidance."
    )

    colA, colB = st.columns(2)
    with colA:
        st.metric(
            "Confidence bucket",
            out.get("confidence_bucket", "n/a"),
            help="Confidence reflects strength of tone signals — not correctness or a value judgment.",
        )
    with colB:
        conf = out.get("confidence_score", None)
        st.metric("Confidence score", f"{float(conf):.2f}" if conf is not None else "n/a")

    # --- Routing ---
    st.write("**Routing**")
    st.info(out.get("routing", "n/a"))

    st.divider()

    # --- Tone tags & risks ---
    tone_tags = out.get("tone_tags", []) or []
    risk_flags = out.get("risk_flags", []) or []

    render_top_pairs("Tone behaviors + tags", tone_tags, k=8, empty_msg="No tone tags surfaced at this sensitivity.")

    st.write("")
    if risk_flags:
        st.error("Potential risks detected (review before publishing).")
        render_top_pairs("Risk flags", risk_flags, k=10, empty_msg="")
    else:
        st.success("No risk flags surfaced at this sensitivity.")

    st.divider()

    # --- Deterministic flags ---
    rf = out.get("rule_flags", {}) or {}
    bf = out.get("behavior_flags", {}) or {}

    render_bool_flags("Rule flags (deterministic checks)", rf, true_icon="✅", false_icon="▫️")
    st.write("")
    render_bool_flags("Behavior flags (pressure / urgency signals)", bf, true_icon="✅", false_icon="▫️")

    st.divider()

    # --- Guidance ---
    rewrite_guidance = out.get("rewrite_guidance", []) or []
    subs = out.get("substitution_suggestions", "") or ""

    if rewrite_guidance:
        st.write("**Rewrite guidance (S.Y.N.Cvoice™)**")
        # Expect list of bullets
        if isinstance(rewrite_guidance, list):
            for g in rewrite_guidance:
                if g:
                    st.write(f"- {g}")
        else:
            # Fallback
            st.info(str(rewrite_guidance))
    else:
        st.caption("No guidance returned.")

    if subs:
        st.write("**Substitution suggestions (TRB language map)**")
        # subs is a string block
        st.info(str(subs))
    else:
        st.caption("No substitutions detected.")

    st.divider()

    # --- Final gate ---
    st.write("**Final gate question**")
    st.markdown(f"> {out.get('final_gate_question', 'Does this copy help someone listen to themselves without pressure?')}")

    # --- Raw JSON ---
    if show_raw:
        st.divider()
        st.write("**Raw output (JSON)**")
        st.code(json.dumps(out, indent=2), language="json")


if __name__ == "__main__":
    main()
