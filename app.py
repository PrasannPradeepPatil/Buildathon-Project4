from flask import Flask, render_template, request, jsonify
import os
import tempfile
import shutil
import logging
from git_analyzer import GitAnalyzer
from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Import enhanced components with graceful fallback
graph_db_available = False
enhanced_features_available = False

try:
    from graph_database import GraphDatabaseManager
    from enhanced_git_analyzer import EnhancedGitAnalyzer
    from architecture_analyzer import ArchitectureAnalyzer
    graph_db_available = True
except ImportError as e:
    print(f"Graph database features not available: {e}")
    GraphDatabaseManager = None
    EnhancedGitAnalyzer = None
    ArchitectureAnalyzer = None

try:
    from vector_graph_database import VectorGraphDatabase
    from llm_code_analyzer import LLMCodeAnalyzer
    from semantic_query_engine import SemanticQueryEngine
    enhanced_features_available = True
except ImportError as e:
    print(f"Enhanced AI features not available: {e}")
    VectorGraphDatabase = None
    LLMCodeAnalyzer = None
    SemanticQueryEngine = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize databases
db = Database()
graph_db = None
vector_db = None
llm_analyzer = None
semantic_engine = None

# Initialize graph database if available
if graph_db_available and GraphDatabaseManager:
    try:
        graph_db = GraphDatabaseManager()
        print("Connected to Neo4j graph database")
    except Exception as e:
        print(f"Graph database connection failed: {e}")
        graph_db = None

# Initialize enhanced features if available
if enhanced_features_available and all([VectorGraphDatabase, LLMCodeAnalyzer, SemanticQueryEngine]):
    try:
        vector_db = VectorGraphDatabase()
        llm_analyzer = LLMCodeAnalyzer()
        semantic_engine = SemanticQueryEngine(vector_db, llm_analyzer)
        print("Enhanced AI features initialized")
    except Exception as e:
        print(f"Enhanced features initialization failed: {e}")
        vector_db = None
        llm_analyzer = None
        semantic_engine = None

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
        'graph_db': 'connected' if graph_db and hasattr(graph_db, 'driver') and graph_db.driver else 'disconnected',
        'vector_db': 'available' if vector_db else 'unavailable',
        'llm_analyzer': 'available' if llm_analyzer else 'unavailable',
        'features': {
            'basic_analysis': True,
            'enhanced_analysis': graph_db_available and graph_db is not None,
            'ai_analysis': enhanced_features_available and llm_analyzer is not None
        }
    })

@app.route('/analyze-enhanced', methods=['POST'])
def analyze_repository_enhanced():
    try:
        repo_url = request.json.get('repo_url')
        logger.info(f"Starting enhanced analysis for repository: {repo_url}")
        
        if not repo_url:
            logger.warning("Repository URL missing in enhanced analysis request")
            return jsonify({'error': 'Repository URL is required'}), 400
        
        if not graph_db_available or not graph_db or not hasattr(graph_db, 'driver') or not graph_db.driver:
            logger.error("Graph database not available for enhanced analysis")
            return jsonify({'error': 'Enhanced analysis requires graph database connection'}), 503
        
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {temp_dir}")
        
        try:
            if not EnhancedGitAnalyzer:
                logger.error("Enhanced analyzer not available")
                return jsonify({'error': 'Enhanced analyzer not available'}), 503
                
            logger.info("Initializing enhanced analyzer with graph database")
            analyzer = EnhancedGitAnalyzer(graph_db)
            
            logger.info("Starting enhanced repository analysis")
            repo_data = analyzer.analyze_repository_full(repo_url, temp_dir)
            logger.info(f"Enhanced analysis complete: {len(repo_data.get('commits', []))} commits processed")
            
            logger.info("Storing enhanced analysis results")
            analysis_id = db.store_analysis(repo_url, repo_data)
            logger.info(f"Enhanced analysis stored with ID: {analysis_id}")
            
            return jsonify({
                'success': True,
                'analysis_id': analysis_id,
                'data': repo_data
            })
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
                
    except Exception as e:
        logger.error(f"Enhanced analysis failed for {repo_url}: {str(e)}", exc_info=True)
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
        
        logger.info(f"Semantic question asked for {repo_url}: {question}")
        
        if not question or not repo_url:
            logger.warning("Missing question or repository URL in semantic query")
            return jsonify({'error': 'Question and repository URL are required'}), 400
        
        if not semantic_engine:
            logger.error("Semantic engine not available")
            return jsonify({'error': 'Semantic engine not available'}), 503
        
        logger.info("Processing semantic question with engine")
        answer = semantic_engine.answer_question(question, repo_url, context)
        logger.info(f"Semantic question processed successfully, answer type: {answer.get('answer_type')}")
        
        return jsonify({
            'success': True,
            'answer': answer
        })
        
    except Exception as e:
        logger.error(f"Semantic question failed for {repo_url}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-with-llm', methods=['POST'])
def analyze_with_llm():
    try:
        repo_url = request.json.get('repo_url')
        analyze_prs = request.json.get('analyze_prs', False)
        
        logger.info(f"Starting LLM analysis for repository: {repo_url}, analyze_prs: {analyze_prs}")
        
        if not repo_url:
            logger.warning("Repository URL missing in LLM analysis request")
            return jsonify({'error': 'Repository URL is required'}), 400
        
        # Check for OpenAI API key
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            logger.error("OpenAI API key not found for LLM analysis")
            return jsonify({
                'error': 'OpenAI API key required for AI analysis. Please add OPENAI_API_KEY to your secrets.',
                'suggestion': 'Add your OpenAI API key in Replit Secrets (Tools → Secrets)'
            }), 503
        
        if not llm_analyzer:
            logger.error("LLM analyzer not available")
            return jsonify({'error': 'LLM analyzer not available'}), 503
        
        temp_dir = tempfile.mkdtemp()
        logger.info(f"Created temporary directory: {temp_dir}")
        
        try:
            # Enhanced analysis with embeddings
            logger.info("Starting enhanced repository analysis")
            analyzer = EnhancedGitAnalyzer(vector_db)
            repo_data = analyzer.analyze_repository_full(repo_url, temp_dir, max_commits=100)
            logger.info(f"Repository analysis complete: {len(repo_data.get('commits', []))} commits analyzed")
            
            # Analyze PRs if requested and available
            pr_analysis = []
            if analyze_prs:
                logger.info("Starting PR analysis")
                prs = llm_analyzer.fetch_github_prs(repo_url, limit=20)
                logger.info(f"Fetched {len(prs)} PRs for analysis")
                
                for i, pr in enumerate(prs):
                    logger.debug(f"Analyzing PR {i+1}/{len(prs)}: #{pr.get('number')}")
                    pr_analysis.append(llm_analyzer.analyze_pull_request(pr))
                    if vector_db:
                        vector_db.store_pull_request(pr, repo_url)
                
                logger.info(f"PR analysis complete: {len(pr_analysis)} PRs analyzed")
            
            # Generate narrative
            logger.info("Generating change narrative")
            narrative = llm_analyzer.generate_change_narrative(repo_data['commits'])
            logger.info("Change narrative generation complete")
            
            # Store in database
            logger.info("Storing analysis results in database")
            analysis_id = db.store_analysis(repo_url, {
                **repo_data,
                'pr_analysis': pr_analysis,
                'narrative': narrative
            })
            logger.info(f"Analysis stored with ID: {analysis_id}")
            
            # Get semantic clusters if available
            semantic_clusters = None
            if vector_db:
                logger.info("Identifying semantic clusters")
                semantic_clusters = vector_db.identify_semantic_clusters(repo_url)
                logger.info(f"Semantic clustering complete: {semantic_clusters.get('num_clusters', 0)} clusters found")
            
            logger.info(f"LLM analysis complete for {repo_url}")
            return jsonify({
                'success': True,
                'analysis_id': analysis_id,
                'repository': repo_data['repository'],
                'narrative': narrative,
                'pr_count': len(pr_analysis),
                'semantic_clusters': semantic_clusters
            })
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
                
    except Exception as e:
        logger.error(f"LLM analysis failed for {repo_url}: {str(e)}", exc_info=True)
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