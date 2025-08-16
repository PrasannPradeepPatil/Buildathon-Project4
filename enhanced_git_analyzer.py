import git
import os
import re
import ast
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import mimetypes

class EnhancedGitAnalyzer:
    def __init__(self, graph_db=None):
        self.graph_db = graph_db
        self.language_extensions = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.rs': 'rust',
            '.scala': 'scala',
            '.r': 'r',
            '.sql': 'sql',
            '.html': 'html',
            '.css': 'css',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.vue': 'vue',
            '.dart': 'dart'
        }
        
        self.commit_patterns = {
            'feature': r'(feat|feature|add|implement)',
            'bugfix': r'(fix|bug|patch|resolve)',
            'refactor': r'(refactor|restructure|cleanup|improve)',
            'docs': r'(doc|readme|comment)',
            'test': r'(test|spec|testing)',
            'style': r'(style|format|lint)',
            'perf': r'(perf|performance|optimize)',
            'chore': r'(chore|build|ci|deps)',
            'security': r'(security|vulnerability|cve)',
            'breaking': r'(breaking|major|incompatible)'
        }
    
    def analyze_repository_full(self, repo_url: str, local_path: str, 
                               max_commits: int = 500, progress_callback=None) -> Dict[str, Any]:
        try:
            repo = git.Repo.clone_from(repo_url, local_path)
            
            if progress_callback:
                progress_callback("Repository cloned, initializing graph storage...")
            
            repo_data = {
                'url': repo_url,
                'name': repo_url.split('/')[-1].replace('.git', ''),
                'default_branch': self._get_default_branch(repo)
            }
            
            if self.graph_db:
                if progress_callback:
                    progress_callback("Storing repository metadata in graph database...")
                repo_id = self.graph_db.store_repository(repo_data)
            
            if progress_callback:
                progress_callback("Analyzing commits and building graph relationships...")
            commits_data = self._analyze_commits_detailed(repo, repo_url, max_commits, progress_callback)
            
            if progress_callback:
                progress_callback("Processing file structure and code analysis...")
            file_structure = self._analyze_file_structure(repo, repo_url, progress_callback)
            
            if progress_callback:
                progress_callback("Mapping dependencies in graph...")
            dependencies = self._analyze_dependencies(repo, repo_url, progress_callback)
            
            if progress_callback:
                progress_callback("Computing architecture metrics...")
            architecture_metrics = self._calculate_architecture_metrics(repo, repo_url)
            
            if progress_callback:
                progress_callback("Analyzing evolution patterns...")
            evolution_patterns = self._analyze_evolution_patterns(commits_data)
            
            return {
                'repository': repo_data,
                'commits': commits_data[:100],  
                'file_structure': file_structure,
                'dependencies': dependencies,
                'architecture_metrics': architecture_metrics,
                'evolution_patterns': evolution_patterns,
                'total_commits_analyzed': len(commits_data)
            }
            
        except Exception as e:
            raise Exception(f"Enhanced analysis failed: {str(e)}")
    
    def _get_default_branch(self, repo) -> str:
        try:
            return repo.head.reference.name
        except:
            return 'main'
    
    def _analyze_commits_detailed(self, repo, repo_url: str, max_commits: int, progress_callback=None) -> List[Dict[str, Any]]:
        commits = []
        commit_count = 0
        
        for commit in repo.iter_commits():
            if commit_count >= max_commits:
                break
            
            if progress_callback and commit_count % 50 == 0:
                progress_callback(f"Processed {commit_count}/{max_commits} commits...")
            
            commit_type = self._classify_commit_advanced(commit.message)
            
            commit_data = {
                'sha': commit.hexsha,
                'message': commit.message.strip(),
                'author_name': commit.author.name,
                'author_email': commit.author.email,
                'timestamp': commit.committed_datetime.isoformat(),
                'type': commit_type,
                'insertions': 0,
                'deletions': 0,
                'files_changed': 0
            }
            
            try:
                if commit.parents:
                    parent = commit.parents[0]
                    diff = parent.diff(commit)
                    
                    for diff_item in diff:
                        file_path = diff_item.b_path or diff_item.a_path
                        
                        insertions = 0
                        deletions = 0
                        if hasattr(diff_item, 'diff') and diff_item.diff:
                            diff_str = diff_item.diff.decode('utf-8', errors='ignore')
                            insertions = len([l for l in diff_str.split('\n') if l.startswith('+')])
                            deletions = len([l for l in diff_str.split('\n') if l.startswith('-')])
                        
                        commit_data['insertions'] += insertions
                        commit_data['deletions'] += deletions
                        commit_data['files_changed'] += 1
                        
                        file_data = {
                            'path': file_path,
                            'extension': os.path.splitext(file_path)[1],
                            'language': self._detect_language(file_path),
                            'insertions': insertions,
                            'deletions': deletions,
                            'change_type': self._get_change_type(diff_item)
                        }
                        
                        if self.graph_db:
                            self.graph_db.store_file_change(commit.hexsha, file_data)
            except Exception as e:
                print(f"Error processing commit {commit.hexsha}: {e}")
            
            if self.graph_db:
                self.graph_db.store_commit(commit_data, repo_url)
            
            commits.append(commit_data)
            commit_count += 1
        
        return commits
    
    def _classify_commit_advanced(self, message: str) -> str:
        message_lower = message.lower()
        
        for commit_type, pattern in self.commit_patterns.items():
            if re.search(pattern, message_lower):
                return commit_type
        
        if re.search(r'merge|merging', message_lower):
            return 'merge'
        elif re.search(r'initial|init|first', message_lower):
            return 'initial'
        
        return 'other'
    
    def _get_change_type(self, diff_item) -> str:
        if diff_item.new_file:
            return 'add'
        elif diff_item.deleted_file:
            return 'delete'
        elif diff_item.renamed_file:
            return 'rename'
        else:
            return 'modify'
    
    def _detect_language(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        return self.language_extensions.get(ext, 'unknown')
    
    def _analyze_file_structure(self, repo, repo_url: str, progress_callback=None) -> Dict[str, Any]:
        structure = {
            'total_files': 0,
            'by_language': defaultdict(int),
            'by_extension': defaultdict(int),
            'directories': set(),
            'code_files': []
        }
        
        try:
            file_count = 0
            for item in repo.tree().traverse():
                if item.type == 'blob':
                    file_path = item.path
                    extension = os.path.splitext(file_path)[1]
                    language = self._detect_language(file_path)
                    
                    structure['total_files'] += 1
                    structure['by_extension'][extension] += 1
                    structure['by_language'][language] += 1
                    file_count += 1
                    
                    if progress_callback and file_count % 100 == 0:
                        progress_callback(f"Analyzed {file_count} files for structure...")
                    
                    directory = os.path.dirname(file_path)
                    if directory:
                        structure['directories'].add(directory)
                    
                    if language != 'unknown' and extension in self.language_extensions:
                        code_file_data = {
                            'path': file_path,
                            'size': item.size,
                            'language': language
                        }
                        structure['code_files'].append(code_file_data)
                        
                        if self.graph_db and language == 'python':
                            self._analyze_python_file(repo, file_path)
        except Exception as e:
            print(f"Error analyzing file structure: {e}")
        
        structure['directories'] = list(structure['directories'])
        structure['by_language'] = dict(structure['by_language'])
        structure['by_extension'] = dict(structure['by_extension'])
        
        return structure
    
    def _analyze_python_file(self, repo, file_path: str):
        try:
            content = repo.odb.stream(repo.tree()[file_path].binsha).read().decode('utf-8', errors='ignore')
            tree = ast.parse(content)
            
            structure_data = {
                'module': file_path,
                'classes': [],
                'functions': [],
                'imports': []
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_data = {
                        'name': node.name,
                        'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                        'attributes': [],
                        'line_start': node.lineno,
                        'line_end': node.end_lineno or node.lineno
                    }
                    structure_data['classes'].append(class_data)
                
                elif isinstance(node, ast.FunctionDef):
                    # Check if this function is not inside a class
                    is_method = False
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef) and node in parent.body:
                            is_method = True
                            break
                    
                    if not is_method:
                        func_data = {
                            'name': node.name,
                            'parameters': [arg.arg for arg in node.args.args] if node.args.args else [],
                            'line_start': node.lineno,
                            'line_end': node.end_lineno or node.lineno,
                            'complexity': self._calculate_complexity(node)
                        }
                        structure_data['functions'].append(func_data)
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    try:
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if hasattr(alias, 'name') and alias.name:
                                    structure_data['imports'].append(alias.name)
                        else:
                            if hasattr(node, 'module') and node.module:
                                structure_data['imports'].append(node.module)
                    except Exception as import_error:
                        logger.warning(f"Error processing import in {file_path}: {import_error}")
                        continue
            
            if self.graph_db:
                try:
                    self.graph_db.store_code_structure(file_path, structure_data)
                    
                    for imp in structure_data['imports']:
                        try:
                            if not imp or '.' not in imp or imp.startswith('.'):
                                continue
                            potential_file = imp.replace('.', '/') + '.py'
                            self.graph_db.store_dependency(file_path, potential_file, 'import')
                        except Exception as dep_error:
                            logger.warning(f"Error storing dependency {imp}: {dep_error}")
                except Exception as store_error:
                    logger.warning(f"Error storing code structure for {file_path}: {store_error}")
                    
        except Exception as e:
            print(f"Error analyzing Python file {file_path}: {e}")
    
    def _calculate_complexity(self, node) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _analyze_dependencies(self, repo, repo_url: str, progress_callback=None) -> Dict[str, Any]:
        dependencies = {
            'external': [],
            'internal': defaultdict(list),
            'package_managers': {}
        }
        
        dependency_files = {
            'requirements.txt': 'pip',
            'package.json': 'npm',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'Gemfile': 'bundler',
            'go.mod': 'go',
            'Cargo.toml': 'cargo',
            'composer.json': 'composer'
        }
        
        for dep_file, manager in dependency_files.items():
            try:
                if dep_file in repo.tree():
                    if progress_callback:
                        progress_callback(f"Parsing {dep_file} dependencies...")
                    content = repo.odb.stream(repo.tree()[dep_file].binsha).read().decode('utf-8', errors='ignore')
                    dependencies['package_managers'][manager] = self._parse_dependency_file(dep_file, content)
            except:
                pass
        
        return dependencies
    
    def _parse_dependency_file(self, filename: str, content: str) -> List[str]:
        deps = []
        
        if filename == 'requirements.txt':
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    deps.append(line.split('==')[0].split('>=')[0].split('<=')[0])
        
        elif filename == 'package.json':
            try:
                import json
                data = json.loads(content)
                deps.extend(data.get('dependencies', {}).keys())
                deps.extend(data.get('devDependencies', {}).keys())
            except:
                pass
        
        return deps
    
    def _calculate_architecture_metrics(self, repo, repo_url: str) -> Dict[str, Any]:
        metrics = {
            'modularity_score': 0,
            'coupling_score': 0,
            'cohesion_score': 0,
            'complexity_score': 0,
            'maintainability_index': 0
        }
        
        try:
            total_files = 0
            total_dirs = set()
            language_distribution = defaultdict(int)
            
            for item in repo.tree().traverse():
                if item.type == 'blob':
                    total_files += 1
                    directory = os.path.dirname(item.path)
                    if directory:
                        total_dirs.add(directory)
                    language = self._detect_language(item.path)
                    language_distribution[language] += 1
            
            if total_files > 0:
                metrics['modularity_score'] = min(100, (len(total_dirs) / total_files) * 200)
            
            if total_files > 10:
                metrics['coupling_score'] = max(0, 100 - (total_files / 10))
            
            metrics['cohesion_score'] = 100 - (len(language_distribution) * 10)
            metrics['cohesion_score'] = max(0, metrics['cohesion_score'])
            
            metrics['maintainability_index'] = (
                metrics['modularity_score'] * 0.3 +
                metrics['coupling_score'] * 0.3 +
                metrics['cohesion_score'] * 0.4
            )
            
        except Exception as e:
            print(f"Error calculating metrics: {e}")
        
        return metrics
    
    def _analyze_evolution_patterns(self, commits_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        patterns = {
            'commit_frequency': defaultdict(int),
            'author_contributions': defaultdict(int),
            'file_change_frequency': defaultdict(int),
            'refactoring_periods': [],
            'feature_periods': [],
            'bugfix_periods': []
        }
        
        for commit in commits_data:
            date = commit['timestamp'][:10]
            patterns['commit_frequency'][date] += 1
            patterns['author_contributions'][commit['author_name']] += 1
            
            if commit['type'] == 'refactor':
                patterns['refactoring_periods'].append(date)
            elif commit['type'] == 'feature':
                patterns['feature_periods'].append(date)
            elif commit['type'] == 'bugfix':
                patterns['bugfix_periods'].append(date)
        
        patterns['commit_frequency'] = dict(patterns['commit_frequency'])
        patterns['author_contributions'] = dict(patterns['author_contributions'])
        patterns['file_change_frequency'] = dict(patterns['file_change_frequency'])
        
        return patterns