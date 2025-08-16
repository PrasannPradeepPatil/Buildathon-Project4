import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from vector_graph_database import VectorGraphDatabase
from llm_code_analyzer import LLMCodeAnalyzer
from embedding_manager import EmbeddingManager
from architecture_analyzer import ArchitectureAnalyzer

class SemanticQueryEngine:
    def __init__(self, vector_db: VectorGraphDatabase, llm_analyzer: LLMCodeAnalyzer):
        self.vector_db = vector_db
        self.llm_analyzer = llm_analyzer
        self.embedding_manager = vector_db.embedding_manager
        self.query_cache = {}
    
    def answer_question(self, question: str, repo_url: str, 
                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        question_lower = question.lower()
        
        if self._is_semantic_query(question_lower):
            return self._handle_semantic_query(question, repo_url, context)
        elif self._is_evolution_query(question_lower):
            return self._handle_evolution_query(question, repo_url, context)
        elif self._is_impact_query(question_lower):
            return self._handle_impact_query(question, repo_url, context)
        elif self._is_pattern_query(question_lower):
            return self._handle_pattern_query(question, repo_url, context)
        elif self._is_collaboration_query(question_lower):
            return self._handle_collaboration_query(question, repo_url, context)
        else:
            return self._handle_general_query(question, repo_url, context)
    
    def _is_semantic_query(self, question: str) -> bool:
        semantic_keywords = ['similar', 'like', 'related', 'same as', 'comparable']
        return any(keyword in question for keyword in semantic_keywords)
    
    def _is_evolution_query(self, question: str) -> bool:
        evolution_keywords = ['evolve', 'change over time', 'history', 'progression', 
                            'timeline', 'drift', 'transform']
        return any(keyword in question for keyword in evolution_keywords)
    
    def _is_impact_query(self, question: str) -> bool:
        impact_keywords = ['impact', 'affect', 'consequence', 'result', 'cause']
        return any(keyword in question for keyword in impact_keywords)
    
    def _is_pattern_query(self, question: str) -> bool:
        pattern_keywords = ['pattern', 'trend', 'common', 'frequent', 'typical']
        return any(keyword in question for keyword in pattern_keywords)
    
    def _is_collaboration_query(self, question: str) -> bool:
        collab_keywords = ['who', 'author', 'contributor', 'team', 'collaborate']
        return any(keyword in question for keyword in collab_keywords)
    
    def _handle_semantic_query(self, question: str, repo_url: str, 
                              context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        similar_commits = self.vector_db.semantic_search_commits(question, repo_url, top_k=10)
        
        response = {
            'question': question,
            'answer_type': 'semantic_search',
            'results': similar_commits,
            'insights': []
        }
        
        if similar_commits:
            commit_types = {}
            for commit in similar_commits:
                commit_type = commit.get('type', 'other')
                commit_types[commit_type] = commit_types.get(commit_type, 0) + 1
            
            dominant_type = max(commit_types, key=commit_types.get)
            response['insights'].append({
                'type': 'pattern',
                'description': f"Most similar commits are of type '{dominant_type}' ({commit_types[dominant_type]} out of {len(similar_commits)})"
            })
            
            if context and 'file_path' in context:
                file_changes = self.vector_db.find_similar_changes(context['file_path'])
                response['related_files'] = file_changes
                
                if file_changes:
                    response['insights'].append({
                        'type': 'related_work',
                        'description': f"Found {len(file_changes)} files with similar change patterns"
                    })
        
        response['summary'] = self._generate_semantic_summary(similar_commits)
        
        return response
    
    def _handle_evolution_query(self, question: str, repo_url: str,
                               context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        response = {
            'question': question,
            'answer_type': 'evolution_analysis',
            'timeline': [],
            'insights': []
        }
        
        if context and 'file_path' in context:
            evolution = self.vector_db.analyze_semantic_evolution(context['file_path'])
            response['evolution'] = evolution
            response['insights'].append({
                'type': 'semantic_drift',
                'description': evolution['drift_interpretation']
            })
        
        clusters = self.vector_db.identify_semantic_clusters(repo_url)
        response['semantic_clusters'] = clusters
        
        if clusters['num_clusters'] > 0:
            response['insights'].append({
                'type': 'development_phases',
                'description': f"Identified {clusters['num_clusters']} distinct development patterns"
            })
        
        with self.vector_db.driver.session() as session:
            timeline_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WITH date(c.timestamp) as commit_date, 
                 COUNT(*) as daily_commits,
                 COLLECT(DISTINCT c.type) as commit_types
            ORDER BY commit_date
            RETURN commit_date, daily_commits, commit_types
            LIMIT 365
            """
            
            timeline_results = session.run(timeline_query, repo_url=repo_url)
            
            for record in timeline_results:
                response['timeline'].append({
                    'date': str(record['commit_date']),
                    'commits': record['daily_commits'],
                    'types': record['commit_types']
                })
        
        response['summary'] = self._generate_evolution_summary(response)
        
        return response
    
    def _handle_impact_query(self, question: str, repo_url: str,
                           context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        response = {
            'question': question,
            'answer_type': 'impact_analysis',
            'impacts': [],
            'recommendations': []
        }
        
        with self.vector_db.driver.session() as session:
            if 'commit_sha' in (context or {}):
                impact_query = """
                MATCH (c:Commit {sha: $commit_sha})-[:CONTAINS_CHANGE]->(ch:Change)-[:MODIFIES]->(f:File)
                OPTIONAL MATCH (f)<-[:DEPENDS_ON]-(dependent:File)
                RETURN f.path as file_changed, 
                       ch.change_type as change_type,
                       COLLECT(DISTINCT dependent.path) as affected_files
                """
                
                results = session.run(impact_query, commit_sha=context['commit_sha'])
                
                for record in results:
                    response['impacts'].append({
                        'file': record['file_changed'],
                        'change_type': record['change_type'],
                        'potentially_affected': record['affected_files']
                    })
            
            ripple_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WHERE c.type = 'breaking'
            WITH c
            MATCH (c)-[:CONTAINS_CHANGE]->(:Change)-[:MODIFIES]->(f:File)
            RETURN c.sha as commit, c.message as message, COLLECT(f.path) as files
            LIMIT 10
            """
            
            breaking_changes = session.run(ripple_query, repo_url=repo_url)
            
            for record in breaking_changes:
                response['impacts'].append({
                    'type': 'breaking_change',
                    'commit': record['commit'],
                    'message': record['message'],
                    'files_affected': record['files']
                })
        
        recent_changes = self._get_recent_changes(repo_url, days=30)
        if recent_changes:
            architecture_impact = self.llm_analyzer.analyze_architecture_impact(recent_changes)
            response['architecture_impact'] = architecture_impact
            
            if 'recommendations' in architecture_impact:
                response['recommendations'].extend(architecture_impact['recommendations'])
        
        response['summary'] = self._generate_impact_summary(response)
        
        return response
    
    def _handle_pattern_query(self, question: str, repo_url: str,
                            context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        response = {
            'question': question,
            'answer_type': 'pattern_analysis',
            'patterns': [],
            'insights': []
        }
        
        clusters = self.vector_db.identify_semantic_clusters(repo_url)
        
        if clusters['clusters']:
            for cluster in clusters['clusters']:
                pattern_name = self._identify_cluster_pattern(cluster['sample_commits'])
                response['patterns'].append({
                    'pattern': pattern_name,
                    'frequency': cluster['size'],
                    'examples': cluster['sample_commits'][:3]
                })
        
        with self.vector_db.driver.session() as session:
            pattern_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WITH c.type as commit_type, COUNT(*) as count
            WHERE count > 5
            RETURN commit_type, count
            ORDER BY count DESC
            """
            
            type_patterns = session.run(pattern_query, repo_url=repo_url)
            
            for record in type_patterns:
                response['patterns'].append({
                    'pattern': f"{record['commit_type']}_commits",
                    'frequency': record['count']
                })
            
            temporal_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WITH date(c.timestamp) as commit_date, 
                 CASE 
                   WHEN date(c.timestamp).dayOfWeek IN [1,2,3,4,5] THEN 'weekday'
                   ELSE 'weekend'
                 END as day_type,
                 COUNT(*) as commits
            RETURN day_type, SUM(commits) as total_commits
            """
            
            temporal_results = session.run(temporal_query, repo_url=repo_url)
            
            temporal_pattern = {}
            for record in temporal_results:
                temporal_pattern[record['day_type']] = record['total_commits']
            
            if temporal_pattern:
                response['insights'].append({
                    'type': 'temporal_pattern',
                    'description': f"Weekday commits: {temporal_pattern.get('weekday', 0)}, Weekend commits: {temporal_pattern.get('weekend', 0)}"
                })
        
        response['summary'] = self._generate_pattern_summary(response)
        
        return response
    
    def _handle_collaboration_query(self, question: str, repo_url: str,
                                  context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        response = {
            'question': question,
            'answer_type': 'collaboration_analysis',
            'contributors': [],
            'collaboration_patterns': [],
            'insights': []
        }
        
        with self.vector_db.driver.session() as session:
            contributor_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)<-[:AUTHORED]-(a:Author)
            WITH a, COUNT(c) as commit_count, 
                 COLLECT(DISTINCT c.type) as commit_types,
                 AVG(c.insertions + c.deletions) as avg_change_size
            RETURN a.name as author, a.email as email, 
                   commit_count, commit_types, avg_change_size
            ORDER BY commit_count DESC
            LIMIT 20
            """
            
            contributors = session.run(contributor_query, repo_url=repo_url)
            
            for record in contributors:
                response['contributors'].append({
                    'author': record['author'],
                    'email': record['email'],
                    'commits': record['commit_count'],
                    'specializations': record['commit_types'],
                    'avg_change_size': record['avg_change_size']
                })
            
            collaboration_query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            MATCH (c)-[:CONTAINS_CHANGE]->(:Change)-[:MODIFIES]->(f:File)
            MATCH (a:Author)-[:AUTHORED]->(c)
            WITH f.path as file, COLLECT(DISTINCT a.name) as authors
            WHERE SIZE(authors) > 1
            RETURN file, authors, SIZE(authors) as author_count
            ORDER BY author_count DESC
            LIMIT 15
            """
            
            collaboration_results = session.run(collaboration_query, repo_url=repo_url)
            
            for record in collaboration_results:
                response['collaboration_patterns'].append({
                    'file': record['file'],
                    'collaborators': record['authors'],
                    'collaboration_level': record['author_count']
                })
        
        if response['contributors']:
            top_contributor = response['contributors'][0]
            response['insights'].append({
                'type': 'top_contributor',
                'description': f"{top_contributor['author']} is the top contributor with {top_contributor['commits']} commits"
            })
        
        if response['collaboration_patterns']:
            avg_collaboration = sum(p['collaboration_level'] for p in response['collaboration_patterns']) / len(response['collaboration_patterns'])
            response['insights'].append({
                'type': 'collaboration_level',
                'description': f"Average {avg_collaboration:.1f} contributors per heavily modified file"
            })
        
        response['summary'] = self._generate_collaboration_summary(response)
        
        return response
    
    def _handle_general_query(self, question: str, repo_url: str,
                            context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        semantic_results = self.vector_db.semantic_search_commits(question, repo_url, top_k=5)
        
        recommendations = self.vector_db.get_contextual_recommendations(question, repo_url)
        
        response = {
            'question': question,
            'answer_type': 'general',
            'semantic_matches': semantic_results,
            'recommendations': recommendations,
            'insights': []
        }
        
        if semantic_results:
            commits_data = []
            for result in semantic_results:
                commits_data.append({
                    'message': result['message'],
                    'type': result.get('type', 'other'),
                    'timestamp': result.get('timestamp', '')
                })
            
            narrative = self.llm_analyzer.generate_change_narrative(commits_data)
            response['narrative'] = narrative
        
        response['summary'] = f"Found {len(semantic_results)} relevant commits. " + \
                              f"Suggested files to review: {', '.join(recommendations['suggested_files'][:3])}"
        
        return response
    
    def _get_recent_changes(self, repo_url: str, days: int = 30) -> List[Dict[str, Any]]:
        with self.vector_db.driver.session() as session:
            query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WHERE c.timestamp > datetime() - duration({days: $days})
            MATCH (c)-[:CONTAINS_CHANGE]->(ch:Change)-[:MODIFIES]->(f:File)
            RETURN c.sha as commit_sha, c.message as commit_message,
                   f.path as file_path, ch.change_type as change_type
            LIMIT 100
            """
            
            results = session.run(query, repo_url=repo_url, days=days)
            
            changes = []
            for record in results:
                changes.append({
                    'commit_sha': record['commit_sha'],
                    'commit_message': record['commit_message'],
                    'file_path': record['file_path'],
                    'change_type': record['change_type']
                })
            
            return changes
    
    def _identify_cluster_pattern(self, sample_commits: List[Dict[str, Any]]) -> str:
        if not sample_commits:
            return 'unknown'
        
        messages = ' '.join([c.get('message', '') for c in sample_commits]).lower()
        
        if 'feat' in messages or 'add' in messages:
            return 'feature_development'
        elif 'fix' in messages or 'bug' in messages:
            return 'bug_fixing'
        elif 'refactor' in messages:
            return 'refactoring'
        elif 'test' in messages:
            return 'testing'
        elif 'doc' in messages:
            return 'documentation'
        else:
            return 'mixed_development'
    
    def _generate_semantic_summary(self, commits: List[Dict[str, Any]]) -> str:
        if not commits:
            return "No semantically similar commits found."
        
        avg_similarity = sum(c.get('similarity', 0) for c in commits) / len(commits)
        
        return f"Found {len(commits)} semantically similar commits with average similarity of {avg_similarity:.2f}. " + \
               f"Top match: '{commits[0]['message'][:100]}...'"
    
    def _generate_evolution_summary(self, data: Dict[str, Any]) -> str:
        timeline_length = len(data.get('timeline', []))
        clusters = data.get('semantic_clusters', {}).get('num_clusters', 0)
        
        summary = f"Repository shows {timeline_length} days of activity with {clusters} distinct development patterns. "
        
        if 'evolution' in data:
            summary += data['evolution']['drift_interpretation']
        
        return summary
    
    def _generate_impact_summary(self, data: Dict[str, Any]) -> str:
        impacts = data.get('impacts', [])
        breaking_changes = [i for i in impacts if i.get('type') == 'breaking_change']
        
        summary = f"Identified {len(impacts)} potential impacts. "
        
        if breaking_changes:
            summary += f"Warning: {len(breaking_changes)} breaking changes detected. "
        
        if data.get('recommendations'):
            summary += f"Generated {len(data['recommendations'])} recommendations for maintaining stability."
        
        return summary
    
    def _generate_pattern_summary(self, data: Dict[str, Any]) -> str:
        patterns = data.get('patterns', [])
        
        if not patterns:
            return "No significant patterns detected."
        
        top_pattern = max(patterns, key=lambda x: x.get('frequency', 0))
        
        return f"Identified {len(patterns)} patterns. Most frequent: {top_pattern['pattern']} " + \
               f"({top_pattern['frequency']} occurrences)."
    
    def _generate_collaboration_summary(self, data: Dict[str, Any]) -> str:
        contributors = data.get('contributors', [])
        collaboration_patterns = data.get('collaboration_patterns', [])
        
        summary = f"Found {len(contributors)} contributors. "
        
        if collaboration_patterns:
            high_collab = [p for p in collaboration_patterns if p['collaboration_level'] > 3]
            summary += f"{len(high_collab)} files show high collaboration (3+ contributors)."
        
        return summary