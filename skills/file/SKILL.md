---
name: FileOperations
description: Capabilities to navigate directories, read files, write new files, and perform targeted modifications.
triggers:
  - read file
  - write file
  - edit file
  - list directory
  - search files
  - modify file
  - create folder
mcp_servers:
  - file_mcp
---

# File Operations Guide

This skill enables the agent to interact with the local filesystem, explore directory structures, view file contents, write new code or data, and safely apply incremental edits. Follow these instructions when this skill is active.

## 1. Directory Exploration & Search

- **Recursive Listing**: Explore directory subtrees when looking for code files or assets, keeping track of depth to avoid massive outputs in deeply nested workspaces (e.g. `node_modules` or `.git`).
- **Targeted Search**: Use pattern matching (globs or regexes) to locate files by name or extension rather than listing all files.

## 2. File Reading & Viewing

- **Chunked Reading**: For large files, view only relevant line ranges (using start/end parameters) instead of loading the entire file, saving token context and processing time.
- **Identify Encoding**: Handle text files with appropriate encodings (UTF-8 by default).

## 3. Writing and Creating Files

- **Clean Structure**: Create parent directories automatically as needed when writing a new file.
- **Format Consistency**: Ensure newly written files follow the formatting rules of the project (e.g., standard indentation, naming conventions).

## 4. File Editing and Patching

- **Targeted Replacements**: When modifying existing files, always prefer targeted, contiguous replacements of specific blocks of code to avoid rewriting whole files.
- **Preserve Documentation**: Maintain existing unrelated inline comments, docstrings, and formatting unless explicitly instructed to refactor or change them.
- **Validation**: Ensure that after editing a file, syntax correctness and semantic integrity are preserved.
