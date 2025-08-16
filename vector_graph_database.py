import os
from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional, Tuple
import json
import numpy as np
from datetime import datetime
from embedding_manager import EmbeddingManager, CodeEmbeddingAnalyzer

class VectorGraphDatabase:
    def __init__(self, uri=None, username=None, password=None, embedding_model='openai'):
        self.uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = username or os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = None
        self.embedding_model = embedding_model or os.getenv('EMBEDDING_MODEL', 'openai')
        self.embedding_manager = EmbeddingManager(self.embedding_model)
        self.code_analyzer = CodeEmbeddingAnalyzer(self.embedding_manager)
        self._connect()
    
    def _connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            self._create_vector_indexes()
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def _create_vector_indexes(self):
        with self.driver.session() as session:
            # Get embedding dimensions based on model
            embedding_dim = self.embedding_manager.embedding_dim
            
            # Drop existing indexes if dimensions changed
            try:
                session.run("DROP INDEX commit_embeddings IF EXISTS")
                session.run("DROP INDEX file_embeddings IF EXISTS")
                session.run("DROP INDEX change_embeddings IF EXISTS")
                session.run("DROP INDEX pr_embeddings IF EXISTS")
            except:
                pass  # Indexes might not exist
            
            indexes = [
                f"""
                CREATE VECTOR INDEX commit_embeddings IF NOT EXISTS
                FOR (c:Commit)
                ON c.embedding
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {embedding_dim},
                    `vector.similarity_function`: 'cosine'
                }}}}
                """,
                f"""
                CREATE VECTOR INDEX file_embeddings IF NOT EXISTS
                FOR (f:File)
                ON f.embedding
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {embedding_dim},
                    `vector.similarity_function`: 'cosine'
                }}}}
                """,
                f"""
                CREATE VECTOR INDEX change_embeddings IF NOT EXISTS
                FOR (ch:Change)
                ON ch.embedding
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {embedding_dim},
                    `vector.similarity_function`: 'cosine'
                }}}}
                """,
                f"""
                CREATE VECTOR INDEX pr_embeddings IF NOT EXISTS
                FOR (pr:PullRequest)
                ON pr.embedding
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {embedding_dim},
                    `vector.similarity_function`: 'cosine'
                }}}}
                """
            ]
            
            for index_query in indexes:
                try:
                    session.run(index_query)
                except Exception as e:
                    print(f"Index creation note: {e}")
    
    def store_commit_with_embedding(self, commit_data: Dict[str, Any], repo_url: str):
        commit_text = f"{commit_data['message']} {commit_data.get('type', '')}"
        embedding = self.embedding_manager.generate_embedding(commit_text, 'commit')
        
        with self.driver.session() as session:
            session.execute_write(
                self._create_commit_with_embedding,
                commit_data, repo_url, embedding
            )
    
    @staticmethod
    def _create_commit_with_embedding(tx, commit_data, repo_url, embedding):
        query = """
        MATCH (r:Repository {url: $repo_url})
        MERGE (a:Author {email: $author_email})
        SET a.name = $author_name
        MERGE (c:Commit {sha: $sha})
        SET c.message = $message,
            c.timestamp = datetime($timestamp),
            c.type = $type,
            c.insertions = $insertions,
            c.deletions = $deletions,
            c.embedding = $embedding,
            c.semantic_category = $semantic_category
        MERGE (r)-[:HAS_COMMIT]->(c)
        MERGE (a)-[:AUTHORED]->(c)
        """
        
        tx.run(query,
               repo_url=repo_url,
               sha=commit_data['sha'],
               message=commit_data['message'],
               author_name=commit_data['author_name'],
               author_email=commit_data['author_email'],
               timestamp=commit_data['timestamp'],
               type=commit_data.get('type', 'other'),
               insertions=commit_data.get('insertions', 0),
               deletions=commit_data.get('deletions', 0),
               embedding=embedding,
               semantic_category=commit_data.get('semantic_category', 'general'))
    
    def store_code_change_with_analysis(self, commit_sha: str, file_path: str, 
                                       before_code: str, after_code: str,
                                       change_analysis: Dict[str, Any]):
        change_embedding = self.code_analyzer.analyze_code_change(
            before_code, after_code, file_path
        )
        
        with self.driver.session() as session:
            session.execute_write(
                self._create_code_change_with_embedding,
                commit_sha, file_path, change_embedding, change_analysis
            )
    
    @staticmethod
    def _create_code_change_with_embedding(tx, commit_sha, file_path, change_embedding, analysis):
        query = """
        MATCH (c:Commit {sha: $commit_sha})
        MERGE (f:File {path: $file_path})
        MERGE (ch:Change {id: $change_id})
        SET ch.embedding = $embedding,
            ch.semantic_similarity = $semantic_similarity,
            ch.change_magnitude = $change_magnitude,
            ch.change_type = $change_type,
            ch.analysis = $analysis
        MERGE (c)-[:CONTAINS_CHANGE]->(ch)
        MERGE (ch)-[:MODIFIES]->(f)
        """
        
        change_id = f"{commit_sha}_{file_path}"
        
        tx.run(query,
               commit_sha=commit_sha,
               file_path=file_path,
               change_id=change_id,
               embedding=change_embedding['after_embedding'],
               semantic_similarity=change_embedding['semantic_similarity'],
               change_magnitude=change_embedding['change_magnitude'],
               change_type=change_embedding['change_type'],
               analysis=json.dumps(analysis))
    
    def store_pull_request(self, pr_data: Dict[str, Any], repo_url: str):
        pr_text = f"{pr_data['title']} {pr_data['description']}"
        embedding = self.embedding_manager.generate_embedding(pr_text, 'commit')
        
        with self.driver.session() as session:
            session.execute_write(
                self._create_pull_request,
                pr_data, repo_url, embedding
            )
    
    @staticmethod
    def _create_pull_request(tx, pr_data, repo_url, embedding):
        query = """
        MATCH (r:Repository {url: $repo_url})
        MERGE (pr:PullRequest {number: $pr_number})
        SET pr.title = $title,
            pr.description = $description,
            pr.state = $state,
            pr.created_at = datetime($created_at),
            pr.merged_at = datetime($merged_at),
            pr.embedding = $embedding,
            pr.author = $author
        MERGE (r)-[:HAS_PR]->(pr)
        """
        
        tx.run(query,
               repo_url=repo_url,
               pr_number=pr_data['number'],
               title=pr_data['title'],
               description=pr_data.get('description', ''),
               state=pr_data['state'],
               created_at=pr_data['created_at'],
               merged_at=pr_data.get('merged_at'),
               embedding=embedding,
               author=pr_data.get('author', 'unknown'))
        
        for commit_sha in pr_data.get('commits', []):
            link_query = """
            MATCH (pr:PullRequest {number: $pr_number})
            MATCH (c:Commit {sha: $commit_sha})
            MERGE (pr)-[:INCLUDES]->(c)
            """
            tx.run(link_query, pr_number=pr_data['number'], commit_sha=commit_sha)
    
    def semantic_search_commits(self, query: str, repo_url: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_manager.generate_embedding(query, 'commit')
        
        with self.driver.session() as session:
            return session.execute_read(
                self._vector_search_commits,
                query_embedding, repo_url, top_k
            )
    
    @staticmethod
    def _vector_search_commits(tx, query_embedding, repo_url, top_k):
        query = """
        MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
        WHERE c.embedding IS NOT NULL
        WITH c, gds.similarity.cosine(c.embedding, $query_embedding) AS similarity
        WHERE similarity > 0.3
        RETURN c.sha as sha, c.message as message, c.timestamp as timestamp,
               c.type as type, similarity
        ORDER BY similarity DESC
        LIMIT $top_k
        """
        
        result = tx.run(query,
                       repo_url=repo_url,
                       query_embedding=query_embedding,
                       top_k=top_k)
        
        return [dict(record) for record in result]
    
    def find_similar_changes(self, file_path: str, top_k: int = 5) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            file_query = """
            MATCH (f:File {path: $file_path})<-[:MODIFIES]-(ch:Change)
            WHERE ch.embedding IS NOT NULL
            RETURN ch.embedding as embedding
            LIMIT 1
            """
            result = session.run(file_query, file_path=file_path).single()
            
            if not result:
                return []
            
            reference_embedding = result['embedding']
            
            similar_query = """
            MATCH (ch:Change)-[:MODIFIES]->(f:File)
            WHERE ch.embedding IS NOT NULL AND f.path <> $file_path
            WITH ch, f, gds.similarity.cosine(ch.embedding, $reference_embedding) AS similarity
            WHERE similarity > 0.5
            RETURN f.path as file, ch.change_type as change_type,
                   ch.semantic_similarity as semantic_similarity, similarity
            ORDER BY similarity DESC
            LIMIT $top_k
            """
            
            results = session.run(similar_query,
                                 file_path=file_path,
                                 reference_embedding=reference_embedding,
                                 top_k=top_k)
            
            return [dict(record) for record in results]
    
    def analyze_semantic_evolution(self, file_path: str) -> Dict[str, Any]:
        with self.driver.session() as session:
            query = """
            MATCH (f:File {path: $file_path})<-[:MODIFIES]-(ch:Change)<-[:CONTAINS_CHANGE]-(c:Commit)
            WHERE ch.embedding IS NOT NULL
            RETURN c.timestamp as timestamp, ch.embedding as embedding,
                   ch.semantic_similarity as similarity, ch.change_type as change_type
            ORDER BY c.timestamp
            """
            
            results = session.run(query, file_path=file_path)
            
            evolution_data = []
            embeddings = []
            
            for record in results:
                evolution_data.append({
                    'timestamp': str(record['timestamp']),
                    'similarity': record['similarity'],
                    'change_type': record['change_type']
                })
                embeddings.append(record['embedding'])
            
            if len(embeddings) > 1:
                drift_scores = []
                for i in range(1, len(embeddings)):
                    drift = 1 - self.embedding_manager.calculate_similarity(
                        embeddings[0], embeddings[i]
                    )
                    drift_scores.append(drift)
                
                semantic_drift = np.mean(drift_scores) if drift_scores else 0
            else:
                semantic_drift = 0
            
            return {
                'file_path': file_path,
                'evolution_timeline': evolution_data,
                'total_changes': len(evolution_data),
                'semantic_drift': float(semantic_drift),
                'drift_interpretation': self._interpret_drift(semantic_drift)
            }
    
    def _interpret_drift(self, drift: float) -> str:
        if drift < 0.2:
            return 'Stable: minimal semantic changes over time'
        elif drift < 0.5:
            return 'Evolving: moderate semantic evolution'
        elif drift < 0.8:
            return 'Significant evolution: substantial semantic changes'
        else:
            return 'Major transformation: fundamental semantic shifts'
    
    def identify_semantic_clusters(self, repo_url: str) -> Dict[str, Any]:
        with self.driver.session() as session:
            query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
            WHERE c.embedding IS NOT NULL
            RETURN c.sha as sha, c.message as message, c.embedding as embedding
            LIMIT 500
            """
            
            results = session.run(query, repo_url=repo_url)
            
            commits = []
            embeddings = []
            
            for record in results:
                commits.append({
                    'sha': record['sha'],
                    'message': record['message']
                })
                embeddings.append(record['embedding'])
            
            if len(embeddings) > 5:
                patterns = self.code_analyzer.identify_semantic_patterns(embeddings)
                
                clusters = []
                for i, cluster_id in enumerate(patterns['cluster_assignments']):
                    if i < len(commits):
                        commits[i]['cluster'] = cluster_id
                
                for cluster_id in set(patterns['cluster_assignments']):
                    cluster_commits = [c for c in commits if c.get('cluster') == cluster_id]
                    clusters.append({
                        'cluster_id': cluster_id,
                        'size': len(cluster_commits),
                        'sample_commits': cluster_commits[:5]
                    })
                
                return {
                    'total_commits_analyzed': len(commits),
                    'num_clusters': patterns['n_patterns'],
                    'clusters': clusters,
                    'cluster_sizes': patterns['cluster_sizes']
                }
            
            return {
                'total_commits_analyzed': len(commits),
                'num_clusters': 0,
                'clusters': [],
                'message': 'Not enough data for clustering'
            }
    
    def get_contextual_recommendations(self, query: str, repo_url: str) -> Dict[str, Any]:
        similar_commits = self.semantic_search_commits(query, repo_url, top_k=5)
        
        recommendations = {
            'query': query,
            'similar_work': similar_commits,
            'suggested_files': [],
            'related_patterns': []
        }
        
        if similar_commits:
            with self.driver.session() as session:
                for commit in similar_commits[:3]:
                    files_query = """
                    MATCH (c:Commit {sha: $sha})-[:CONTAINS_CHANGE]->(:Change)-[:MODIFIES]->(f:File)
                    RETURN DISTINCT f.path as file_path
                    """
                    files_result = session.run(files_query, sha=commit['sha'])
                    
                    for record in files_result:
                        if record['file_path'] not in recommendations['suggested_files']:
                            recommendations['suggested_files'].append(record['file_path'])
                
                pattern_query = """
                MATCH (c:Commit)
                WHERE c.sha IN $commit_shas
                RETURN DISTINCT c.type as pattern, COUNT(*) as count
                ORDER BY count DESC
                """
                patterns_result = session.run(
                    pattern_query,
                    commit_shas=[c['sha'] for c in similar_commits]
                )
                
                for record in patterns_result:
                    recommendations['related_patterns'].append({
                        'pattern': record['pattern'],
                        'frequency': record['count']
                    })
        
        return recommendations
    
    def close(self):
        if self.driver:
            self.driver.close()