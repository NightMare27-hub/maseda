"""
MASEDA - Multi-Agent Software Development Assistant
Interactive Web UI built with Streamlit.
"""

import os
import sys
import streamlit as st

# Ensure repository root is on PYTHONPATH
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.graph import run_task
from app.tools.files import apply_edits


def main():
    st.set_page_config(
        page_title="MASEDA | Multi-Agent Coding Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🤖 MASEDA Software Development Assistant")
    st.caption("Planner, Coder & Reviewer agents autonomously writing, testing, and reviewing code in a headless sandbox.")

    # ---------------- Sidebar Configuration ----------------
    with st.sidebar:
        st.header("⚙️ Configuration")
        repo_path = st.text_input(
            "Target Repository Path",
            value="demos/portfolio_simulator",
            help="Relative or absolute path to the Python project.",
        )

        st.subheader("RAG Options")
        rag_enabled = st.checkbox("Enable AST Codebase RAG", value=False, help="Index repository AST symbols and retrieve relevant code chunks.")
        rag_mode = st.selectbox(
            "Retrieval Strategy",
            options=["hybrid", "dense", "bm25"],
            index=0,
            disabled=not rag_enabled,
        )

        st.subheader("Patching")
        auto_apply = st.checkbox(
            "Auto-Apply Edits to Disk",
            value=True,
            help="Automatically write approved changes to the target repository if verification passes.",
        )

        st.divider()
        st.info("💡 **Dual-Gate Verification Active:** Generated code is verified with unit tests and headless entrypoint smoke tests before Reviewer approval.")

    # ---------------- Task Input ----------------
    st.subheader("📝 Task Specification")
    default_task = "Fix the AttributeError in app.py where PortfolioMetrics is missing the diversification_score attribute. Compute it in portfolio_engine.py and display it in app.py."
    task = st.text_area(
        "Describe the coding task, feature, or bug fix in plain English:",
        value=default_task,
        height=100,
        placeholder="e.g. Add Monte Carlo simulation percentile metrics to the portfolio engine...",
    )

    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        run_clicked = st.button("🚀 Run MASEDA", type="primary", use_container_width=True)

    # ---------------- Agent Execution ----------------
    if run_clicked:
        if not task.strip():
            st.error("Please enter a task description before running.")
            return

        abs_repo = os.path.abspath(os.path.join(ROOT_DIR, repo_path)) if not os.path.isabs(repo_path) else repo_path
        if not os.path.exists(abs_repo):
            st.error(f"Target repository path does not exist: `{abs_repo}`")
            return

        with st.spinner("Agents collaborating: Planner formulating strategy ➔ Coder patching ➔ Headless Sandbox verifying ➔ Reviewer auditing..."):
            try:
                result = run_task(
                    task=task.strip(),
                    repo_path=abs_repo,
                    rag=rag_enabled,
                    rag_mode=rag_mode,
                    verbose=True,
                )
                st.session_state["last_result"] = result
                st.session_state["target_repo"] = abs_repo

                if auto_apply and result.get("status") == "success" and result.get("edits"):
                    apply_edits(abs_repo, result["edits"])
                    st.session_state["applied"] = True
                else:
                    st.session_state["applied"] = False

            except Exception as ex:
                st.error(f"Execution failed: {ex}")
                return

    # ---------------- Display Results ----------------
    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        abs_repo = st.session_state.get("target_repo", "")
        status = res.get("status", "unknown")
        iterations = res.get("iteration", 1)

        st.divider()

        # Status Banner
        if status == "success":
            st.success(f"✅ **Task Solved and Approved!** Completed in {iterations} iteration(s). Run ID: `{res.get('run_id')}`")
        elif status == "retrying":
            st.warning(f"⚠️ **Incomplete / Retrying:** Reached iteration {iterations}.")
        else:
            st.error(f"❌ **Task Failed:** {res.get('error') or 'Verification did not pass within allowed rounds.'}")

        # Metrics Bar
        m1, m2, m3, m4 = st.columns(4)
        tokens = res.get("total_tokens", 0)
        cost = res.get("total_cost", 0.0)
        seconds = res.get("total_seconds", 0.0)
        chunks = len(res.get("retrieved_chunks", []))

        with m1:
            st.metric("Total Tokens", f"{tokens:,}")
        with m2:
            st.metric("Total Cost", f"${cost:.4f}")
        with m3:
            st.metric("Elapsed Time", f"{seconds:.2f}s")
        with m4:
            st.metric("RAG Chunks", chunks if rag_enabled else "Off")

        # Plain-English Explanation
        rf = res.get("reviewer_feedback", {})
        user_explanation = res.get("user_explanation") or rf.get("user_explanation")
        if user_explanation:
            with st.expander("📖 User Explanation & How-To-Run Instructions", expanded=True):
                st.markdown(user_explanation)

        # Tabbed Details
        tab_diff, tab_plan, tab_tests, tab_review = st.tabs(["📄 Code Diff", "📋 Agent Plan", "🧪 Sandbox & Tests", "🔍 Reviewer Feedback"])

        with tab_diff:
            diff = res.get("diff", "")
            if diff:
                st.code(diff, language="diff")
                if not st.session_state.get("applied", False) and res.get("edits"):
                    if st.button("💾 Apply These Changes to Disk Now"):
                        apply_edits(abs_repo, res["edits"])
                        st.session_state["applied"] = True
                        st.success("Changes successfully written to disk!")
                elif st.session_state.get("applied", False):
                    st.info("ℹ️ These changes have been applied to the target repository.")
            else:
                st.write("No code modifications proposed.")

        with tab_plan:
            plan = res.get("plan", {})
            st.json(plan)

        with tab_tests:
            st.write(f"**Tests Passed:** `{res.get('tests_passed', False)}`")
            test_out = res.get("test_output", "No test output available.")
            st.code(test_out, language="text")

        with tab_review:
            if rf:
                st.write(f"**Verdict Summary:** {rf.get('summary', 'N/A')}")
                if rf.get("feedback"):
                    st.write(f"**Diagnostic Details:** {rf.get('feedback')}")
                if rf.get("suggested_fixes"):
                    st.write("**Suggested Fixes:**")
                    for fix in rf["suggested_fixes"]:
                        st.markdown(f"- {fix}")
            else:
                st.write("No reviewer feedback recorded.")


if __name__ == "__main__":
    main()

