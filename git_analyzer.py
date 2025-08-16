import git
import os
from datetime import datetime
from collections import defaultdict, Counter
import re

class GitAnalyzer:
    def __init__(self):
        self.commit_patterns = {
            'feature': r'(feat|feature|add)',
            'bugfix': r'(fix|bug|patch)',
            'refactor': r'(refactor|restructure|cleanup)',
            'docs': r'(doc|readme|comment)',
            'test': r'(test|spec)',
            'style': r'(style|format|lint)'
        }
    
    def analyze_repository(self, repo_url, local_path):
        """Main analysis function"""
        try:
            # Clone repository
            repo = git.Repo.clone_from(repo_url, local_path)
            
            # Analyze commits
            commits_data = self._analyze_commits(repo)
            
            # Analyze contributors
            contributors_data = self._analyze_contributors(commits_data)
            
            # Analyze file changes
            files_data = self._analyze_files(repo)
            
            # Generate timeline
            timeline_data = self._generate_timeline(commits_data)
            
            return {
                'repository': {
                    'url': repo_url,
                    'name': repo_url.split('/')[-1].replace('.git', ''),
                    'total_commits': len(commits_data),
                    'analyzed_at': datetime.now().isoformat()
                },
                'commits': commits_data[:50],  # Limit for demo
                'contributors': contributors_data,
                'files': files_data,
                'timeline': timeline_data,
                'insights': self._generate_insights(commits_data, contributors_data)
            }
            
        except Exception as e:
            raise Exception(f"Analysis failed: {str(e)}")
    
    def _analyze_commits(self, repo):
        """Analyze commit history"""
        commits = []
        
        for commit in list(repo.iter_commits())[:100]:  # Limit for demo
            commit_type = self._classify_commit(commit.message)
            
            commits.append({
                'hash': commit.hexsha[:8],
                'message': commit.message.strip(),
                'author': commit.author.name,
                'email': commit.author.email,
                'date': commit.committed_datetime.isoformat(),
                'type': commit_type,
                'files_changed': len(commit.stats.files),
                'insertions': commit.stats.total['insertions'],
                'deletions': commit.stats.total['deletions']
            })
        
        return commits
    
    def _classify_commit(self, message):
        """Classify commit type based on message"""
        message_lower = message.lower()
        
        for commit_type, pattern in self.commit_patterns.items():
            if re.search(pattern, message_lower):
                return commit_type
        
        return 'other'
    
    def _analyze_contributors(self, commits_data):
        """Analyze contributor statistics"""
        contributors = defaultdict(lambda: {
            'commits': 0,
            'insertions': 0,
            'deletions': 0,
            'files_changed': 0
        })
        
        for commit in commits_data:
            author = commit['author']
            contributors[author]['commits'] += 1
            contributors[author]['insertions'] += commit['insertions']
            contributors[author]['deletions'] += commit['deletions']
            contributors[author]['files_changed'] += commit['files_changed']
        
        # Convert to list and sort by commits
        result = []
        for name, stats in contributors.items():
            result.append({
                'name': name,
                **stats
            })
        
        return sorted(result, key=lambda x: x['commits'], reverse=True)
    
    def _analyze_files(self, repo):
        """Analyze file statistics"""
        files_data = []
        
        try:
            for item in repo.tree().traverse():
                if item.type == 'blob':  # It's a file
                    file_path = item.path
                    extension = os.path.splitext(file_path)[1]
                    
                    files_data.append({
                        'path': file_path,
                        'extension': extension,
                        'size': item.size
                    })
        except:
            pass  # Skip if unable to traverse
        
        return files_data[:100]  # Limit for demo
    
    def _generate_timeline(self, commits_data):
        """Generate commit timeline"""
        timeline = defaultdict(int)
        
        for commit in commits_data:
            date = commit['date'][:10]  # YYYY-MM-DD
            timeline[date] += 1
        
        return dict(timeline)
    
    def _generate_insights(self, commits_data, contributors_data):
        """Generate repository insights"""
        if not commits_data:
            return {}
        
        commit_types = Counter(commit['type'] for commit in commits_data)
        
        return {
            'most_active_contributor': contributors_data[0]['name'] if contributors_data else 'Unknown',
            'most_common_commit_type': commit_types.most_common(1)[0][0] if commit_types else 'unknown',
            'avg_files_per_commit': sum(c['files_changed'] for c in commits_data) / len(commits_data),
            'total_contributors': len(contributors_data),
            'commit_type_distribution': dict(commit_types)
        }