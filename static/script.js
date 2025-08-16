let currentAnalysis = null;
let currentRepoUrl = null;

async function checkFeatures() {
    try {
        const response = await fetch('/health');
        const health = await response.json();
        return health.features || {};
    } catch (error) {
        console.error('Error checking features:', error);
        return { basic_analysis: true, enhanced_analysis: false, ai_analysis: false };
    }
}

async function analyzeRepository() {
    const repoUrl = document.getElementById('repo-url').value.trim();
    const analysisType = document.getElementById('analysis-type').value;
    const analyzePRs = document.getElementById('analyze-prs').checked;

    if (!repoUrl) {
        showError('Please enter a repository URL');
        return;
    }

    // Check feature availability
    const features = await checkFeatures();

    if (analysisType === 'enhanced' && !features.enhanced_analysis) {
        showError('Enhanced analysis is not available. Graph database is not connected.');
        return;
    }

    if (analysisType === 'llm' && !features.ai_analysis) {
        showError('AI-powered analysis is not available. LLM components are not initialized.');
        return;
    }

    currentRepoUrl = repoUrl;

    // Show loading state
    showLoading();
    hideResults();
    hideError();

    try {
        let endpoint = '/analyze';
        let requestBody = { repo_url: repoUrl };

        // Choose endpoint based on analysis type
        switch (analysisType) {
            case 'enhanced':
                endpoint = '/analyze-enhanced';
                break;
            case 'llm':
                endpoint = '/analyze-with-llm';
                requestBody.analyze_prs = analyzePRs;
                break;
            case 'basic':
            default:
                endpoint = '/analyze';
                break;
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            currentAnalysis = data.data || data;
            displayResults(currentAnalysis, analysisType);
        } else {
            showError(data.error || 'Analysis failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function analyzeArchitecture() {
    if (!currentRepoUrl) {
        alert('Please analyze a repository first');
        return;
    }

    showLoading();

    try {
        const response = await fetch('/architecture-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ repo_url: currentRepoUrl })
        });

        const data = await response.json();

        if (data.success) {
            displayArchitectureAnalysis(data.analysis);
        } else {
            showError(data.error || 'Architecture analysis failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    } finally {
        hideLoading();
    }
}

async function performSemanticSearch() {
    const query = document.getElementById('semantic-query').value.trim();

    if (!query || !currentRepoUrl) {
        alert('Please enter a search query and analyze a repository first');
        return;
    }

    try {
        const response = await fetch('/semantic-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                query: query,
                repo_url: currentRepoUrl 
            })
        });

        const data = await response.json();

        if (data.success) {
            displaySemanticResults(data);
        } else {
            showError(data.error || 'Semantic search failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

async function askSemanticQuestion() {
    const question = document.getElementById('semantic-question').value.trim();

    if (!question || !currentRepoUrl) {
        alert('Please enter a question and analyze a repository first');
        return;
    }

    try {
        const response = await fetch('/ask-semantic', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                question: question,
                repo_url: currentRepoUrl 
            })
        });

        const data = await response.json();

        if (data.success) {
            displaySemanticAnswer(data.answer);
        } else {
            showError(data.error || 'Question answering failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

function displayResults(data, analysisType = 'basic') {
    // Update repository info
    document.getElementById('repo-name').textContent = data.repository.name;
    document.getElementById('total-commits').textContent = data.repository.total_commits || data.total_commits_analyzed || 0;
    document.getElementById('total-contributors').textContent = data.insights?.total_contributors || 0;
    document.getElementById('total-files').textContent = data.files?.length || data.file_structure?.total_files || 0;

    // Display insights
    if (data.insights) {
        displayInsights(data.insights);
    }

    // Display contributors
    if (data.contributors) {
        displayContributors(data.contributors);
    }

    // Display commits
    if (data.commits) {
        displayCommits(data.commits);
    }

    // Enhanced analysis features
    if (analysisType === 'enhanced' || analysisType === 'llm') {
        if (data.file_structure) {
            displayFileStructure(data.file_structure);
        }

        if (data.dependencies) {
            displayDependencies(data.dependencies);
        }

        if (data.architecture_metrics) {
            displayArchitectureMetrics(data.architecture_metrics);
        }

        if (data.evolution_patterns) {
            displayEvolutionPatterns(data.evolution_patterns);
        }

        if (data.narrative) {
            displayNarrative(data.narrative);
        }

        if (data.pr_count) {
            displayPRAnalysis(data.pr_count);
        }

        if (data.semantic_clusters) {
            displaySemanticClusters(data.semantic_clusters);
        }
    }

    showResults();
}

function displayInsights(insights) {
    const container = document.getElementById('insights-content');
    container.innerHTML = '';

    const insightItems = [
        { label: 'Most Active Contributor', value: insights.most_active_contributor },
        { label: 'Most Common Commit Type', value: insights.most_common_commit_type },
        { label: 'Avg Files per Commit', value: insights.avg_files_per_commit?.toFixed(1) || '0' },
        { label: 'Total Contributors', value: insights.total_contributors }
    ];

    insightItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'insight-item';
        div.innerHTML = `
            <span class="insight-label">${item.label}:</span>
            <span class="insight-value">${item.value}</span>
        `;
        container.appendChild(div);
    });
}

function displayContributors(contributors) {
    const container = document.getElementById('contributors-list');
    container.innerHTML = '';

    contributors.slice(0, 10).forEach(contributor => {
        const div = document.createElement('div');
        div.className = 'contributor-item';
        div.innerHTML = `
            <div class="contributor-name">${contributor.name}</div>
            <div class="contributor-stats">
                ${contributor.commits} commits • 
                +${contributor.insertions}/-${contributor.deletions} lines
            </div>
        `;
        container.appendChild(div);
    });
}

function displayCommits(commits) {
    const container = document.getElementById('commits-list');
    container.innerHTML = '';

    commits.slice(0, 20).forEach(commit => {
        const div = document.createElement('div');
        div.className = 'commit-item';

        const date = new Date(commit.date).toLocaleDateString();
        const time = new Date(commit.date).toLocaleTimeString();

        div.innerHTML = `
            <div class="commit-message">${commit.message}</div>
            <div class="commit-meta">
                <span class="commit-type">${commit.type}</span>
                <span>👤 ${commit.author}</span>
                <span>📅 ${date} ${time}</span>
                <span>📁 ${commit.files_changed} files</span>
                <span>📊 +${commit.insertions}/-${commit.deletions}</span>
            </div>
        `;
        container.appendChild(div);
    });
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('analyze-btn').disabled = true;
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('analyze-btn').disabled = false;
}

function showResults() {
    document.getElementById('results').classList.remove('hidden');
}

function hideResults() {
    document.getElementById('results').classList.add('hidden');
}

function displayFileStructure(fileStructure) {
    const container = document.getElementById('file-structure-content');
    if (!container) return;

    container.innerHTML = '';

    const languageList = Object.entries(fileStructure.by_language)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 10);

    languageList.forEach(([language, count]) => {
        const div = document.createElement('div');
        div.className = 'language-item';
        div.innerHTML = `
            <span class="language-name">${language}</span>
            <span class="language-count">${count} files</span>
        `;
        container.appendChild(div);
    });
}

function displayDependencies(dependencies) {
    const container = document.getElementById('dependencies-content');
    if (!container) return;

    container.innerHTML = '';

    Object.entries(dependencies.package_managers).forEach(([manager, deps]) => {
        if (deps.length > 0) {
            const div = document.createElement('div');
            div.className = 'dependency-manager';
            div.innerHTML = `
                <h4>${manager.toUpperCase()}</h4>
                <div class="deps-list">${deps.slice(0, 10).join(', ')}</div>
            `;
            container.appendChild(div);
        }
    });
}

function displayArchitectureMetrics(metrics) {
    const container = document.getElementById('architecture-metrics-content');
    if (!container) return;

    container.innerHTML = '';

    const metricItems = [
        { label: 'Modularity Score', value: metrics.modularity_score?.toFixed(1) || '0' },
        { label: 'Coupling Score', value: metrics.coupling_score?.toFixed(1) || '0' },
        { label: 'Cohesion Score', value: metrics.cohesion_score?.toFixed(1) || '0' },
        { label: 'Maintainability Index', value: metrics.maintainability_index?.toFixed(1) || '0' }
    ];

    metricItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'metric-item';
        div.innerHTML = `
            <span class="metric-label">${item.label}:</span>
            <span class="metric-value">${item.value}</span>
        `;
        container.appendChild(div);
    });
}

function displayEvolutionPatterns(patterns) {
    const container = document.getElementById('evolution-patterns-content');
    if (!container) return;

    container.innerHTML = '';

    const topContributors = Object.entries(patterns.author_contributions)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5);

    topContributors.forEach(([author, commits]) => {
        const div = document.createElement('div');
        div.className = 'evolution-item';
        div.innerHTML = `
            <span class="evolution-author">${author}</span>
            <span class="evolution-commits">${commits} commits</span>
        `;
        container.appendChild(div);
    });
}

function displayNarrative(narrative) {
    const container = document.getElementById('narrative-content');
    if (!container) return;

    container.innerHTML = `<div class="narrative-text">${narrative}</div>`;
}

function displayPRAnalysis(prCount) {
    const container = document.getElementById('pr-analysis-content');
    if (!container) return;

    container.innerHTML = `<div class="pr-count">Analyzed ${prCount} pull requests</div>`;
}

function displaySemanticClusters(clusters) {
    const container = document.getElementById('semantic-clusters-content');
    if (!container) return;

    container.innerHTML = '';

    if (clusters && clusters.length > 0) {
        clusters.forEach((cluster, index) => {
            const div = document.createElement('div');
            div.className = 'cluster-item';
            div.innerHTML = `
                <span class="cluster-label">Cluster ${index + 1}:</span>
                <span class="cluster-description">${cluster.description || 'Semantic group'}</span>
            `;
            container.appendChild(div);
        });
    }
}

function displayArchitectureAnalysis(analysis) {
    const container = document.getElementById('architecture-analysis-content');
    if (!container) return;

    container.innerHTML = `<pre class="architecture-analysis">${JSON.stringify(analysis, null, 2)}</pre>`;
}

function displaySemanticResults(data) {
    const container = document.getElementById('semantic-results-content');
    if (!container) return;

    container.innerHTML = '';

    if (data.results && data.results.length > 0) {
        data.results.forEach(result => {
            const div = document.createElement('div');
            div.className = 'semantic-result-item';
            div.innerHTML = `
                <div class="result-message">${result.message || result.title}</div>
                <div class="result-score">Relevance: ${(result.score * 100).toFixed(1)}%</div>
            `;
            container.appendChild(div);
        });
    }

    if (data.recommendations && data.recommendations.length > 0) {
        const recDiv = document.createElement('div');
        recDiv.innerHTML = '<h4>Recommendations:</h4>';
        data.recommendations.forEach(rec => {
            const div = document.createElement('div');
            div.className = 'recommendation-item';
            div.textContent = rec;
            recDiv.appendChild(div);
        });
        container.appendChild(recDiv);
    }
}

function displaySemanticAnswer(answer) {
    const container = document.getElementById('semantic-answer-content');
    if (!container) return;

    container.innerHTML = `<div class="semantic-answer">${answer}</div>`;
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('error').classList.remove('hidden');
}

function hideError() {
    document.getElementById('error').classList.add('hidden');
}

// Allow Enter key to trigger analysis
document.getElementById('repo-url').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        analyzeRepository();
    }
});

// Allow Enter key for semantic search
document.addEventListener('DOMContentLoaded', function() {
    const semanticQuery = document.getElementById('semantic-query');
    if (semanticQuery) {
        semanticQuery.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSemanticSearch();
            }
        });
    }

    const semanticQuestion = document.getElementById('semantic-question');
    if (semanticQuestion) {
        semanticQuestion.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                askSemanticQuestion();
            }
        });
    }
});