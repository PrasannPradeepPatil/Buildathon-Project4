#!/usr/bin/env python3
"""
Codebase Time Machine CLI - Analyze Git repositories with AI-powered insights
"""

import os
import sys
import argparse
import json
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from tabulate import tabulate
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from database import Database
from graph_database import GraphDatabaseManager
from vector_graph_database import VectorGraphDatabase
from enhanced_git_analyzer import EnhancedGitAnalyzer
from architecture_analyzer import ArchitectureAnalyzer
from llm_code_analyzer import LLMCodeAnalyzer
from semantic_query_engine import SemanticQueryEngine
from embedding_manager import EmbeddingManager

console = Console()


class CodebaseTimeMachineCLI:
    def __init__(self):
        self.db = Database()
        self.graph_db = None
        self.vector_db = None
        self.llm_analyzer = None
        self.semantic_engine = None
        self._initialize_connections()
    
    def _initialize_connections(self):
        """Initialize database connections"""
        try:
            self.graph_db = GraphDatabaseManager()
            self.vector_db = VectorGraphDatabase()
            self.llm_analyzer = LLMCodeAnalyzer()
            self.semantic_engine = SemanticQueryEngine(self.vector_db, self.llm_analyzer)
            console.print("[green]✓[/green] Connected to Neo4j with vector support")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Graph database not available: {e}")
            console.print("[yellow]Some features will be limited[/yellow]")
    
    def analyze_repository(self, repo_url: str, deep: bool = False, 
                          analyze_prs: bool = False, max_commits: int = 500):
        """Analyze a Git repository"""
        console.print(f"\n[bold blue]Analyzing repository:[/bold blue] {repo_url}")
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                # Basic or deep analysis
                if deep and self.vector_db:
                    task = progress.add_task("Performing deep analysis with embeddings...", total=None)
                    analyzer = EnhancedGitAnalyzer(self.vector_db)
                    repo_data = analyzer.analyze_repository_full(repo_url, temp_dir, max_commits)
                    progress.update(task, completed=True)
                else:
                    task = progress.add_task("Performing basic analysis...", total=None)
                    from git_analyzer import GitAnalyzer
                    analyzer = GitAnalyzer()
                    repo_data = analyzer.analyze_repository(repo_url, temp_dir)
                    progress.update(task, completed=True)
                
                # Analyze PRs if requested
                pr_analysis = []
                if analyze_prs and self.llm_analyzer:
                    task = progress.add_task("Analyzing pull requests...", total=None)
                    prs = self.llm_analyzer.fetch_github_prs(repo_url, limit=20)
                    for pr in prs:
                        pr_analysis.append(self.llm_analyzer.analyze_pull_request(pr))
                        if self.vector_db:
                            self.vector_db.store_pull_request(pr, repo_url)
                    progress.update(task, completed=True)
                
                # Generate narrative
                narrative = None
                if self.llm_analyzer and repo_data.get('commits'):
                    task = progress.add_task("Generating narrative...", total=None)
                    narrative = self.llm_analyzer.generate_change_narrative(repo_data['commits'])
                    progress.update(task, completed=True)
                
                # Store in database
                analysis_id = self.db.store_analysis(repo_url, {
                    **repo_data,
                    'pr_analysis': pr_analysis,
                    'narrative': narrative
                })
            
            # Display results
            self._display_analysis_results(repo_data, pr_analysis, narrative)
            
            return analysis_id
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def _display_analysis_results(self, repo_data: Dict, pr_analysis: List, narrative: str):
        """Display analysis results in a formatted way"""
        
        # Repository overview
        repo_info = repo_data.get('repository', {})
        console.print("\n[bold green]Repository Overview[/bold green]")
        overview_table = Table(show_header=False)
        overview_table.add_column("Property", style="cyan")
        overview_table.add_column("Value")
        overview_table.add_row("Name", repo_info.get('name', 'Unknown'))
        overview_table.add_row("Total Commits", str(repo_info.get('total_commits', 0)))
        overview_table.add_row("Analyzed At", repo_info.get('analyzed_at', 'Unknown'))
        console.print(overview_table)
        
        # Contributors
        if repo_data.get('contributors'):
            console.print("\n[bold green]Top Contributors[/bold green]")
            contrib_table = Table()
            contrib_table.add_column("Name", style="cyan")
            contrib_table.add_column("Commits", justify="right")
            contrib_table.add_column("Insertions", justify="right", style="green")
            contrib_table.add_column("Deletions", justify="right", style="red")
            
            for contributor in repo_data['contributors'][:5]:
                contrib_table.add_row(
                    contributor['name'],
                    str(contributor['commits']),
                    str(contributor['insertions']),
                    str(contributor['deletions'])
                )
            console.print(contrib_table)
        
        # Insights
        if repo_data.get('insights'):
            console.print("\n[bold green]Key Insights[/bold green]")
            insights = repo_data['insights']
            insights_table = Table(show_header=False)
            insights_table.add_column("Metric", style="cyan")
            insights_table.add_column("Value")
            insights_table.add_row("Most Active Contributor", insights.get('most_active_contributor', 'Unknown'))
            insights_table.add_row("Most Common Commit Type", insights.get('most_common_commit_type', 'Unknown'))
            insights_table.add_row("Avg Files per Commit", f"{insights.get('avg_files_per_commit', 0):.2f}")
            insights_table.add_row("Total Contributors", str(insights.get('total_contributors', 0)))
            console.print(insights_table)
        
        # Narrative
        if narrative:
            console.print("\n[bold green]Development Narrative[/bold green]")
            console.print(Panel(Markdown(narrative), border_style="green"))
        
        # PR Analysis
        if pr_analysis:
            console.print(f"\n[bold green]Pull Request Analysis ({len(pr_analysis)} PRs)[/bold green]")
            for pr in pr_analysis[:3]:
                console.print(f"  • PR #{pr.get('pr_number', 'Unknown')}: {pr.get('pr_title', 'No title')}")
                console.print(f"    Risk: {pr.get('risk_level', 'Unknown')}, Priority: {pr.get('review_priority', 'Unknown')}")
    
    def search_commits(self, repo_url: str, query: str, limit: int = 10):
        """Semantic search for commits"""
        if not self.vector_db:
            console.print("[red]Error: Vector database not available[/red]")
            return
        
        console.print(f"\n[bold blue]Searching for:[/bold blue] {query}")
        
        with console.status("Searching..."):
            results = self.vector_db.semantic_search_commits(query, repo_url, limit)
            recommendations = self.vector_db.get_contextual_recommendations(query, repo_url)
        
        if results:
            console.print(f"\n[bold green]Found {len(results)} relevant commits:[/bold green]")
            
            results_table = Table()
            results_table.add_column("SHA", style="cyan", width=12)
            results_table.add_column("Message", width=50)
            results_table.add_column("Type", style="yellow")
            results_table.add_column("Similarity", justify="right", style="green")
            
            for result in results:
                results_table.add_row(
                    result['sha'][:8],
                    result['message'][:50] + "..." if len(result['message']) > 50 else result['message'],
                    result.get('type', 'unknown'),
                    f"{result['similarity']:.3f}"
                )
            console.print(results_table)
            
            if recommendations.get('suggested_files'):
                console.print("\n[bold yellow]Suggested files to review:[/bold yellow]")
                for file in recommendations['suggested_files'][:5]:
                    console.print(f"  • {file}")
        else:
            console.print("[yellow]No matching commits found[/yellow]")
    
    def ask_question(self, repo_url: str, question: str, context: Optional[Dict] = None):
        """Ask a natural language question about the repository"""
        if not self.semantic_engine:
            console.print("[red]Error: Semantic engine not available[/red]")
            return
        
        console.print(f"\n[bold blue]Question:[/bold blue] {question}")
        
        with console.status("Thinking..."):
            answer = self.semantic_engine.answer_question(question, repo_url, context or {})
        
        # Display answer
        console.print(f"\n[bold green]Answer:[/bold green]")
        console.print(Panel(answer.get('summary', 'No answer available'), border_style="green"))
        
        # Display supporting data if available
        if answer.get('insights'):
            console.print("\n[bold yellow]Insights:[/bold yellow]")
            for insight in answer['insights']:
                console.print(f"  • [{insight['type']}] {insight['description']}")
        
        # Display results in table if available
        if answer.get('results'):
            console.print("\n[bold yellow]Detailed Results:[/bold yellow]")
            self._display_generic_results(answer['results'])
    
    def analyze_architecture(self, repo_url: str):
        """Analyze repository architecture"""
        if not self.graph_db:
            console.print("[red]Error: Graph database not available[/red]")
            return
        
        console.print(f"\n[bold blue]Analyzing architecture for:[/bold blue] {repo_url}")
        
        with console.status("Analyzing architecture..."):
            arch_analyzer = ArchitectureAnalyzer(self.graph_db)
            analysis = arch_analyzer.analyze_architecture(repo_url)
        
        # Display patterns
        if analysis.get('patterns_detected'):
            console.print("\n[bold green]Detected Architecture Patterns:[/bold green]")
            patterns_table = Table()
            patterns_table.add_column("Pattern", style="cyan")
            patterns_table.add_column("Confidence", justify="right", style="green")
            
            for pattern, confidence in analysis['patterns_detected'].items():
                patterns_table.add_row(pattern.replace('_', ' ').title(), f"{confidence:.1f}%")
            console.print(patterns_table)
        
        # Display complexity
        if analysis.get('complexity_analysis'):
            complexity = analysis['complexity_analysis']
            console.print("\n[bold green]Complexity Analysis:[/bold green]")
            console.print(f"  Average File Complexity: {complexity.get('average_file_complexity', 0):.2f}")
            console.print(f"  High Complexity Files: {len(complexity.get('high_complexity_files', []))}")
            console.print(f"  Refactoring Candidates: {len(complexity.get('refactoring_candidates', []))}")
        
        # Display technical debt
        if analysis.get('technical_debt'):
            debt = analysis['technical_debt']
            console.print(f"\n[bold yellow]Technical Debt Score: {debt.get('debt_score', 0)}/100[/bold yellow]")
            
            if debt.get('indicators'):
                console.print("\n[bold yellow]Debt Indicators:[/bold yellow]")
                for indicator in debt['indicators']:
                    severity_color = {'critical': 'red', 'high': 'yellow', 'medium': 'cyan'}.get(indicator['severity'], 'white')
                    console.print(f"  [{severity_color}]• {indicator['type']}: {indicator['description']}[/{severity_color}]")
        
        # Display recommendations
        if analysis.get('recommendations'):
            console.print("\n[bold green]Recommendations:[/bold green]")
            for rec in analysis['recommendations']:
                priority_color = {'high': 'red', 'medium': 'yellow', 'low': 'cyan'}.get(rec['priority'], 'white')
                console.print(f"\n  [{priority_color}][{rec['priority'].upper()}][/{priority_color}] {rec['recommendation']}")
                if rec.get('actions'):
                    for action in rec['actions']:
                        console.print(f"    → {action}")
    
    def analyze_file_evolution(self, repo_url: str, file_path: str):
        """Analyze semantic evolution of a file"""
        if not self.vector_db:
            console.print("[red]Error: Vector database not available[/red]")
            return
        
        console.print(f"\n[bold blue]Analyzing evolution of:[/bold blue] {file_path}")
        
        with console.status("Analyzing file evolution..."):
            evolution = self.vector_db.analyze_semantic_evolution(file_path)
            similar_files = self.vector_db.find_similar_changes(file_path)
        
        # Display evolution
        console.print(f"\n[bold green]Semantic Evolution:[/bold green]")
        console.print(f"  Total Changes: {evolution.get('total_changes', 0)}")
        console.print(f"  Semantic Drift: {evolution.get('semantic_drift', 0):.3f}")
        console.print(f"  Interpretation: {evolution.get('drift_interpretation', 'Unknown')}")
        
        # Display timeline
        if evolution.get('evolution_timeline'):
            console.print("\n[bold yellow]Change Timeline:[/bold yellow]")
            timeline_table = Table()
            timeline_table.add_column("Timestamp", style="cyan")
            timeline_table.add_column("Change Type", style="yellow")
            timeline_table.add_column("Similarity", justify="right", style="green")
            
            for change in evolution['evolution_timeline'][-10:]:  # Last 10 changes
                timeline_table.add_row(
                    change['timestamp'][:19],
                    change['change_type'],
                    f"{change.get('similarity', 0):.3f}"
                )
            console.print(timeline_table)
        
        # Display similar files
        if similar_files:
            console.print("\n[bold yellow]Files with Similar Changes:[/bold yellow]")
            for file_info in similar_files:
                console.print(f"  • {file_info['file']} (similarity: {file_info['similarity']:.3f})")
    
    def interactive_mode(self, repo_url: str):
        """Interactive query mode"""
        console.print("\n[bold green]Entering interactive mode[/bold green]")
        console.print("Type 'help' for available commands, 'exit' to quit\n")
        
        while True:
            try:
                command = Prompt.ask("[bold blue]Query[/bold blue]")
                
                if command.lower() in ['exit', 'quit', 'q']:
                    break
                elif command.lower() == 'help':
                    self._show_interactive_help()
                elif command.lower().startswith('search '):
                    query = command[7:]
                    self.search_commits(repo_url, query)
                elif command.lower().startswith('file '):
                    file_path = command[5:]
                    self.analyze_file_evolution(repo_url, file_path)
                elif command.lower() == 'architecture':
                    self.analyze_architecture(repo_url)
                elif command.lower() == 'clusters':
                    self._show_semantic_clusters(repo_url)
                else:
                    # Treat as natural language question
                    self.ask_question(repo_url, command)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        console.print("\n[green]Goodbye![/green]")
    
    def _show_interactive_help(self):
        """Show help for interactive mode"""
        help_text = """
[bold yellow]Available Commands:[/bold yellow]

  [cyan]Natural Language:[/cyan]
    Just type your question naturally, e.g.:
    • "What are the main architectural patterns?"
    • "Who are the top contributors?"
    • "Show me recent bugfixes"
    
  [cyan]Specific Commands:[/cyan]
    • search <query>     - Semantic search for commits
    • file <path>        - Analyze file evolution
    • architecture       - Analyze repository architecture
    • clusters           - Show semantic commit clusters
    • help              - Show this help
    • exit              - Exit interactive mode
        """
        console.print(help_text)
    
    def _show_semantic_clusters(self, repo_url: str):
        """Display semantic clusters"""
        if not self.vector_db:
            console.print("[red]Error: Vector database not available[/red]")
            return
        
        with console.status("Identifying clusters..."):
            clusters = self.vector_db.identify_semantic_clusters(repo_url)
        
        if clusters.get('clusters'):
            console.print(f"\n[bold green]Found {clusters['num_clusters']} Semantic Clusters:[/bold green]")
            
            for i, cluster in enumerate(clusters['clusters'], 1):
                console.print(f"\n[bold yellow]Cluster {i} ({cluster['size']} commits):[/bold yellow]")
                for commit in cluster['sample_commits'][:3]:
                    console.print(f"  • {commit['sha'][:8]}: {commit['message'][:60]}...")
        else:
            console.print("[yellow]Not enough data for clustering[/yellow]")
    
    def _display_generic_results(self, results: List[Dict]):
        """Display generic results in a table"""
        if not results:
            return
        
        # Get all keys from first result
        keys = list(results[0].keys())
        
        table = Table()
        for key in keys[:5]:  # Limit to 5 columns
            table.add_column(key.replace('_', ' ').title(), style="cyan")
        
        for result in results[:10]:  # Limit to 10 rows
            row = []
            for key in keys[:5]:
                value = str(result.get(key, ''))
                if len(value) > 30:
                    value = value[:27] + "..."
                row.append(value)
            table.add_row(*row)
        
        console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description='Codebase Time Machine - AI-powered Git repository analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze https://github.com/user/repo.git
  %(prog)s analyze https://github.com/user/repo.git --deep --prs
  %(prog)s search https://github.com/user/repo.git "authentication"
  %(prog)s ask https://github.com/user/repo.git "What are the main patterns?"
  %(prog)s interactive https://github.com/user/repo.git
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a repository')
    analyze_parser.add_argument('repo_url', help='Repository URL')
    analyze_parser.add_argument('--deep', action='store_true', help='Perform deep analysis with embeddings')
    analyze_parser.add_argument('--prs', action='store_true', help='Analyze pull requests')
    analyze_parser.add_argument('--max-commits', type=int, default=500, help='Maximum commits to analyze')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Semantic search for commits')
    search_parser.add_argument('repo_url', help='Repository URL')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Number of results')
    
    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a question about the repository')
    ask_parser.add_argument('repo_url', help='Repository URL')
    ask_parser.add_argument('question', help='Question to ask')
    ask_parser.add_argument('--context', type=json.loads, help='Additional context (JSON)')
    
    # Architecture command
    arch_parser = subparsers.add_parser('architecture', help='Analyze repository architecture')
    arch_parser.add_argument('repo_url', help='Repository URL')
    
    # File evolution command
    file_parser = subparsers.add_parser('file', help='Analyze file evolution')
    file_parser.add_argument('repo_url', help='Repository URL')
    file_parser.add_argument('file_path', help='File path to analyze')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Interactive query mode')
    interactive_parser.add_argument('repo_url', help='Repository URL')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = CodebaseTimeMachineCLI()
    
    try:
        if args.command == 'analyze':
            cli.analyze_repository(args.repo_url, args.deep, args.prs, args.max_commits)
        elif args.command == 'search':
            cli.search_commits(args.repo_url, args.query, args.limit)
        elif args.command == 'ask':
            cli.ask_question(args.repo_url, args.question, args.context)
        elif args.command == 'architecture':
            cli.analyze_architecture(args.repo_url)
        elif args.command == 'file':
            cli.analyze_file_evolution(args.repo_url, args.file_path)
        elif args.command == 'interactive':
            cli.interactive_mode(args.repo_url)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()