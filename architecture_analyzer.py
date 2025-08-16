import networkx as nx
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import re
from datetime import datetime, timedelta

class ArchitectureAnalyzer:
    def __init__(self, graph_db):
        self.graph_db = graph_db
        self.architecture_patterns = {
            'mvc': ['model', 'view', 'controller', 'template'],
            'layered': ['presentation', 'business', 'data', 'service', 'repository'],
            'microservices': ['service', 'api', 'gateway', 'docker', 'kubernetes'],
            'event_driven': ['event', 'handler', 'listener', 'publisher', 'subscriber'],
            'domain_driven': ['domain', 'entity', 'aggregate', 'repository', 'value'],
            'hexagonal': ['adapter', 'port', 'domain', 'infrastructure', 'application'],
            'clean': ['entity', 'usecase', 'controller', 'gateway', 'presenter']
        }
    
    def analyze_architecture(self, repo_url: str) -> Dict[str, Any]:
        analysis = {
            'patterns_detected': self._detect_patterns(repo_url),
            'complexity_analysis': self._analyze_complexity(repo_url),
            'dependency_graph': self._build_dependency_graph(repo_url),
            'hotspots': self._identify_hotspots(repo_url),
            'technical_debt': self._assess_technical_debt(repo_url),
            'evolution_timeline': self._analyze_evolution_timeline(repo_url),
            'recommendations': []
        }
        
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _detect_patterns(self, repo_url: str) -> Dict[str, float]:
        detected_patterns = {}
        
        with self.graph_db.driver.session() as session:
            for pattern_name, keywords in self.architecture_patterns.items():
                query = """
                MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(:Commit)-[:MODIFIES]->(f:File)
                WHERE ANY(keyword IN $keywords WHERE toLower(f.path) CONTAINS keyword)
                RETURN COUNT(DISTINCT f) as file_count
                """
                result = session.run(query, repo_url=repo_url, keywords=keywords)
                count = result.single()['file_count']
                
                total_files_query = """
                MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(:Commit)-[:MODIFIES]->(f:File)
                RETURN COUNT(DISTINCT f) as total
                """
                total_result = session.run(total_files_query, repo_url=repo_url)
                total = total_result.single()['total']
                
                if total > 0:
                    confidence = min(100, (count / total) * 100 * len(keywords))
                    if confidence > 10:
                        detected_patterns[pattern_name] = confidence
        
        return detected_patterns
    
    def _analyze_complexity(self, repo_url: str) -> Dict[str, Any]:
        complexity_data = {
            'average_file_complexity': 0,
            'high_complexity_files': [],
            'complexity_distribution': {},
            'refactoring_candidates': []
        }
        
        with self.graph_db.driver.session() as session:
            query = """
            MATCH (f:File)-[:DEFINES]->(fn:Function)
            WHERE fn.complexity IS NOT NULL
            WITH f.path as file, AVG(fn.complexity) as avg_complexity, 
                 MAX(fn.complexity) as max_complexity,
                 COLLECT({name: fn.name, complexity: fn.complexity}) as functions
            RETURN file, avg_complexity, max_complexity, functions
            ORDER BY avg_complexity DESC
            """
            
            results = session.run(query)
            complexities = []
            
            for record in results:
                complexities.append(record['avg_complexity'])
                
                if record['max_complexity'] > 10:
                    complexity_data['high_complexity_files'].append({
                        'file': record['file'],
                        'average_complexity': record['avg_complexity'],
                        'max_complexity': record['max_complexity'],
                        'complex_functions': [f for f in record['functions'] if f['complexity'] > 10]
                    })
                
                if record['avg_complexity'] > 7:
                    complexity_data['refactoring_candidates'].append(record['file'])
            
            if complexities:
                complexity_data['average_file_complexity'] = sum(complexities) / len(complexities)
                
                complexity_data['complexity_distribution'] = {
                    'low': len([c for c in complexities if c <= 5]),
                    'medium': len([c for c in complexities if 5 < c <= 10]),
                    'high': len([c for c in complexities if c > 10])
                }
        
        return complexity_data
    
    def _build_dependency_graph(self, repo_url: str) -> Dict[str, Any]:
        dependency_graph = nx.DiGraph()
        
        with self.graph_db.driver.session() as session:
            query = """
            MATCH (f1:File)-[d:DEPENDS_ON]->(f2:File)
            RETURN f1.path as source, f2.path as target, d.type as dep_type
            """
            
            results = session.run(query)
            
            for record in results:
                dependency_graph.add_edge(
                    record['source'], 
                    record['target'],
                    type=record['dep_type']
                )
        
        analysis = {
            'total_dependencies': dependency_graph.number_of_edges(),
            'total_modules': dependency_graph.number_of_nodes(),
            'circular_dependencies': list(nx.simple_cycles(dependency_graph))[:10],
            'most_depended_upon': [],
            'most_dependent': [],
            'isolated_modules': list(nx.isolates(dependency_graph))
        }
        
        if dependency_graph.nodes():
            in_degrees = dict(dependency_graph.in_degree())
            out_degrees = dict(dependency_graph.out_degree())
            
            analysis['most_depended_upon'] = sorted(
                in_degrees.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            analysis['most_dependent'] = sorted(
                out_degrees.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        
        return analysis
    
    def _identify_hotspots(self, repo_url: str) -> Dict[str, Any]:
        hotspots = {
            'change_hotspots': [],
            'bug_hotspots': [],
            'author_hotspots': [],
            'coupling_hotspots': []
        }
        
        with self.graph_db.driver.session() as session:
            change_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)-[:MODIFIES]->(f:File)
            WITH f.path as file, COUNT(c) as changes, 
                 SUM(CASE WHEN c.type = 'bugfix' THEN 1 ELSE 0 END) as bug_fixes
            WHERE changes > 5
            RETURN file, changes, bug_fixes
            ORDER BY changes DESC
            LIMIT 20
            """
            
            results = session.run(change_query, repo_url=repo_url)
            for record in results:
                hotspots['change_hotspots'].append({
                    'file': record['file'],
                    'changes': record['changes'],
                    'bug_fixes': record['bug_fixes']
                })
                
                if record['bug_fixes'] > 3:
                    hotspots['bug_hotspots'].append({
                        'file': record['file'],
                        'bug_fixes': record['bug_fixes'],
                        'total_changes': record['changes']
                    })
            
            coupling_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            MATCH (c)-[:MODIFIES]->(f1:File)
            MATCH (c)-[:MODIFIES]->(f2:File)
            WHERE f1.path < f2.path
            WITH f1.path as file1, f2.path as file2, COUNT(*) as co_changes
            WHERE co_changes > 5
            RETURN file1, file2, co_changes
            ORDER BY co_changes DESC
            LIMIT 10
            """
            
            coupling_results = session.run(coupling_query, repo_url=repo_url)
            for record in coupling_results:
                hotspots['coupling_hotspots'].append({
                    'file1': record['file1'],
                    'file2': record['file2'],
                    'co_changes': record['co_changes']
                })
            
            author_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)-[:MODIFIES]->(f:File)
            MATCH (a:Author)-[:AUTHORED]->(c)
            WITH f.path as file, a.name as author, COUNT(*) as contributions
            WHERE contributions > 5
            WITH file, COLLECT({author: author, contributions: contributions}) as authors
            WHERE SIZE(authors) = 1
            RETURN file, authors[0].author as sole_author, authors[0].contributions as contributions
            ORDER BY contributions DESC
            LIMIT 10
            """
            
            author_results = session.run(author_query, repo_url=repo_url)
            for record in author_results:
                hotspots['author_hotspots'].append({
                    'file': record['file'],
                    'sole_author': record['sole_author'],
                    'contributions': record['contributions']
                })
        
        return hotspots
    
    def _assess_technical_debt(self, repo_url: str) -> Dict[str, Any]:
        debt_indicators = {
            'debt_score': 0,
            'indicators': [],
            'high_risk_files': [],
            'improvement_areas': []
        }
        
        complexity_analysis = self._analyze_complexity(repo_url)
        dependency_graph = self._build_dependency_graph(repo_url)
        hotspots = self._identify_hotspots(repo_url)
        
        if complexity_analysis['average_file_complexity'] > 7:
            debt_indicators['indicators'].append({
                'type': 'high_complexity',
                'severity': 'high',
                'description': f"Average complexity {complexity_analysis['average_file_complexity']:.2f} exceeds threshold"
            })
            debt_indicators['debt_score'] += 30
        
        if dependency_graph['circular_dependencies']:
            debt_indicators['indicators'].append({
                'type': 'circular_dependencies',
                'severity': 'critical',
                'description': f"Found {len(dependency_graph['circular_dependencies'])} circular dependencies"
            })
            debt_indicators['debt_score'] += 40
        
        if hotspots['bug_hotspots']:
            debt_indicators['indicators'].append({
                'type': 'bug_prone_files',
                'severity': 'high',
                'description': f"Found {len(hotspots['bug_hotspots'])} files with frequent bug fixes"
            })
            debt_indicators['debt_score'] += 25
        
        if hotspots['author_hotspots']:
            debt_indicators['indicators'].append({
                'type': 'knowledge_silos',
                'severity': 'medium',
                'description': f"Found {len(hotspots['author_hotspots'])} files maintained by single authors"
            })
            debt_indicators['debt_score'] += 15
        
        debt_indicators['high_risk_files'] = list(set(
            [f['file'] for f in complexity_analysis['high_complexity_files']] +
            [f['file'] for f in hotspots['bug_hotspots']]
        ))[:10]
        
        if debt_indicators['debt_score'] > 60:
            debt_indicators['improvement_areas'].append('Refactor high complexity functions')
        if dependency_graph['circular_dependencies']:
            debt_indicators['improvement_areas'].append('Resolve circular dependencies')
        if hotspots['bug_hotspots']:
            debt_indicators['improvement_areas'].append('Stabilize bug-prone modules')
        
        return debt_indicators
    
    def _analyze_evolution_timeline(self, repo_url: str) -> Dict[str, Any]:
        timeline = {
            'growth_rate': {},
            'activity_periods': {},
            'major_refactorings': [],
            'architecture_changes': []
        }
        
        with self.graph_db.driver.session() as session:
            growth_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WITH date(c.timestamp) as commit_date, COUNT(*) as daily_commits
            ORDER BY commit_date
            RETURN commit_date, daily_commits
            """
            
            results = session.run(growth_query, repo_url=repo_url)
            dates = []
            for record in results:
                date_str = str(record['commit_date'])
                timeline['growth_rate'][date_str] = record['daily_commits']
                dates.append(date_str)
            
            refactor_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WHERE c.type = 'refactor'
            WITH date(c.timestamp) as refactor_date, COUNT(*) as refactor_count
            WHERE refactor_count > 3
            RETURN refactor_date, refactor_count
            ORDER BY refactor_date
            """
            
            refactor_results = session.run(refactor_query, repo_url=repo_url)
            for record in refactor_results:
                timeline['major_refactorings'].append({
                    'date': str(record['refactor_date']),
                    'count': record['refactor_count']
                })
            
            if dates:
                timeline['activity_periods'] = {
                    'start_date': dates[0],
                    'end_date': dates[-1],
                    'total_days': len(dates),
                    'average_daily_commits': len(dates) / max(1, len(set(dates)))
                }
        
        return timeline
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        recommendations = []
        
        if analysis['technical_debt']['debt_score'] > 70:
            recommendations.append({
                'priority': 'high',
                'category': 'technical_debt',
                'recommendation': 'Critical technical debt detected. Prioritize refactoring efforts.',
                'actions': analysis['technical_debt']['improvement_areas']
            })
        
        if analysis['dependency_graph']['circular_dependencies']:
            recommendations.append({
                'priority': 'high',
                'category': 'architecture',
                'recommendation': 'Circular dependencies detected. Consider dependency inversion.',
                'actions': ['Review and refactor circular dependencies', 'Apply SOLID principles']
            })
        
        if analysis['complexity_analysis']['high_complexity_files']:
            recommendations.append({
                'priority': 'medium',
                'category': 'maintainability',
                'recommendation': 'High complexity files need simplification.',
                'actions': ['Break down complex functions', 'Extract methods', 'Apply single responsibility principle']
            })
        
        if analysis['hotspots']['coupling_hotspots']:
            recommendations.append({
                'priority': 'medium',
                'category': 'coupling',
                'recommendation': 'High coupling detected between files.',
                'actions': ['Consider extracting shared functionality', 'Reduce interdependencies']
            })
        
        if analysis['hotspots']['author_hotspots']:
            recommendations.append({
                'priority': 'low',
                'category': 'knowledge_sharing',
                'recommendation': 'Knowledge silos detected.',
                'actions': ['Implement pair programming', 'Conduct code reviews', 'Document critical modules']
            })
        
        return recommendations
    
    def answer_architecture_question(self, question: str, repo_url: str) -> Dict[str, Any]:
        question_lower = question.lower()
        response = {
            'question': question,
            'answer': '',
            'supporting_data': {},
            'visualizations': []
        }
        
        if 'pattern' in question_lower or 'architecture' in question_lower:
            patterns = self._detect_patterns(repo_url)
            response['answer'] = f"Detected patterns: {', '.join([f'{p} ({v:.1f}% confidence)' for p, v in patterns.items()])}"
            response['supporting_data'] = patterns
            
        elif 'complex' in question_lower:
            complexity = self._analyze_complexity(repo_url)
            response['answer'] = f"Average complexity: {complexity['average_file_complexity']:.2f}. Found {len(complexity['high_complexity_files'])} high complexity files."
            response['supporting_data'] = complexity
            
        elif 'depend' in question_lower:
            deps = self._build_dependency_graph(repo_url)
            response['answer'] = f"Found {deps['total_dependencies']} dependencies across {deps['total_modules']} modules. {len(deps['circular_dependencies'])} circular dependencies detected."
            response['supporting_data'] = deps
            
        elif 'hotspot' in question_lower or 'problem' in question_lower:
            hotspots = self._identify_hotspots(repo_url)
            response['answer'] = f"Identified {len(hotspots['change_hotspots'])} change hotspots and {len(hotspots['bug_hotspots'])} bug-prone files."
            response['supporting_data'] = hotspots
            
        elif 'debt' in question_lower or 'quality' in question_lower:
            debt = self._assess_technical_debt(repo_url)
            response['answer'] = f"Technical debt score: {debt['debt_score']}/100. Main issues: {', '.join([i['type'] for i in debt['indicators']])}"
            response['supporting_data'] = debt
            
        elif 'evolv' in question_lower or 'history' in question_lower:
            timeline = self._analyze_evolution_timeline(repo_url)
            response['answer'] = f"Repository active from {timeline['activity_periods'].get('start_date', 'unknown')} to {timeline['activity_periods'].get('end_date', 'unknown')}."
            response['supporting_data'] = timeline
            
        else:
            full_analysis = self.analyze_architecture(repo_url)
            response['answer'] = "Here's a comprehensive architecture analysis of your repository."
            response['supporting_data'] = full_analysis
        
        return response