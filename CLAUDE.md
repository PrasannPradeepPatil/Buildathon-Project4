# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application called "Codebase Time Machine" that analyzes Git repositories and provides insights into their evolution, commit history, and contributor statistics.

## Development Commands

### Setting up the environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the application
```bash
# Start the Flask development server
python app.py
```
The application runs on `http://localhost:5000` with debug mode enabled.

### Database management
```bash
# The SQLite database (analysis.db) is automatically initialized on first run
# To reset the database, simply delete analysis.db and restart the app
rm analysis.db
```

## Architecture

### Core Components

1. **app.py** (lines 1-51): Main Flask application entry point
   - Sets up Flask server with routes for web interface
   - `/` - Serves the main HTML interface
   - `/analyze` - POST endpoint that accepts repository URLs for analysis
   - `/health` - Health check endpoint
   - Manages temporary directory creation/cleanup for repository cloning

2. **git_analyzer.py** (lines 1-153): Core repository analysis logic
   - `GitAnalyzer` class handles all Git repository analysis
   - Clones repositories to temporary directories
   - Analyzes commits with pattern-based classification (feature, bugfix, refactor, docs, test, style)
   - Aggregates contributor statistics (commits, insertions, deletions)
   - Generates timeline data and insights
   - Limited to 100 commits and 100 files for demo purposes

3. **database.py** (lines 1-63): SQLite database interface
   - `Database` class manages persistent storage
   - Stores analysis results as JSON in SQLite
   - Simple schema with analyses table (id, repo_url, analysis_data, created_at)

4. **Frontend** (templates/index.html, static/script.js, static/style.css)
   - Single-page application with vanilla JavaScript
   - Displays repository statistics, contributor rankings, and recent commits
   - Real-time loading states and error handling

### Data Flow

1. User submits repository URL via web interface
2. Flask endpoint receives request and creates temporary directory
3. GitAnalyzer clones repository and performs analysis
4. Results stored in SQLite database
5. JSON response sent back to frontend
6. Temporary repository files cleaned up automatically

### Key Design Patterns

- **Temporary file management**: Uses Python's `tempfile` module with proper cleanup in finally blocks
- **Error handling**: Try-catch blocks at each layer with appropriate error messages
- **Data limitation**: Analysis limited to recent commits/files to prevent performance issues
- **Commit classification**: Regex-based pattern matching for categorizing commit types

## Important Notes

- No test files exist in the main codebase (only in venv dependencies)
- Application uses Flask's built-in development server (not production-ready)
- GitPython library handles all Git operations
- Database uses JSON serialization for flexible schema
- Frontend uses vanilla JavaScript (no build process required)

# Claude Editing Guidelines

These are the rules Claude should follow when assisting with writing, editing, or refactoring text or code.

## General Principles
1. **Confirmation Before Major Changes**  
   - Always confirm with me before making large-scale rewrites, restructuring, or deletions.  
   - For any change that alters more than a few sentences/lines, pause and ask for approval.  

2. **Confidence in Changes**  
   - When making changes, be clear and confident about what was changed and why.  
   - Explain the reasoning briefly so I can trust the edit.  

3. **Minimalism & Precision**  
   - Make only the edits that I explicitly request.  
   - Keep changes as small as possible while still addressing the request.  
   - Avoid introducing additional edits, improvements, or suggestions unless asked.  

4. **Iteration Over Perfection**  
   - Provide small, incremental changes rather than large overhauls.  
   - Let me review and approve each step before proceeding further.  

5. **Transparency**  
   - Clearly mark what was changed (e.g., by quoting before/after snippets).  
   - If unsure whether a change is “major” or “minor,” treat it as major and confirm first.  

## Editing Workflow
1. Receive request.  
2. Propose the **minimal** set of edits needed.  
3. Show me the diff or highlight changes.  
4. Confirm with me before applying major or bulk edits.  
5. Apply confirmed edits with confidence.  

## Things NOT to Do
- ❌ Do **not** rewrite or rephrase beyond what was explicitly requested.  
- ❌ Do **not** change formatting, structure, or style unless I ask.  
- ❌ Do **not** merge multiple edits into one big rewrite; keep them incremental.  
- ❌ Do **not** make assumptions about my intent — always clarify if unsure.  
- ❌ Do **not** hide or gloss over changes; every edit must be transparent.  
- ❌ Do **not** downgrade or weaken confident language in my text unless I request a softer tone.  
- ❌ Do **not** suggest optional improvements unless I specifically ask for ideas or alternatives.  

---

**Example Behavior**  
- If I ask: *“Fix grammar in this sentence”* → Only fix grammar, don’t reword style.  
- If I ask: *“Shorten this section”* → Suggest a shorter version, then wait for my approval before replacing.  
- If I ask: *“Rewrite the introduction”* → Propose one draft and confirm with me before making additional passes.  
