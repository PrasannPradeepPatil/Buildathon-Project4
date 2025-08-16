from flask import Flask, render_template, request, jsonify
import os
import tempfile
import shutil
from git_analyzer import GitAnalyzer
from database import Database
from graph_database import GraphDatabaseManager
from enhanced_git_analyzer import EnhancedGitAnalyzer
from architecture_analyzer import ArchitectureAnalyzer
from vector_graph_database import VectorGraphDatabase
from llm_code_analyzer import LLMCodeAnalyzer
from semantic_query_engine import SemanticQueryEngine

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize databases
db = Database()
graph_db = None
vector_db = None
llm_analyzer = None
semantic_engine = None

try:
    graph_db = GraphDatabaseManager()
    vector_db = VectorGraphDatabase()
    llm_analyzer = LLMCodeAnalyzer()
    semantic_engine = SemanticQueryEngine(vector_db, llm_analyzer)
    print("Connected to Neo4j graph database with vector support")
except Exception as e:
    print(f"Graph database not available: {e}")
    graph_db = None
    vector_db = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_repository():
    try:
        repo_url = request.json.get('repo_url')
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            analyzer = GitAnalyzer()
            repo_data = analyzer.analyze_repository(repo_url, temp_dir)
            analysis_id = db.store_analysis(repo_url, repo_data)
            
            return jsonify({
                'success': True,
                'analysis_id': analysis_id,
                'data': repo_data
            })
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'graph_db': 'connected' if graph_db and graph_db.driver else 'disconnected'
    })

@app.route('/analyze-enhanced', methods=['POST'])
def analyze_repository_enhanced():
    try:
        repo_url = request.json.get('repo_url')
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        if not graph_db or not graph_db.driver:
            return jsonify({'error': 'Graph database not available'}), 503
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            analyzer = EnhancedGitAnalyzer(graph_db)
            repo_data = analyzer.analyze_repository_full(repo_url, temp_dir)
            analysis_id = db.store_analysis(repo_url, repo_data)
            
            return jsonify({
                'success': True,
                'analysis_id': analysis_id,
                'data': repo_data
            })
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/architecture-analysis', methods=['POST'])
def analyze_architecture():
    try:
        repo_url = request.json.get('repo_url')
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        if not graph_db or not graph_db.driver:
            return jsonify({'error': 'Graph database not available'}), 503
        
        arch_analyzer = ArchitectureAnalyzer(graph_db)
        analysis = arch_analyzer.analyze_architecture(repo_url)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ask-architecture', methods=['POST'])
def ask_architecture_question():
    try:
        repo_url = request.json.get('repo_url')
        question = request.json.get('question')
        
        if not repo_url or not question:
            return jsonify({'error': 'Repository URL and question are required'}), 400
        
        if not graph_db or not graph_db.driver:
            return jsonify({'error': 'Graph database not available'}), 503
        
        arch_analyzer = ArchitectureAnalyzer(graph_db)
        response = arch_analyzer.answer_architecture_question(question, repo_url)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/query-evolution', methods=['POST'])
def query_file_evolution():
    try:
        file_path = request.json.get('file_path')
        
        if not file_path:
            return jsonify({'error': 'File path is required'}), 400
        
        if not graph_db or not graph_db.driver:
            return jsonify({'error': 'Graph database not available'}), 503
        
        evolution = graph_db.query_evolution(file_path)
        
        return jsonify({
            'success': True,
            'evolution': evolution
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/repository-insights/<repo_url>', methods=['GET'])
def get_repository_insights(repo_url):
    try:
        if not graph_db or not graph_db.driver:
            return jsonify({'error': 'Graph database not available'}), 503
        
        insights = graph_db.get_architecture_insights(repo_url)
        patterns = graph_db.find_architectural_patterns(repo_url)
        
        return jsonify({
            'success': True,
            'insights': insights,
            'patterns': patterns
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/semantic-search', methods=['POST'])
def semantic_search():
    try:
        query = request.json.get('query')
        repo_url = request.json.get('repo_url')
        
        if not query or not repo_url:
            return jsonify({'error': 'Query and repository URL are required'}), 400
        
        if not vector_db or not vector_db.driver:
            return jsonify({'error': 'Vector database not available'}), 503
        
        results = vector_db.semantic_search_commits(query, repo_url)
        recommendations = vector_db.get_contextual_recommendations(query, repo_url)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'recommendations': recommendations
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ask-semantic', methods=['POST'])
def ask_semantic_question():
    try:
        question = request.json.get('question')
        repo_url = request.json.get('repo_url')
        context = request.json.get('context', {})
        
        if not question or not repo_url:
            return jsonify({'error': 'Question and repository URL are required'}), 400
        
        if not semantic_engine:
            return jsonify({'error': 'Semantic engine not available'}), 503
        
        answer = semantic_engine.answer_question(question, repo_url, context)
        
        return jsonify({
            'success': True,
            'answer': answer
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-with-llm', methods=['POST'])
def analyze_with_llm():
    try:
        repo_url = request.json.get('repo_url')
        analyze_prs = request.json.get('analyze_prs', False)
        
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        if not llm_analyzer:
            return jsonify({'error': 'LLM analyzer not available'}), 503
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Enhanced analysis with embeddings
            analyzer = EnhancedGitAnalyzer(vector_db)
            repo_data = analyzer.analyze_repository_full(repo_url, temp_dir, max_commits=100)
            
            # Analyze PRs if requested and available
            pr_analysis = []
            if analyze_prs:
                prs = llm_analyzer.fetch_github_prs(repo_url, limit=20)
                for pr in prs:
                    pr_analysis.append(llm_analyzer.analyze_pull_request(pr))
                    if vector_db:
                        vector_db.store_pull_request(pr, repo_url)
            
            # Generate narrative
            narrative = llm_analyzer.generate_change_narrative(repo_data['commits'])
            
            # Store in database
            analysis_id = db.store_analysis(repo_url, {
                **repo_data,
                'pr_analysis': pr_analysis,
                'narrative': narrative
            })
            
            return jsonify({
                'success': True,
                'analysis_id': analysis_id,
                'repository': repo_data['repository'],
                'narrative': narrative,
                'pr_count': len(pr_analysis),
                'semantic_clusters': vector_db.identify_semantic_clusters(repo_url) if vector_db else None
            })
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/file-evolution', methods=['POST'])
def analyze_file_evolution():
    try:
        file_path = request.json.get('file_path')
        repo_url = request.json.get('repo_url')
        
        if not file_path or not repo_url:
            return jsonify({'error': 'File path and repository URL are required'}), 400
        
        if not vector_db or not vector_db.driver:
            return jsonify({'error': 'Vector database not available'}), 503
        
        evolution = vector_db.analyze_semantic_evolution(file_path)
        similar_files = vector_db.find_similar_changes(file_path)
        
        return jsonify({
            'success': True,
            'evolution': evolution,
            'similar_files': similar_files
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    db.init_db()
    if graph_db:
        print("Graph database available for enhanced analysis")
    else:
        print("Running in basic mode without graph database")
    app.run(host='0.0.0.0', port=5000, debug=True)