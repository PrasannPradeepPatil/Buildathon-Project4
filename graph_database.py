import os
import logging
from neo4j import GraphDatabase
from datetime import datetime
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

class GraphDatabaseManager:
    def __init__(self, uri=None, username=None, password=None):
        self.uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = username or os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = None
        self._connect()
    
    def _connect(self):
        logger.info(f"Attempting to connect to Neo4j at {self.uri}")
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j database")
            self._create_constraints()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def _create_constraints(self):
        logger.info("Creating Neo4j constraints and indexes")
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.url IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Commit) REQUIRE c.sha IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE a.email IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
                "CREATE INDEX IF NOT EXISTS FOR (c:Commit) ON (c.timestamp)",
                "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.extension)",
                "CREATE INDEX IF NOT EXISTS FOR (m:Module) ON (m.name)",
                "CREATE INDEX IF NOT EXISTS FOR (cl:Class) ON (cl.name)",
                "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.name)"
            ]
            
            success_count = 0
            for constraint in constraints:
                try:
                    session.run(constraint)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Constraint creation warning: {e}")
            
            logger.info(f"Successfully created {success_count}/{len(constraints)} constraints/indexes")
    
    def store_repository(self, repo_data: Dict[str, Any]) -> str:
        logger.info(f"Storing repository: {repo_data.get('url', 'Unknown URL')}")
        with self.driver.session() as session:
            result = session.execute_write(self._create_repository, repo_data)
            logger.info(f"Successfully stored repository with ID: {result}")
            return result
    
    @staticmethod
    def _create_repository(tx, repo_data):
        query = """
        MERGE (r:Repository {url: $url})
        SET r.name = $name,
            r.analyzed_at = $analyzed_at,
            r.default_branch = $default_branch
        RETURN r.url as repo_id
        """
        result = tx.run(query, 
                       url=repo_data['url'],
                       name=repo_data['name'],
                       analyzed_at=datetime.now().isoformat(),
                       default_branch=repo_data.get('default_branch', 'main'))
        return result.single()['repo_id']
    
    def store_commit(self, commit_data: Dict[str, Any], repo_url: str):
        logger.debug(f"Storing commit {commit_data.get('sha', 'Unknown SHA')} for repo {repo_url}")
        with self.driver.session() as session:
            session.execute_write(self._create_commit, commit_data, repo_url)
            logger.debug(f"Successfully stored commit {commit_data.get('sha', 'Unknown SHA')}")
    
    @staticmethod
    def _create_commit(tx, commit_data, repo_url):
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
            c.files_changed = $files_changed
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
               files_changed=commit_data.get('files_changed', 0))
    
    def store_file_change(self, commit_sha: str, file_data: Dict[str, Any]):
        with self.driver.session() as session:
            session.execute_write(self._create_file_change, commit_sha, file_data)
    
    @staticmethod
    def _create_file_change(tx, commit_sha, file_data):
        query = """
        MATCH (c:Commit {sha: $commit_sha})
        MERGE (f:File {path: $file_path})
        SET f.extension = $extension,
            f.current_size = $size,
            f.language = $language
        MERGE (c)-[m:MODIFIES]->(f)
        SET m.insertions = $insertions,
            m.deletions = $deletions,
            m.change_type = $change_type
        """
        
        tx.run(query,
               commit_sha=commit_sha,
               file_path=file_data['path'],
               extension=file_data.get('extension', ''),
               size=file_data.get('size', 0),
               language=file_data.get('language', 'unknown'),
               insertions=file_data.get('insertions', 0),
               deletions=file_data.get('deletions', 0),
               change_type=file_data.get('change_type', 'modify'))
    
    def store_code_structure(self, file_path: str, structure_data: Dict[str, Any]):
        with self.driver.session() as session:
            session.execute_write(self._create_code_structure, file_path, structure_data)
    
    @staticmethod
    def _create_code_structure(tx, file_path, structure_data):
        query = """
        MATCH (f:File {path: $file_path})
        MERGE (m:Module {name: $module_name})
        MERGE (f)-[:CONTAINS]->(m)
        """
        tx.run(query, file_path=file_path, module_name=structure_data.get('module', file_path))
        
        for class_data in structure_data.get('classes', []):
            class_query = """
            MATCH (f:File {path: $file_path})
            MERGE (cl:Class {name: $class_name, file: $file_path})
            SET cl.methods = $methods,
                cl.attributes = $attributes,
                cl.line_start = $line_start,
                cl.line_end = $line_end
            MERGE (f)-[:DEFINES]->(cl)
            """
            tx.run(class_query,
                   file_path=file_path,
                   class_name=class_data['name'],
                   methods=class_data.get('methods', []),
                   attributes=class_data.get('attributes', []),
                   line_start=class_data.get('line_start', 0),
                   line_end=class_data.get('line_end', 0))
        
        for func_data in structure_data.get('functions', []):
            func_query = """
            MATCH (f:File {path: $file_path})
            MERGE (fn:Function {name: $func_name, file: $file_path})
            SET fn.parameters = $parameters,
                fn.line_start = $line_start,
                fn.line_end = $line_end,
                fn.complexity = $complexity
            MERGE (f)-[:DEFINES]->(fn)
            """
            tx.run(func_query,
                   file_path=file_path,
                   func_name=func_data['name'],
                   parameters=func_data.get('parameters', []),
                   line_start=func_data.get('line_start', 0),
                   line_end=func_data.get('line_end', 0),
                   complexity=func_data.get('complexity', 0))
    
    def store_dependency(self, from_file: str, to_file: str, dep_type: str = 'imports'):
        with self.driver.session() as session:
            session.execute_write(self._create_dependency, from_file, to_file, dep_type)
    
    @staticmethod
    def _create_dependency(tx, from_file, to_file, dep_type):
        query = """
        MERGE (f1:File {path: $from_file})
        MERGE (f2:File {path: $to_file})
        MERGE (f1)-[d:DEPENDS_ON]->(f2)
        SET d.type = $dep_type
        """
        tx.run(query, from_file=from_file, to_file=to_file, dep_type=dep_type)
    
    def get_architecture_insights(self, repo_url: str) -> Dict[str, Any]:
        logger.info(f"Getting architecture insights for {repo_url}")
        with self.driver.session() as session:
            result = session.execute_read(self._analyze_architecture, repo_url)
            logger.info(f"Retrieved architecture insights: {len(result.get('most_changed_files', []))} changed files, {len(result.get('coupled_files', []))} coupled files")
            return result
    
    @staticmethod
    def _analyze_architecture(tx, repo_url):
        insights = {}
        
        core_modules_query = """
        MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(:Commit)-[:MODIFIES]->(f:File)
        WITH f, COUNT(DISTINCT f) as change_frequency
        ORDER BY change_frequency DESC
        LIMIT 10
        RETURN f.path as file, change_frequency
        """
        result = tx.run(core_modules_query, repo_url=repo_url)
        insights['most_changed_files'] = [{'file': r['file'], 'changes': r['change_frequency']} for r in result]
        
        coupling_query = """
        MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)
        MATCH (c)-[:MODIFIES]->(f1:File)
        MATCH (c)-[:MODIFIES]->(f2:File)
        WHERE f1.path < f2.path
        WITH f1.path as file1, f2.path as file2, COUNT(*) as co_changes
        ORDER BY co_changes DESC
        LIMIT 10
        RETURN file1, file2, co_changes
        """
        result = tx.run(coupling_query, repo_url=repo_url)
        insights['coupled_files'] = [{'file1': r['file1'], 'file2': r['file2'], 'co_changes': r['co_changes']} for r in result]
        
        complexity_query = """
        MATCH (f:File)-[:DEFINES]->(fn:Function)
        WHERE fn.complexity > 10
        RETURN f.path as file, fn.name as function, fn.complexity as complexity
        ORDER BY complexity DESC
        LIMIT 10
        """
        result = tx.run(complexity_query)
        insights['complex_functions'] = [{'file': r['file'], 'function': r['function'], 'complexity': r['complexity']} for r in result]
        
        return insights
    
    def query_evolution(self, file_path: str) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            return session.execute_read(self._get_file_evolution, file_path)
    
    @staticmethod
    def _get_file_evolution(tx, file_path):
        query = """
        MATCH (c:Commit)-[m:MODIFIES]->(f:File {path: $file_path})
        MATCH (a:Author)-[:AUTHORED]->(c)
        RETURN c.sha as commit, c.message as message, c.timestamp as timestamp,
               a.name as author, m.insertions as insertions, m.deletions as deletions
        ORDER BY c.timestamp DESC
        """
        result = tx.run(query, file_path=file_path)
        return [dict(r) for r in result]
    
    def find_architectural_patterns(self, repo_url: str) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(self._detect_patterns, repo_url)
    
    @staticmethod
    def _detect_patterns(tx, repo_url):
        patterns = {}
        
        mvc_query = """
        MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(:Commit)-[:MODIFIES]->(f:File)
        WITH f.path as path
        WHERE path CONTAINS 'model' OR path CONTAINS 'view' OR path CONTAINS 'controller'
           OR path CONTAINS 'template' OR path CONTAINS 'static'
        RETURN COUNT(DISTINCT path) as mvc_files
        """
        result = tx.run(mvc_query, repo_url=repo_url).single()
        patterns['mvc_pattern'] = result['mvc_files'] > 0 if result else False
        
        layered_query = """
        MATCH (f:File)
        WITH f.path as path
        WHERE path CONTAINS 'service' OR path CONTAINS 'repository' 
           OR path CONTAINS 'controller' OR path CONTAINS 'entity'
           OR path CONTAINS 'dto' OR path CONTAINS 'dao'
        RETURN COUNT(DISTINCT path) as layered_files
        """
        result = tx.run(layered_query).single()
        patterns['layered_architecture'] = result['layered_files'] > 3 if result else False
        
        microservice_query = """
        MATCH (f:File)
        WHERE f.path CONTAINS 'docker' OR f.path CONTAINS 'kubernetes'
           OR f.path CONTAINS '.yaml' OR f.path CONTAINS '.yml'
        RETURN COUNT(DISTINCT f.path) as config_files
        """
        result = tx.run(microservice_query).single()
        patterns['microservices'] = result['config_files'] > 0 if result else False
        
        return patterns
    
    def answer_architecture_question(self, question: str, repo_url: str) -> str:
        question_lower = question.lower()
        
        if 'depend' in question_lower or 'coupling' in question_lower:
            return self._answer_dependency_question(repo_url)
        elif 'complex' in question_lower:
            return self._answer_complexity_question(repo_url)
        elif 'pattern' in question_lower:
            return self._answer_pattern_question(repo_url)
        elif 'evolv' in question_lower or 'chang' in question_lower:
            return self._answer_evolution_question(repo_url)
        elif 'author' in question_lower or 'contributor' in question_lower:
            return self._answer_contributor_question(repo_url)
        else:
            return "I can answer questions about dependencies, complexity, patterns, evolution, and contributors."
    
    def _answer_dependency_question(self, repo_url: str) -> str:
        with self.driver.session() as session:
            query = """
            MATCH (f1:File)-[d:DEPENDS_ON]->(f2:File)
            WITH f1.path as source, f2.path as target, COUNT(d) as deps
            ORDER BY deps DESC
            LIMIT 5
            RETURN source, target, deps
            """
            result = session.run(query)
            deps = [f"{r['source']} -> {r['target']}" for r in result]
            if deps:
                return f"Top dependencies: {', '.join(deps)}"
            return "No explicit dependencies found. Consider running code analysis first."
    
    def _answer_complexity_question(self, repo_url: str) -> str:
        insights = self.get_architecture_insights(repo_url)
        complex_funcs = insights.get('complex_functions', [])
        if complex_funcs:
            top_complex = complex_funcs[:3]
            return f"Most complex functions: " + ", ".join([f"{f['function']} (complexity: {f['complexity']})" for f in top_complex])
        return "No complexity metrics available yet."
    
    def _answer_pattern_question(self, repo_url: str) -> str:
        patterns = self.find_architectural_patterns(repo_url)
        detected = [name.replace('_', ' ').title() for name, found in patterns.items() if found]
        if detected:
            return f"Detected architectural patterns: {', '.join(detected)}"
        return "No clear architectural patterns detected."
    
    def _answer_evolution_question(self, repo_url: str) -> str:
        insights = self.get_architecture_insights(repo_url)
        most_changed = insights.get('most_changed_files', [])
        if most_changed:
            top_files = most_changed[:3]
            return f"Most frequently changed files: " + ", ".join([f['file'] for f in top_files])
        return "No evolution data available."
    
    def _answer_contributor_question(self, repo_url: str) -> str:
        with self.driver.session() as session:
            query = """
            MATCH (r:Repository {url: $repo_url})-[:HAS_COMMIT]->(c:Commit)<-[:AUTHORED]-(a:Author)
            WITH a.name as author, COUNT(c) as commits
            ORDER BY commits DESC
            LIMIT 5
            RETURN author, commits
            """
            result = session.run(query, repo_url=repo_url)
            contributors = [f"{r['author']} ({r['commits']} commits)" for r in result]
            if contributors:
                return f"Top contributors: {', '.join(contributors)}"
            return "No contributor data available."
    
    def close(self):
        if self.driver:
            self.driver.close()