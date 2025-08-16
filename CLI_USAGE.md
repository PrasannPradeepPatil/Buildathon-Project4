# Codebase Time Machine CLI

A powerful command-line interface for analyzing Git repositories with AI-powered insights, semantic search, and architectural analysis.

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys:
# - OPENAI_API_KEY (required for embeddings)
# - GITHUB_TOKEN (optional for PR analysis)
# - NEO4J credentials
```

3. **Make the launcher executable:**
```bash
chmod +x codebase-tm
```

## Quick Start

```bash
# Basic repository analysis
./codebase-tm analyze https://github.com/user/repo.git

# Deep analysis with embeddings and PRs
./codebase-tm analyze https://github.com/user/repo.git --deep --prs

# Interactive mode for exploration
./codebase-tm interactive https://github.com/user/repo.git
```

## Commands

### 1. Analyze Repository

Perform comprehensive repository analysis with optional deep learning features.

```bash
./codebase-tm analyze <repo_url> [options]

Options:
  --deep          Enable deep analysis with embeddings
  --prs           Analyze pull requests (requires GITHUB_TOKEN)
  --max-commits   Maximum commits to analyze (default: 500)
```

**Example:**
```bash
./codebase-tm analyze https://github.com/facebook/react.git --deep --max-commits 1000
```

**Output includes:**
- Repository overview and statistics
- Top contributors with metrics
- Key insights and patterns
- Development narrative (with LLM)
- Pull request analysis (if enabled)

### 2. Semantic Search

Search for commits using natural language queries.

```bash
./codebase-tm search <repo_url> "<query>" [--limit N]

Options:
  --limit    Number of results to return (default: 10)
```

**Examples:**
```bash
# Find authentication-related commits
./codebase-tm search https://github.com/user/repo.git "authentication and security"

# Find performance improvements
./codebase-tm search https://github.com/user/repo.git "optimize performance"

# Find bug fixes related to memory
./codebase-tm search https://github.com/user/repo.git "memory leak fix"
```

### 3. Ask Questions

Ask natural language questions about the repository.

```bash
./codebase-tm ask <repo_url> "<question>" [--context JSON]

Options:
  --context    Additional context as JSON
```

**Examples:**
```bash
# Architecture questions
./codebase-tm ask https://github.com/user/repo.git "What are the main architectural patterns?"

# Evolution questions
./codebase-tm ask https://github.com/user/repo.git "How has the authentication module evolved?"

# Collaboration questions
./codebase-tm ask https://github.com/user/repo.git "Who are the experts on the payment system?"

# Impact questions
./codebase-tm ask https://github.com/user/repo.git "What would be affected if we refactor the database layer?"
```

### 4. Architecture Analysis

Analyze repository architecture, patterns, and technical debt.

```bash
./codebase-tm architecture <repo_url>
```

**Output includes:**
- Detected architecture patterns (MVC, microservices, etc.)
- Complexity metrics and analysis
- Technical debt assessment
- Hotspot identification
- Actionable recommendations

**Example:**
```bash
./codebase-tm architecture https://github.com/nodejs/node.git
```

### 5. File Evolution

Track semantic evolution of specific files over time.

```bash
./codebase-tm file <repo_url> <file_path>
```

**Examples:**
```bash
# Track evolution of a core module
./codebase-tm file https://github.com/user/repo.git src/auth/login.py

# Analyze changes to configuration
./codebase-tm file https://github.com/user/repo.git config/database.yml
```

**Output includes:**
- Total changes and timeline
- Semantic drift measurement
- Similar files with comparable changes
- Change type distribution

### 6. Interactive Mode

Enter an interactive session for exploratory analysis.

```bash
./codebase-tm interactive <repo_url>
```

**Interactive Commands:**
- Natural language questions (just type normally)
- `search <query>` - Semantic search
- `file <path>` - Analyze specific file
- `architecture` - Architecture analysis
- `clusters` - Show semantic commit clusters
- `help` - Show available commands
- `exit` - Exit interactive mode

**Example Session:**
```
$ ./codebase-tm interactive https://github.com/user/repo.git

Entering interactive mode
Type 'help' for available commands, 'exit' to quit

Query: What are the most complex functions?
[Answer with detailed complexity analysis...]

Query: search authentication bug fix
[Results of semantic search...]

Query: file src/core/auth.py
[File evolution analysis...]

Query: Who works on the payment module?
[Contributor analysis...]

Query: exit
Goodbye!
```

## Advanced Usage

### Combining with Unix Tools

```bash
# Export analysis to JSON
./codebase-tm analyze https://github.com/user/repo.git --deep > analysis.json

# Search multiple queries
echo -e "authentication\nperformance\nsecurity" | while read query; do
  ./codebase-tm search https://github.com/user/repo.git "$query"
done

# Analyze multiple repositories
for repo in repo1 repo2 repo3; do
  ./codebase-tm architecture "https://github.com/org/$repo.git"
done
```

### Using Different Embedding Models

Set in `.env`:
```bash
# Options: openai, openai-large, openai-ada, sentence-transformer
EMBEDDING_MODEL=openai-large  # For highest quality
```

### Working with Private Repositories

For private GitHub repositories:
1. Generate a GitHub personal access token
2. Add to `.env`: `GITHUB_TOKEN=your-token-here`
3. Use HTTPS URLs with the token

## Output Formats

The CLI provides rich, colored output with:
- **Tables**: For structured data (contributors, commits, etc.)
- **Panels**: For narratives and summaries
- **Progress indicators**: For long-running operations
- **Syntax highlighting**: For code snippets
- **Markdown rendering**: For formatted text

## Performance Tips

1. **Start with basic analysis** before deep analysis
2. **Use `--max-commits` to limit scope** for large repositories
3. **Cache is automatic** - repeated queries are faster
4. **Batch operations** in scripts to minimize API calls

## Troubleshooting

### Neo4j Connection Issues
```bash
# Check Neo4j is running
neo4j status

# Verify credentials in .env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

### OpenAI API Issues
```bash
# Verify API key
echo $OPENAI_API_KEY

# Check rate limits
# The CLI automatically handles rate limiting with retries
```

### Memory Issues with Large Repos
```bash
# Limit analysis scope
./codebase-tm analyze <repo> --max-commits 100

# Or increase Python memory
export PYTHONMALLOC=malloc
```

## Examples for Common Tasks

### Find Technical Debt
```bash
./codebase-tm ask https://github.com/user/repo.git "What are the main sources of technical debt?"
```

### Identify Experts
```bash
./codebase-tm ask https://github.com/user/repo.git "Who should review changes to the authentication system?"
```

### Understand Recent Changes
```bash
./codebase-tm search https://github.com/user/repo.git "recent refactoring" --limit 20
```

### Analyze Code Quality
```bash
./codebase-tm architecture https://github.com/user/repo.git
```

### Track Feature Development
```bash
./codebase-tm ask https://github.com/user/repo.git "How was the payment feature implemented?"
```

## Integration with CI/CD

```yaml
# GitHub Actions example
- name: Analyze Repository
  run: |
    ./codebase-tm analyze ${{ github.repository }} --deep
    ./codebase-tm architecture ${{ github.repository }}
```

## API Keys and Costs

- **OpenAI**: ~$0.02-0.10 per 1000 commits analyzed
- **Neo4j**: Free for local deployment
- **GitHub**: Free tier allows 5000 requests/hour

## Support

For issues or questions:
1. Check the logs in the console output
2. Verify environment variables are set correctly
3. Ensure all services (Neo4j, APIs) are accessible
4. Try with a smaller repository first for testing