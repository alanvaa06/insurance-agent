"""Streamlit interface for the Insurance Claims Processing Agent."""
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

# Make the project root importable when run as `streamlit run app/main.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.graph import get_claims_graph  # noqa: E402
from app.database.vector_store import get_policy_store  # noqa: E402
from app.utils.config import config  # noqa: E402
from app.utils.logger import logger  # noqa: E402

# --- Decision presentation (status, tone) ---
DECISION_STYLES = {
    "APPROVED": ("Approved", "ok"),
    "DENIED": ("Denied", "bad"),
    "INVALID": ("Invalid", "bad"),
    "REQUIRES_REVIEW": ("Requires review", "warn"),
}


# --- Streamlit log capture (per execution) ---
class StreamlitLogHandler(logging.Handler):
    def emit(self, record):
        entry = self.format(record)
        execution_id = st.session_state.get("current_execution_id")
        if not execution_id:
            return
        store = st.session_state.setdefault("execution_logs", {})
        bucket = store.setdefault(execution_id, [])
        if not bucket or bucket[-1] != entry:
            bucket.append(entry)


def _attach_log_handler():
    if not any(isinstance(h, StreamlitLogHandler) for h in logger.handlers):
        handler = StreamlitLogHandler()
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)s %(module)s - %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)


def _inject_css():
    st.markdown(
        """
        <style>
        html, body, [class*="css"] { font-family: ui-sans-serif, system-ui,
            -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        .block-container { max-width: 960px; padding-top: 2.2rem; }

        .app-title { font-size: 1.55rem; font-weight: 650; letter-spacing: -0.01em;
            color: #23211E; margin: 0; }
        .app-subtitle { font-size: 0.95rem; color: #6E6A62; margin: 0.25rem 0 0; }
        .app-rule { border: none; border-top: 1px solid #DEDAD2;
            margin: 1.1rem 0 1.6rem; }

        .decision { border: 1px solid #DEDAD2; border-radius: 0.5rem;
            padding: 1.1rem 1.25rem; margin: 0.5rem 0 1rem; background: #FFFFFF; }
        .decision-head { display: flex; align-items: center; gap: 0.6rem; }
        .decision-dot { width: 0.7rem; height: 0.7rem; border-radius: 50%;
            flex: 0 0 auto; }
        .decision-label { font-size: 1.1rem; font-weight: 620; letter-spacing: -0.01em; }
        .decision-reason { margin: 0.55rem 0 0; color: #45413A; line-height: 1.55;
            font-size: 0.94rem; }
        .decision.ok   { background: #F1F5F1; border-color: #CBDDCD; }
        .decision.ok   .decision-dot { background: #3E7D5C; }
        .decision.warn { background: #F6F1E4; border-color: #E2D6B6; }
        .decision.warn .decision-dot { background: #9A7B22; }
        .decision.bad  { background: #F6ECEA; border-color: #E3CBC6; }
        .decision.bad  .decision-dot { background: #A8463C; }

        .meta-row { display: flex; justify-content: space-between;
            padding: 0.35rem 0; border-bottom: 1px solid #E6E2DA; font-size: 0.9rem; }
        .meta-row:last-child { border-bottom: none; }
        .meta-key { color: #6E6A62; }
        .meta-val { color: #23211E; font-weight: 540; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_decision(decision: str, reasoning: str):
    label, tone = DECISION_STYLES.get(decision, (decision or "Unknown", "warn"))
    st.markdown(
        f"""
        <div class="decision {tone}">
          <div class="decision-head">
            <span class="decision-dot"></span>
            <span class="decision-label">{label}</span>
          </div>
          <p class="decision-reason">{reasoning or "No reasoning provided."}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_logs():
    execution_id = st.session_state.get("current_execution_id")
    logs = st.session_state.get("execution_logs", {}).get(execution_id, [])
    if logs:
        with st.expander("Processing log", expanded=False):
            st.code("\n".join(logs), language="log")


def start_execution() -> str:
    execution_id = str(uuid.uuid4())
    st.session_state.current_execution_id = execution_id
    st.session_state.execution_logs = {execution_id: []}
    return execution_id


def initialize_vector_store() -> bool:
    """Populate the policy index once. Returns True when ready."""
    if st.session_state.get("vector_store_ready"):
        return True
    if not config.is_api_key_configured():
        return False
    with st.spinner("Indexing policy documents"):
        try:
            get_policy_store().populate_from_pdf()
            st.session_state.vector_store_ready = True
            return True
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not initialize the policy index: {e}")
            logger.error(f"Vector store init failed: {e}")
            return False


def process_claim(claim_data: dict) -> dict:
    start_execution()
    logger.info("New claim received: %s", claim_data.get("claim_id", "N/A"))
    logger.info("Timestamp: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    initial_state = {"claim_json": json.dumps(claim_data), "current_step": "initialized"}
    final_state = get_claims_graph().invoke(initial_state)
    logger.info("Final decision: %s", final_state.get("final_decision", "N/A"))
    return final_state


def show_result(result: dict):
    render_decision(result.get("final_decision", "UNKNOWN"), result.get("final_reasoning", ""))
    render_logs()
    with st.expander("Processing detail"):
        st.json(
            {
                "claim_id": result.get("claim_id"),
                "valid": result.get("is_valid"),
                "validation_reason": result.get("validation_reason") or None,
                "coverage_status": result.get("coverage_status"),
                "coverage_reason": result.get("coverage_reason"),
                "queries_generated": len(result.get("policy_queries") or []),
                "recommendation": result.get("recommendation"),
                "recommendation_reasoning": result.get("recommendation_reasoning"),
                "price_check": result.get("price_check_result"),
                "final_decision": result.get("final_decision"),
            }
        )


def claim_form():
    st.caption("Required fields are marked with an asterisk.")
    col1, col2 = st.columns(2)
    with col1:
        claim_id = st.text_input("Claim ID *", placeholder="CLM-2026-001")
        policy_holder = st.text_input("Policy holder *", placeholder="Jane Doe")
    with col2:
        vendor_name = st.text_input("Service provider *", placeholder="AutoFix Garage")
        policy_number = st.text_input("Policy number", placeholder="Optional, e.g. PN-2")

    st.write("Invoice items")
    items = st.session_state.setdefault("invoice_items", [{"item": "", "amount": 0.0}])
    for i, item in enumerate(items):
        c_desc, c_amt, c_rm = st.columns([3, 1.4, 0.5])
        desc = c_desc.text_input("Description", value=item["item"], key=f"d{i}",
                                 label_visibility="collapsed", placeholder="Engine repair")
        amt = c_amt.number_input("Amount", value=float(item["amount"]), min_value=0.0,
                                 step=10.0, key=f"a{i}", label_visibility="collapsed")
        if c_rm.button("Remove", key=f"r{i}") and len(items) > 1:
            items.pop(i)
            st.rerun()
        items[i] = {"item": desc, "amount": amt}
    if st.button("Add item"):
        items.append({"item": "", "amount": 0.0})
        st.rerun()

    total = sum(it["amount"] for it in items if it["item"])
    st.markdown(f"**Total:** ${total:,.2f}")

    if st.button("Process claim", type="primary"):
        if not (claim_id and policy_holder and vendor_name):
            st.error("Fill in all required fields.")
            return
        if total <= 0:
            st.error("Claim total must be greater than zero.")
            return
        claim = {
            "claim_id": claim_id,
            "policy_holder": policy_holder,
            "vendor_name": vendor_name,
            "policy_number": policy_number or None,
            "invoice_items": [it for it in items if it["item"]],
            "total_amount": total,
        }
        with st.spinner("Processing claim"):
            try:
                show_result(process_claim(claim))
            except Exception as e:  # noqa: BLE001
                st.error(f"Processing failed: {e}")
                render_logs()


def upload_tab():
    uploaded = st.file_uploader("Claim JSON file", type=["json"])
    if not uploaded:
        return
    try:
        claim = json.load(uploaded)
    except json.JSONDecodeError:
        st.error("That file is not valid JSON.")
        return
    st.json(claim)
    if st.button("Process uploaded claim", type="primary"):
        with st.spinner("Processing claim"):
            try:
                show_result(process_claim(claim))
            except Exception as e:  # noqa: BLE001
                st.error(f"Processing failed: {e}")
                render_logs()


def logs_tab():
    log_dir = Path("logs")
    if not log_dir.exists() or not any(log_dir.iterdir()):
        st.info("No log files yet. Process a claim to generate one.")
        return
    files = sorted(p.name for p in log_dir.iterdir() if p.is_file())
    selected = st.selectbox("Log file", files)
    content = (log_dir / selected).read_text(encoding="utf-8")
    st.download_button("Download", content, file_name=selected, mime="text/plain")
    st.code(content, language="log")


def sidebar():
    with st.sidebar:
        st.subheader("About")
        st.write(
            "Adjudicates auto-insurance claims against policy documents using a "
            "LangGraph workflow with retrieval-augmented policy lookup."
        )
        st.subheader("Status")
        ready = st.session_state.get("vector_store_ready")
        rows = {
            "Model": config.model_name,
            "Policy index": "Ready" if ready else "Not loaded",
            "API key": "Configured" if config.is_api_key_configured() else "Missing",
        }
        for key, val in rows.items():
            st.markdown(
                f'<div class="meta-row"><span class="meta-key">{key}</span>'
                f'<span class="meta-val">{val}</span></div>',
                unsafe_allow_html=True,
            )


def main():
    st.set_page_config(page_title="Claims Processing Agent", layout="centered")
    _inject_css()
    _attach_log_handler()

    st.markdown('<p class="app-title">Insurance Claims Processing Agent</p>',
                unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">Automated adjudication of auto-repair claims '
                'against policy coverage.</p>', unsafe_allow_html=True)
    st.markdown('<hr class="app-rule" />', unsafe_allow_html=True)

    sidebar()

    if not config.is_api_key_configured():
        st.warning(
            "No OpenAI API key configured. Add OPENAI_API_KEY to your .env file "
            "(see .env.example) to process claims."
        )
        return

    initialize_vector_store()

    tab_new, tab_upload, tab_logs = st.tabs(["New claim", "Upload JSON", "Logs"])
    with tab_new:
        claim_form()
    with tab_upload:
        upload_tab()
    with tab_logs:
        logs_tab()


if __name__ == "__main__":
    main()
