let currentAnalysis = null;

async function analyzeRepository() {
    const repoUrl = document.getElementById('repo-url').value.trim();
    
    if (!repoUrl) {
        alert('Please enter a repository URL');
        return;
    }
    
    // Show loading state
    showLoading();
    hideResults();
    hideError();
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ repo_url: repoUrl })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentAnalysis = data.data;
            displayResults(data.data);
        } else {
            showError(data.error || 'Analysis failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    } finally {
        hideLoading();
    }
}

function displayResults(data) {
    // Update repository info
    document.getElementById('repo-name').textContent = data.repository.name;
    document.getElementById('total-commits').textContent = data.repository.total_commits;
    document.getElementById('total-contributors').textContent = data.insights.total_contributors || 0;
    document.getElementById('total-files').textContent = data.files.length;
    
    // Display insights
    displayInsights(data.insights);
    
    // Display contributors
    displayContributors(data.contributors);
    
    // Display commits
    displayCommits(data.commits);
    
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