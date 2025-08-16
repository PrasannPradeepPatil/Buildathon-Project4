
import os
import logging
import openai
from typing import Dict, List, Any, Optional
import requests
import json
from datetime import datetime
import re

# Configure logging
logger = logging.getLogger(__name__)

class LLMCodeAnalyzer:
    def __init__(self):
        """Initialize the LLM Code Analyzer with OpenAI API"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OpenAI API key not found. LLM features will be limited.")
            self.client = None
        else:
            try:
                openai.api_key = self.api_key
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("LLM Code Analyzer initialized successfully with OpenAI")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    def is_available(self) -> bool:
        """Check if LLM analyzer is available"""
        return self.client is not None

    def analyze_commit(self, commit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single commit using LLM"""
        logger.info(f"Analyzing commit: {commit_data.get('hash', 'unknown')}")
        
        if not self.is_available():
            logger.warning("LLM not available for commit analysis")
            return {
                'summary': 'LLM analysis not available',
                'impact': 'unknown',
                'type': 'unknown'
            }

        try:
            # Prepare commit context
            commit_message = commit_data.get('message', '')
            files_changed = commit_data.get('files_changed', [])
            
            # Create prompt for commit analysis
            prompt = f"""
            Analyze this git commit and provide insights:
            
            Commit Message: {commit_message}
            Files Changed: {', '.join(files_changed) if files_changed else 'No files listed'}
            
            Please provide:
            1. A brief summary of what this commit does
            2. The impact level (low/medium/high)
            3. The type of change (feature/bugfix/refactor/docs/test)
            
            Respond in JSON format:
            {{
                "summary": "brief description",
                "impact": "low/medium/high",
                "type": "feature/bugfix/refactor/docs/test"
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a code analysis expert. Analyze git commits and provide structured insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )

            result = response.choices[0].message.content
            try:
                analysis = json.loads(result)
                logger.debug(f"Commit analysis complete: {analysis.get('type', 'unknown')}")
                return analysis
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response as JSON")
                return {
                    'summary': result,
                    'impact': 'medium',
                    'type': 'unknown'
                }

        except Exception as e:
            logger.error(f"LLM commit analysis failed: {e}")
            return {
                'summary': f'Analysis failed: {str(e)}',
                'impact': 'unknown',
                'type': 'unknown'
            }

    def generate_change_narrative(self, commits: List[Dict[str, Any]], max_commits: int = 50) -> Dict[str, Any]:
        """Generate a narrative summary of repository changes"""
        logger.info(f"Generating change narrative for {len(commits)} commits")
        
        if not self.is_available():
            logger.warning("LLM not available for narrative generation")
            return {
                'narrative': 'LLM analysis not available',
                'key_themes': [],
                'evolution_summary': 'Analysis requires OpenAI API key'
            }

        try:
            # Limit commits for analysis
            recent_commits = commits[:max_commits] if len(commits) > max_commits else commits
            
            # Extract key information from commits
            commit_summaries = []
            for commit in recent_commits:
                summary = f"- {commit.get('message', 'No message')[:100]}"
                if commit.get('files_changed'):
                    summary += f" (Modified: {len(commit['files_changed'])} files)"
                commit_summaries.append(summary)

            commits_text = '\n'.join(commit_summaries)

            prompt = f"""
            Analyze this repository's evolution based on recent commits:
            
            {commits_text}
            
            Please provide:
            1. A narrative summary of the repository's evolution
            2. Key themes and patterns in the changes
            3. Overall development direction
            
            Respond in JSON format:
            {{
                "narrative": "A comprehensive summary of the repository evolution",
                "key_themes": ["theme1", "theme2", "theme3"],
                "evolution_summary": "Brief overview of development direction"
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a software development analyst. Analyze repository evolution and provide insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.4
            )

            result = response.choices[0].message.content
            try:
                narrative = json.loads(result)
                logger.info("Change narrative generated successfully")
                return narrative
            except json.JSONDecodeError:
                logger.warning("Failed to parse narrative response as JSON")
                return {
                    'narrative': result,
                    'key_themes': ['Analysis completed'],
                    'evolution_summary': 'Repository analysis complete'
                }

        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            return {
                'narrative': f'Narrative generation failed: {str(e)}',
                'key_themes': [],
                'evolution_summary': 'Analysis unavailable'
            }

    def fetch_github_prs(self, repo_url: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch pull requests from GitHub repository"""
        logger.info(f"Fetching PRs for repository: {repo_url}")
        
        try:
            # Extract owner and repo from URL
            if 'github.com' not in repo_url:
                logger.warning("Not a GitHub repository, skipping PR fetch")
                return []

            # Parse GitHub URL
            match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
            if not match:
                logger.warning("Could not parse GitHub repository URL")
                return []

            owner, repo = match.groups()
            repo = repo.replace('.git', '')

            # GitHub API endpoint
            api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            params = {
                'state': 'all',
                'per_page': limit,
                'sort': 'updated',
                'direction': 'desc'
            }

            # Add GitHub token if available
            headers = {}
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                headers['Authorization'] = f'token {github_token}'

            response = requests.get(api_url, params=params, headers=headers)
            response.raise_for_status()

            prs = response.json()
            logger.info(f"Fetched {len(prs)} pull requests")
            return prs

        except Exception as e:
            logger.error(f"Failed to fetch GitHub PRs: {e}")
            return []

    def analyze_pull_request(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a pull request using LLM"""
        logger.debug(f"Analyzing PR: #{pr_data.get('number', 'unknown')}")
        
        if not self.is_available():
            return {
                'summary': 'LLM analysis not available',
                'complexity': 'unknown',
                'type': 'unknown'
            }

        try:
            title = pr_data.get('title', '')
            body = pr_data.get('body', '')[:500]  # Limit body length
            
            prompt = f"""
            Analyze this pull request:
            
            Title: {title}
            Description: {body}
            
            Provide:
            1. Summary of the PR purpose
            2. Complexity level (low/medium/high)
            3. Change type (feature/bugfix/refactor/docs)
            
            JSON response:
            {{
                "summary": "brief description",
                "complexity": "low/medium/high",
                "type": "feature/bugfix/refactor/docs"
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Analyze pull requests and provide structured insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )

            result = response.choices[0].message.content
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {
                    'summary': result,
                    'complexity': 'medium',
                    'type': 'unknown'
                }

        except Exception as e:
            logger.error(f"PR analysis failed: {e}")
            return {
                'summary': f'Analysis failed: {str(e)}',
                'complexity': 'unknown',
                'type': 'unknown'
            }

    def analyze_code_quality(self, file_content: str, file_path: str) -> Dict[str, Any]:
        """Analyze code quality using LLM"""
        if not self.is_available():
            return {'quality_score': 0, 'suggestions': [], 'issues': []}

        try:
            # Limit content length
            content = file_content[:2000] if len(file_content) > 2000 else file_content
            
            prompt = f"""
            Analyze this code file for quality:
            
            File: {file_path}
            Content:
            {content}
            
            Provide quality assessment in JSON:
            {{
                "quality_score": 1-10,
                "suggestions": ["suggestion1", "suggestion2"],
                "issues": ["issue1", "issue2"]
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a code quality analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )

            result = response.choices[0].message.content
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {
                    'quality_score': 7,
                    'suggestions': ['Code analysis completed'],
                    'issues': []
                }

        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
            return {
                'quality_score': 0,
                'suggestions': [],
                'issues': [f'Analysis failed: {str(e)}']
            }
