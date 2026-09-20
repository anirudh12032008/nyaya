"""Nyaya UI for legal document analysis."""

from __future__ import annotations

import io

import streamlit as st
from pypdf import PdfReader

from agent.document_analyzer import analyze_document


def _extract_pdf_text(uploaded_file) -> str:
    """Extract text from all readable PDF pages."""

    reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n\n".join(pages)


def _extract_text(uploaded_file) -> str:
    """Extract text from supported document formats."""

    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return _extract_pdf_text(uploaded_file)

    if filename.endswith(".txt"):
        return uploaded_file.getvalue().decode(
            "utf-8",
            errors="ignore",
        )

    return ""


def _show_list(title: str, items) -> None:
    """Display a list section consistently."""

    st.subheader(title)

    if not items:
        st.write("Not specified.")
        return

    for item in items:
        st.write(f"• {item}")


def render():
    """Render the Legal Document Analyzer page."""

    st.title("📄 Legal Document Analyzer")

    st.markdown(
        """
        Upload a legal document and Nyaya will extract:

        - 👥 Parties
        - 📅 Important dates
        - ⚖️ Laws and sections
        - 📌 Key clauses
        - 📝 Obligations
        - ⏰ Deadlines
        - ⚠️ Potential issues to review
        - ✅ Required actions
        """
    )

    uploaded_file = st.file_uploader(
        "Upload a legal document",
        type=["pdf", "txt"],
        help="Supported formats: PDF and TXT.",
    )

    if uploaded_file is None:
        st.info("Upload a PDF or TXT document to start.")
        return

    st.success(f"Uploaded: {uploaded_file.name}")

    if not st.button(
        "🔍 Analyze Document",
        type="primary",
    ):
        return

    with st.spinner("Analyzing document..."):

        try:
            document_text = _extract_text(uploaded_file)
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

    st.success("Document analysis completed.")

    st.subheader("📋 Document Type")
    st.write(
        result.get(
            "document_type",
            "Not specified",
        )
    )

    _show_list(
        "👥 Parties",
        result.get("parties", []),
    )

    _show_list(
        "📅 Important Dates",
        result.get("important_dates", []),
    )

    _show_list(
        "⚖️ Laws & Sections",
        result.get("laws_and_sections", []),
    )

    _show_list(
        "📌 Key Clauses",
        result.get("key_clauses", []),
    )

    _show_list(
        "📝 Obligations",
        result.get("obligations", []),
    )

    _show_list(
        "⏰ Deadlines",
        result.get("deadlines", []),
    )

    st.subheader("⚠️ Potential Issues to Review")

    risks = result.get("potential_risks", [])

    if risks:
        for risk in risks:
            st.warning(risk)
    else:
        st.write("No potential issues were identified.")

    _show_list(
        "✅ Required Actions",
        result.get("required_actions", []),
    )

    st.subheader("💡 Simple Explanation")

    st.info(
        result.get(
            "simple_explanation",
            "No explanation available.",
        )
    )

    st.caption(
        "This analysis is informational and does not constitute legal advice."
    )