from flask import Flask, render_template, request, jsonify
import os
import tempfile
import shutil
from git_analyzer import GitAnalyzer
from database import Database

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize database
db = Database()

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
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    db.init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)