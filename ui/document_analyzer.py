"""Nyaya UI for legal document analysis."""
from __future__ import annotations

import streamlit as st

from agent.document_analyzer import analyze_document
from agent.evidence import extract_text
from ui import theme


def _show_list(title: str, items) -> None:
    """Display a list section consistently."""

    st.subheader(theme.t(title))

    if not items:
        st.write(theme.t("Not specified."))
        return

    for item in items:
        st.write(f"• {item}")


def render():
    """Render the Legal Document Analyzer page."""

    st.title(theme.t("📄 Legal Document Analyzer"))

    st.markdown(
        theme.t("""
        Upload a legal document and Nyaya will extract:

        - 👥 Parties
        - 📅 Important dates
        - ⚖️ Laws and sections
        - 📌 Key clauses
        - 📝 Obligations
        - ⏰ Deadlines
        - ⚠️ Potential issues to review
        - ✅ Required actions
        """)
    )

    uploaded_file = st.file_uploader(
        theme.t("Upload a legal document"),
        type=["pdf", "txt"],
        help=theme.t("Supported formats: PDF and TXT."),
    )

    if uploaded_file is None:
        st.info(theme.t("Upload a PDF or TXT document to start."))
        return

    st.success(f'{theme.t("Uploaded:")} {uploaded_file.name}')

    if not st.button(
        theme.t("🔍 Analyze Document"),
        type="primary",
    ):
        return

    with st.spinner("Analyzing document..."):

        try:
            document_text = extract_text(uploaded_file.getvalue(),
                                         uploaded_file.type or "", uploaded_file.name)
        except Exception as exc:
            st.error(f"Could not read the document: {exc}")
            return

        if not document_text.strip():
            st.error(
                "No readable text was found in this document."
            )
            return

        result = analyze_document(document_text)

    if "error" in result:
        st.error(result["error"])
        return

    st.success(theme.t("Document analysis completed."))

    st.subheader(theme.t("📋 Document Type"))
    st.write(
        result.get(
            "document_type",
            theme.t("Not specified."),
        )
    )

    explanation = result.get("simple_explanation", "No explanation available.")
    st.info(explanation)

    with st.expander(theme.t("👥 Parties & 📅 Important Dates")):
        _show_list("👥 Parties", result.get("parties", []))
        _show_list("📅 Important Dates", result.get("important_dates", []))

    with st.expander(theme.t("⚖️ Laws & Sections")):
        _show_list("⚖️ Laws & Sections", result.get("laws_and_sections", []))

    with st.expander(theme.t("📌 Key Clauses & 📝 Obligations")):
        _show_list("📌 Key Clauses", result.get("key_clauses", []))
        _show_list("📝 Obligations", result.get("obligations", []))

    with st.expander(theme.t("⏰ Deadlines")):
        _show_list("⏰ Deadlines", result.get("deadlines", []))

    with st.expander(theme.t("⚠️ Potential Issues to Review")):
        risks = result.get("potential_risks", [])
        if risks:
            for risk in risks:
                st.warning(risk)
        else:
            st.write(theme.t("No potential issues were identified."))

    with st.expander(theme.t("✅ Required Actions")):
        _show_list("✅ Required Actions", result.get("required_actions", []))

    st.caption(
        theme.t("This analysis is informational and does not constitute legal advice.")
    )
