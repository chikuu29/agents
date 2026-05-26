---
name: WebSearch
description: Comprehensive capability to search the web, fetch URLs, extract content, and navigate pages.
triggers:
  - web search
  - search the web
  - fetch url
  - browse page
  - read website
  - find information online
mcp_servers:
  - web_mcp
  - fetch_mcp
---

# Web Search and Browsing Guide

This skill equips the agent with capabilities to search the web, fetch specific URLs, scrape text content, and extract key insights. When this skill is active, you should follow these detailed operation procedures.

## 1. Web Search Execution

Use the search engines and query syntax effectively:
- **Be Specific**: Formulate precise keywords rather than generic conversational sentences.
- **Advanced Syntax**: Use double quotes `"exact phrase"` for precise matches, `site:example.com` to restrict queries to specific domains, or a minus `-term` to exclude irrelevant search results.
- **Iterative Search**: If the first query yields no results or irrelevant results, analyze the returned snippets, refine the query terms, and try again.

## 2. Scraping and Page Retrieval

Once relevant URLs are identified, fetch their content:
- **Clean Content**: Extract main article text, headers, and bullet points. Strip out noise like advertisements, navigation bars, sidebars, headers, and cookie notices.
- **Handle Tables & Data**: When browsing pages containing structured tables or logs, convert the data into clear markdown tables or JSON lists for easy synthesis.
- **Handle Errors**: If a fetch fails due to rate limits or standard HTTP errors (403, 404, etc.), try to look for cached versions (e.g., via search engine snippets or alternative sources).

## 3. Link Navigation & Deep Browsing

If the target information is not on the landing page, navigate deeper:
- **Scan for Links**: Identify relative or absolute links matching terms like "next page", "documentation", "details", or topic keywords.
- **Paging**: Follow pagination controls when browsing multi-page articles or logs, maintaining context across page transitions.

## 4. Citation and Summarization

When presenting findings to the user:
- **Citing Sources**: Always provide absolute URLs for findings, formatting them clearly as Markdown links with descriptive text (e.g., `[Source Title](URL)`).
- **Accurate Summaries**: Condense long documents into highly informative bulleted summaries. Highlight the answer to the user's primary query explicitly.
