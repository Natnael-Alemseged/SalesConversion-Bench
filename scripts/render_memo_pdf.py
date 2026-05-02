#!/usr/bin/env python3
"""Render memo.md to memo.pdf (plain layout; no pandoc required)."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _md_line_to_fragments(line: str) -> str:
    """Minimal inline markdown → reportlab markup (escape XML)."""
    s = line.replace("\u2212", "-")  # unicode minus → ASCII for Helvetica
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    # `code`
    s = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", s)
    return s


def _lines_to_story(lines: list[str], body_style: ParagraphStyle) -> list:
    story: list = []
    in_fence = False
    for raw in lines:
        line = raw.rstrip("\n")
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            frag = _md_line_to_fragments(line) if line else " "
            story.append(Paragraph(frag or " ", mono_style))
            continue
        if not line.strip():
            story.append(Spacer(1, 0.12 * inch))
            continue
        if line.startswith("# "):
            frag = _md_line_to_fragments(line[2:])
            story.append(Paragraph(frag, title_style))
            story.append(Spacer(1, 0.08 * inch))
        elif line.startswith("## "):
            frag = _md_line_to_fragments(line[3:])
            story.append(Paragraph(frag, h2_style))
            story.append(Spacer(1, 0.06 * inch))
        elif line.startswith("### "):
            frag = _md_line_to_fragments(line[4:])
            story.append(Paragraph(frag, h3_style))
            story.append(Spacer(1, 0.05 * inch))
        elif line.startswith("---"):
            story.append(Spacer(1, 0.15 * inch))
        elif line.startswith("|") and "|" in line[1:]:
            frag = _md_line_to_fragments(line)
            story.append(Paragraph(frag, mono_style))
        else:
            frag = _md_line_to_fragments(line)
            story.append(Paragraph(frag, body_style))
    return story


base = Path(__file__).resolve().parent.parent
md_path = base / "memo.md"
pdf_path = base / "memo.pdf"
text = md_path.read_text(encoding="utf-8")
lines = text.splitlines()

styles = getSampleStyleSheet()
body_style = ParagraphStyle(
    "Body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=13,
    spaceAfter=4,
)
mono_style = ParagraphStyle(
    "Mono",
    parent=styles["Code"],
    fontName="Courier",
    fontSize=8,
    leading=10,
    leftIndent=0.15 * inch,
)
title_style = ParagraphStyle(
    "Title",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=16,
    leading=20,
    spaceAfter=8,
)
h2_style = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=16,
    spaceAfter=6,
)
h3_style = ParagraphStyle(
    "H3",
    parent=styles["Heading3"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    spaceAfter=4,
)

story = _lines_to_story(lines, body_style)
doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=letter,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.65 * inch,
    bottomMargin=0.65 * inch,
)
doc.build(story)
print(f"Wrote {pdf_path.relative_to(base)}")
