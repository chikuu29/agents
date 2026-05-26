---
name: PDFGeneration
description: Generate professional PDF documents from text, markdown, HTML, or structured data with templates and styling.
triggers:
  - generate pdf
  - create pdf
  - export pdf
  - make pdf
  - convert to pdf
  - pdf report
  - pdf document
  - save as pdf
  - build report
mcp_servers:
  - pdf_mcp
---

# PDF Generation Guide

This skill enables the agent to generate professional PDF documents from various input formats. When this skill is active, follow these procedures for high-quality PDF output.

## 1. Input Analysis

Before generating a PDF, determine the input type:
- **Markdown text**: Convert markdown formatting (headers, bold, lists, code blocks) into styled PDF elements.
- **HTML content**: Render HTML with CSS into a PDF layout.
- **Structured data (JSON)**: Create formatted tables, charts, and reports from data dictionaries/lists.
- **Plain text**: Apply clean typography and formatting.

## 2. Document Structure

Follow standard document layout practices:
- **Title Page**: Include document title, subtitle (optional), author, and date when appropriate.
- **Headers & Footers**: Add page numbers, document title, and generation date in footers.
- **Table of Contents**: For documents longer than 3 pages, generate an automatic TOC.
- **Consistent Styling**: Use the same font family, heading sizes, and color scheme throughout.

## 3. Content Formatting

- **Typography**: Use professional fonts (Helvetica for body, appropriate weights for headers).
- **Tables**: Render data tables with alternating row colors, bold headers, and proper alignment.
- **Code Blocks**: Display code in monospace font with subtle background shading.
- **Lists**: Support ordered and unordered lists with proper indentation and bullet styles.
- **Images**: Embed images if provided, scaling appropriately to page width.

## 4. Templates

Available templates:
- `report` — Professional report with cover page, TOC, and sections.
- `invoice` — Formatted invoice with line items, totals, and payment details.
- `letter` — Formal letter layout with header, salutation, body, and signature.
- `simple` — Clean, minimal document for general content.

## 5. Output

- Save generated PDFs to the specified output path.
- Default filename format: `{title}_{date}.pdf`
- Report the file path and page count upon successful generation.

## 6. Error Handling

- Validate input data before generation.
- Handle missing fonts gracefully by falling back to built-in fonts.
- Report any images that failed to embed with clear error messages.
