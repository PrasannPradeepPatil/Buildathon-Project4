import os
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import openai
from langchain import PromptTemplate, LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
import tiktoken
from github import Github

load_dotenv()

class LLMCodeAnalyzer:
    def __init__(self, model='gpt-3.5-turbo'):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.model = model
        
        if self.api_key:
            openai.api_key = self.api_key
            self.llm = ChatOpenAI(
                model=model,
                temperature=0.3,
                openai_api_key=self.api_key
            )
        else:
            print("Warning: OpenAI API key not found. LLM features will be limited.")
            self.llm = None
        
        if self.github_token:
            self.github = Github(self.github_token)
        else:
            self.github = None
        
        self.encoding = tiktoken.encoding_for_model(model if 'gpt' in model else 'gpt-3.5-turbo')
    
    def analyze_code_diff(self, diff: str, file_path: str, 
                         commit_message: str) -> Dict[str, Any]:
        if not self.llm:
            return self._basic_diff_analysis(diff, file_path, commit_message)
        
        if self._count_tokens(diff) > 3000:
            diff = self._truncate_diff(diff, 3000)
        
        prompt = f"""
        Analyze the following code change:
        
        File: {file_path}
        Commit Message: {commit_message}
        
        Diff:
        ```
        {diff}
        ```
        
        Provide a structured analysis with:
        1. Change Summary (2-3 sentences)
        2. Change Type (feature/bugfix/refactor/performance/security/documentation)
        3. Impact Assessment (low/medium/high)
        4. Potential Issues or Risks
        5. Architecture Impact (if any)
        6. Suggested Improvements (if any)
        
        Format as JSON.
        """
        
        try:
            response = self.llm.predict(prompt)
            analysis = self._parse_llm_response(response)
            
            analysis['file_path'] = file_path
            analysis['commit_message'] = commit_message
            analysis['analyzed_at'] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._basic_diff_analysis(diff, file_path, commit_message)
    
    def _basic_diff_analysis(self, diff: str, file_path: str, 
                            commit_message: str) -> Dict[str, Any]:
        lines = diff.split('\n')
        additions = len([l for l in lines if l.startswith('+')])
        deletions = len([l for l in lines if l.startswith('-')])
        
        change_type = 'unknown'
        if 'fix' in commit_message.lower() or 'bug' in commit_message.lower():
            change_type = 'bugfix'
        elif 'feat' in commit_message.lower() or 'add' in commit_message.lower():
            change_type = 'feature'
        elif 'refactor' in commit_message.lower():
            change_type = 'refactor'
        
        return {
            'file_path': file_path,
            'commit_message': commit_message,
            'change_summary': f"Modified {file_path} with {additions} additions and {deletions} deletions",
            'change_type': change_type,
            'impact_assessment': 'medium' if (additions + deletions) > 50 else 'low',
            'additions': additions,
            'deletions': deletions,
            'analyzed_at': datetime.now().isoformat()
        }
    
    def analyze_commit_intent(self, commit_message: str, 
                             files_changed: List[str],
                             diffs: List[str]) -> Dict[str, Any]:
        if not self.llm:
            return self._basic_intent_analysis(commit_message, files_changed)
        
        files_summary = ', '.join(files_changed[:10])
        if len(files_changed) > 10:
            files_summary += f" and {len(files_changed) - 10} more files"
        
        sample_diffs = '\n'.join(diffs[:3])
        if self._count_tokens(sample_diffs) > 1000:
            sample_diffs = self._truncate_diff(sample_diffs, 1000)
        
        prompt = f"""
        Analyze the intent and context of this commit:
        
        Commit Message: {commit_message}
        Files Changed: {files_summary}
        
        Sample Changes:
        ```
        {sample_diffs}
        ```
        
        Determine:
        1. Primary Intent (what was the developer trying to achieve?)
        2. Secondary Effects (any side effects or related changes?)
        3. Development Phase (new feature/maintenance/bugfix/refactoring)
        4. Quality Indicators (does this look like quality code?)
        5. Completeness (does the commit seem complete or part of larger work?)
        
        Format as JSON.
        """
        
        try:
            response = self.llm.predict(prompt)
            analysis = self._parse_llm_response(response)
            
            analysis['commit_message'] = commit_message
            analysis['files_changed_count'] = len(files_changed)
            
            return analysis
            
        except Exception as e:
            print(f"Intent analysis failed: {e}")
            return self._basic_intent_analysis(commit_message, files_changed)
    
    def _basic_intent_analysis(self, commit_message: str, 
                              files_changed: List[str]) -> Dict[str, Any]:
        intent = 'general'
        phase = 'maintenance'
        
        message_lower = commit_message.lower()
        if 'implement' in message_lower or 'add' in message_lower:
            intent = 'new_feature'
            phase = 'development'
        elif 'fix' in message_lower or 'bug' in message_lower:
            intent = 'bugfix'
            phase = 'maintenance'
        elif 'refactor' in message_lower:
            intent = 'refactoring'
            phase = 'improvement'
        
        return {
            'primary_intent': intent,
            'development_phase': phase,
            'files_changed_count': len(files_changed),
            'commit_message': commit_message
        }
    
    def analyze_architecture_impact(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.llm:
            return self._basic_architecture_impact(changes)
        
        changes_summary = []
        for change in changes[:20]:
            changes_summary.append({
                'file': change.get('file_path', ''),
                'type': change.get('change_type', ''),
                'message': change.get('commit_message', '')[:100]
            })
        
        prompt = f"""
        Analyze the architectural impact of these changes:
        
        {json.dumps(changes_summary, indent=2)}
        
        Assess:
        1. Architectural Pattern Changes (MVC, microservices, etc.)
        2. Module Coupling Impact
        3. Code Organization Changes
        4. Dependency Changes
        5. Breaking Changes Risk
        6. Technical Debt Impact
        
        Provide recommendations for maintaining architectural integrity.
        
        Format as JSON.
        """
        
        try:
            response = self.llm.predict(prompt)
            analysis = self._parse_llm_response(response)
            
            analysis['changes_analyzed'] = len(changes)
            analysis['analysis_timestamp'] = datetime.now().isoformat()
            
            return analysis
            
        except Exception as e:
            print(f"Architecture impact analysis failed: {e}")
            return self._basic_architecture_impact(changes)
    
    def _basic_architecture_impact(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        file_types = {}
        for change in changes:
            file_path = change.get('file_path', '')
            if '/' in file_path:
                module = file_path.split('/')[0]
                file_types[module] = file_types.get(module, 0) + 1
        
        return {
            'modules_affected': list(file_types.keys()),
            'change_distribution': file_types,
            'changes_analyzed': len(changes),
            'risk_level': 'high' if len(file_types) > 5 else 'medium'
        }
    
    def generate_change_narrative(self, commits: List[Dict[str, Any]]) -> str:
        if not self.llm:
            return self._basic_narrative(commits)
        
        commit_summaries = []
        for commit in commits[:30]:
            commit_summaries.append({
                'message': commit.get('message', '')[:100],
                'type': commit.get('type', ''),
                'author': commit.get('author_name', ''),
                'date': commit.get('timestamp', '')[:10]
            })
        
        prompt = f"""
        Generate a narrative summary of this development history:
        
        {json.dumps(commit_summaries, indent=2)}
        
        Create a coherent story that describes:
        1. The overall development journey
        2. Key milestones and features added
        3. Major refactorings or architectural changes
        4. Bug fixing patterns
        5. Team collaboration patterns
        
        Write in a professional, technical tone. Maximum 300 words.
        """
        
        try:
            narrative = self.llm.predict(prompt)
            return narrative
            
        except Exception as e:
            print(f"Narrative generation failed: {e}")
            return self._basic_narrative(commits)
    
    def _basic_narrative(self, commits: List[Dict[str, Any]]) -> str:
        feature_count = len([c for c in commits if c.get('type') == 'feature'])
        bug_count = len([c for c in commits if c.get('type') == 'bugfix'])
        refactor_count = len([c for c in commits if c.get('type') == 'refactor'])
        
        return f"""
        Repository Development Summary:
        
        This repository has undergone {len(commits)} commits with the following distribution:
        - {feature_count} feature additions
        - {bug_count} bug fixes
        - {refactor_count} refactoring efforts
        
        The development shows a {'feature-focused' if feature_count > bug_count else 'maintenance-focused'} 
        pattern with {'frequent' if refactor_count > 5 else 'occasional'} code improvements.
        """
    
    def analyze_pull_request(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.llm:
            return self._basic_pr_analysis(pr_data)
        
        prompt = f"""
        Analyze this pull request:
        
        Title: {pr_data.get('title', '')}
        Description: {pr_data.get('description', '')[:500]}
        Files Changed: {pr_data.get('files_changed', 0)}
        Commits: {pr_data.get('commits_count', 0)}
        
        Assess:
        1. PR Quality (clear description, focused changes)
        2. Scope Assessment (appropriate size)
        3. Risk Level
        4. Review Priority
        5. Suggested Review Focus Areas
        
        Format as JSON.
        """
        
        try:
            response = self.llm.predict(prompt)
            analysis = self._parse_llm_response(response)
            
            analysis['pr_number'] = pr_data.get('number')
            analysis['pr_title'] = pr_data.get('title')
            
            return analysis
            
        except Exception as e:
            print(f"PR analysis failed: {e}")
            return self._basic_pr_analysis(pr_data)
    
    def _basic_pr_analysis(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        files_changed = pr_data.get('files_changed', 0)
        
        return {
            'pr_number': pr_data.get('number'),
            'pr_title': pr_data.get('title'),
            'scope': 'large' if files_changed > 20 else 'medium' if files_changed > 5 else 'small',
            'risk_level': 'high' if files_changed > 30 else 'medium',
            'review_priority': 'high' if 'fix' in pr_data.get('title', '').lower() else 'normal'
        }
    
    def fetch_github_prs(self, repo_url: str, state='all', limit=100) -> List[Dict[str, Any]]:
        if not self.github:
            return []
        
        try:
            repo_parts = repo_url.replace('https://github.com/', '').replace('.git', '').split('/')
            repo = self.github.get_repo(f"{repo_parts[0]}/{repo_parts[1]}")
            
            prs = []
            for pr in repo.get_pulls(state=state)[:limit]:
                pr_data = {
                    'number': pr.number,
                    'title': pr.title,
                    'description': pr.body or '',
                    'state': pr.state,
                    'created_at': pr.created_at.isoformat(),
                    'merged_at': pr.merged_at.isoformat() if pr.merged_at else None,
                    'author': pr.user.login,
                    'files_changed': pr.changed_files,
                    'commits_count': pr.commits,
                    'additions': pr.additions,
                    'deletions': pr.deletions,
                    'commits': []
                }
                
                for commit in pr.get_commits():
                    pr_data['commits'].append(commit.sha)
                
                prs.append(pr_data)
            
            return prs
            
        except Exception as e:
            print(f"Failed to fetch PRs: {e}")
            return []
    
    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))
    
    def _truncate_diff(self, diff: str, max_tokens: int) -> str:
        tokens = self.encoding.encode(diff)
        if len(tokens) <= max_tokens:
            return diff
        
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens) + "\n... (truncated)"
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        parsed = {}
        lines = response.split('\n')
        current_key = None
        current_value = []
        
        for line in lines:
            if ':' in line and not line.startswith(' '):
                if current_key:
                    parsed[current_key] = ' '.join(current_value).strip()
                
                parts = line.split(':', 1)
                current_key = parts[0].strip().lower().replace(' ', '_')
                current_value = [parts[1].strip()] if len(parts) > 1 else []
            elif current_key:
                current_value.append(line.strip())
        
        if current_key:
            parsed[current_key] = ' '.join(current_value).strip()
        
        return parsed
    
    def suggest_improvements(self, file_analysis: Dict[str, Any]) -> List[str]:
        suggestions = []
        
        if file_analysis.get('impact_assessment') == 'high':
            suggestions.append("Consider breaking this change into smaller, incremental commits")
        
        if file_analysis.get('change_type') == 'bugfix':
            suggestions.append("Add test cases to prevent regression")
        
        if 'security' in file_analysis.get('change_type', ''):
            suggestions.append("Ensure security review and penetration testing")
        
        if file_analysis.get('potential_issues'):
            suggestions.append("Address identified potential issues before merging")
        
        return suggestions