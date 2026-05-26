# mcp_servers/pdf_mcp.py
"""
PDF Generation MCP Server.

Exposes PDF creation tools via the Model Context Protocol (MCP).
Uses reportlab for lightweight, dependency-free PDF generation.

Run standalone:  python mcp_servers/pdf_mcp.py
"""

import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ---------------------------------------------------------------------------
# PDF generation functions
# ---------------------------------------------------------------------------

def _get_styles():
    """Build custom paragraph styles for PDF documents."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontSize=28,
        leading=34,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a2e"),
    ))
    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        parent=styles["Normal"],
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#6c757d"),
        spaceAfter=40,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#16213e"),
    ))
    styles.add(ParagraphStyle(
        name="SubsectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        leading=17,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#0f3460"),
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="CodeBlock",
        parent=styles["Code"],
        fontSize=9,
        leading=12,
        backColor=colors.HexColor("#f5f5f5"),
        borderColor=colors.HexColor("#e0e0e0"),
        borderWidth=1,
        borderPadding=8,
        leftIndent=20,
        spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        name="FooterText",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
    ))
    return styles


def _markdown_to_flowables(text: str, styles) -> list:
    """Convert simple markdown text to reportlab flowables."""
    flowables = []
    lines = text.split("\n")
    in_code_block = False
    code_buffer = []

    for line in lines:
        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                code_text = "<br/>".join(code_buffer)
                flowables.append(Paragraph(code_text, styles["CodeBlock"]))
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        stripped = line.strip()

        # Headers
        if stripped.startswith("### "):
            flowables.append(Paragraph(stripped[4:], styles["SubsectionHeader"]))
        elif stripped.startswith("## "):
            flowables.append(Paragraph(stripped[3:], styles["SectionHeader"]))
        elif stripped.startswith("# "):
            flowables.append(Paragraph(stripped[2:], styles["CoverTitle"]))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            bullet_text = f"• {stripped[2:]}"
            flowables.append(Paragraph(bullet_text, styles["BodyText2"]))
        elif stripped.startswith("---"):
            flowables.append(HRFlowable(
                width="80%", thickness=1, color=colors.HexColor("#cccccc"),
                spaceAfter=10, spaceBefore=10,
            ))
        elif stripped == "":
            flowables.append(Spacer(1, 8))
        else:
            # Apply inline markdown: **bold**, *italic*
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
            flowables.append(Paragraph(text, styles["BodyText2"]))

    return flowables


def _add_page_numbers(canvas, doc):
    """Footer callback to add page numbers."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#999999"))
    page_text = f"Page {doc.page}"
    canvas.drawCentredString(letter[0] / 2, 0.5 * inch, page_text)
    date_text = datetime.now().strftime("%Y-%m-%d %H:%M")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, date_text)
    canvas.restoreState()


def generate_pdf_from_markdown(
    content: str,
    output_path: str,
    title: str = "Document",
    author: str = "Agent System",
    page_size: str = "letter",
) -> dict:
    """Generate a PDF from markdown content."""
    try:
        sizes = {"letter": letter, "a4": A4}
        psize = sizes.get(page_size.lower(), letter)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=psize,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
            title=title,
            author=author,
        )

        styles = _get_styles()
        flowables = []

        # Cover title
        flowables.append(Spacer(1, 80))
        flowables.append(Paragraph(title, styles["CoverTitle"]))
        flowables.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y')}",
            styles["CoverSubtitle"],
        ))
        flowables.append(Paragraph(f"Author: {author}", styles["CoverSubtitle"]))
        flowables.append(Spacer(1, 40))
        flowables.append(HRFlowable(
            width="60%", thickness=2, color=colors.HexColor("#16213e"),
            spaceAfter=20,
        ))
        flowables.append(PageBreak())

        # Content
        flowables.extend(_markdown_to_flowables(content, styles))

        doc.build(flowables, onFirstPage=_add_page_numbers, onLaterPages=_add_page_numbers)

        return {
            "success": True,
            "output_path": str(Path(output_path).resolve()),
            "pages": doc.page,
            "title": title,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_pdf_from_data(
    data: list[dict],
    output_path: str,
    title: str = "Data Report",
    columns: list[str] | None = None,
) -> dict:
    """Generate a PDF table report from structured data."""
    try:
        if not data:
            return {"success": False, "error": "No data provided"}

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
            title=title,
        )

        styles = _get_styles()
        flowables = []

        flowables.append(Paragraph(title, styles["CoverTitle"]))
        flowables.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["CoverSubtitle"],
        ))
        flowables.append(Spacer(1, 20))

        # Determine columns
        cols = columns or list(data[0].keys())

        # Build table data
        table_data = [cols]  # Header row
        for row in data:
            table_data.append([str(row.get(c, "")) for c in cols])

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))

        flowables.append(table)
        flowables.append(Spacer(1, 20))
        flowables.append(Paragraph(
            f"Total rows: {len(data)}", styles["BodyText2"],
        ))

        doc.build(flowables, onFirstPage=_add_page_numbers, onLaterPages=_add_page_numbers)

        return {
            "success": True,
            "output_path": str(Path(output_path).resolve()),
            "pages": doc.page,
            "rows": len(data),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_pdf_from_html(
    html_content: str,
    output_path: str,
    title: str = "Document",
) -> dict:
    """Generate a PDF from HTML content using reportlab's Paragraph (subset of HTML)."""
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
            title=title,
        )

        styles = _get_styles()
        flowables = [
            Paragraph(title, styles["CoverTitle"]),
            Spacer(1, 20),
            Paragraph(html_content, styles["BodyText2"]),
        ]

        doc.build(flowables, onFirstPage=_add_page_numbers, onLaterPages=_add_page_numbers)

        return {
            "success": True,
            "output_path": str(Path(output_path).resolve()),
            "pages": doc.page,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# MCP Server (JSON-RPC over stdin/stdout)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "generate_pdf_from_markdown",
        "description": "Generate a professional PDF document from markdown text content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Markdown content to convert to PDF",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path for the generated PDF",
                },
                "title": {
                    "type": "string",
                    "description": "Document title (default: 'Document')",
                },
                "author": {
                    "type": "string",
                    "description": "Document author (default: 'Agent System')",
                },
                "page_size": {
                    "type": "string",
                    "description": "Page size: 'letter' or 'a4' (default: 'letter')",
                },
            },
            "required": ["content", "output_path"],
        },
    },
    {
        "name": "generate_pdf_from_data",
        "description": "Generate a PDF report with formatted tables from structured JSON data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of data objects to render as a table",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path for the generated PDF",
                },
                "title": {
                    "type": "string",
                    "description": "Report title (default: 'Data Report')",
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column names to include (default: all keys from first row)",
                },
            },
            "required": ["data", "output_path"],
        },
    },
    {
        "name": "generate_pdf_from_html",
        "description": "Generate a PDF from HTML content (supports basic HTML subset).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "html_content": {
                    "type": "string",
                    "description": "HTML content to render in the PDF",
                },
                "output_path": {
                    "type": "string",
                    "description": "Output file path for the generated PDF",
                },
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
            },
            "required": ["html_content", "output_path"],
        },
    },
]


def handle_rpc(request: dict) -> dict:
    """Handle a single JSON-RPC request."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id", 1)

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOL_DEFINITIONS},
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handlers = {
            "generate_pdf_from_markdown": generate_pdf_from_markdown,
            "generate_pdf_from_data": generate_pdf_from_data,
            "generate_pdf_from_html": generate_pdf_from_html,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        result = handler(**arguments)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }


def main():
    """Run the MCP server, reading JSON-RPC from stdin and writing to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_rpc(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
