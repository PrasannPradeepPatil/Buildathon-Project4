import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import openai
from openai import OpenAI
from dotenv import load_dotenv
import tiktoken
import hashlib
import json
import time

load_dotenv()

class EmbeddingManager:
    def __init__(self, model_type='openai'):
        self.model_type = model_type
        self.embedding_cache = {}
        
        if model_type == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI embeddings")
            self.client = OpenAI(api_key=api_key)
            self.model = 'text-embedding-3-small'  # Better performance and lower cost
            self.embedding_dim = 1536
        elif model_type == 'openai-large':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI embeddings")
            self.client = OpenAI(api_key=api_key)
            self.model = 'text-embedding-3-large'  # Highest quality
            self.embedding_dim = 3072
        elif model_type == 'openai-ada':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI embeddings")
            self.client = OpenAI(api_key=api_key)
            self.model = 'text-embedding-ada-002'  # Legacy model
            self.embedding_dim = 1536
        elif model_type == 'sentence-transformer':
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_dim = 384
        elif model_type == 'code-bert':
            self.model = SentenceTransformer('microsoft/codebert-base')
            self.embedding_dim = 768
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def generate_embedding(self, text: str, context_type: str = 'general') -> List[float]:
        cache_key = hashlib.md5(f"{text}{context_type}{self.model_type}".encode()).hexdigest()
        
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        if context_type == 'code':
            text = self._preprocess_code(text)
        elif context_type == 'commit':
            text = self._preprocess_commit_message(text)
        
        if self.model_type in ['sentence-transformer', 'code-bert']:
            embedding = self.model.encode(text).tolist()
        elif self.model_type.startswith('openai'):
            try:
                # Add context prefix for better embeddings
                if context_type == 'code':
                    text = f"Code: {text}"
                elif context_type == 'commit':
                    text = f"Commit message: {text}"
                
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    encoding_format="float"
                )
                embedding = response.data[0].embedding
                
                # Handle dimension reduction if needed
                if self.model_type == 'openai' and len(embedding) > 1536:
                    embedding = embedding[:1536]  # Truncate for compatibility
                    
            except Exception as e:
                print(f"OpenAI embedding failed: {e}")
                # Retry with exponential backoff
                try:
                    time.sleep(1)
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=text[:8000],  # Truncate if too long
                        encoding_format="float"
                    )
                    embedding = response.data[0].embedding
                    if self.model_type == 'openai' and len(embedding) > 1536:
                        embedding = embedding[:1536]
                except:
                    embedding = [0.0] * self.embedding_dim
        
        self.embedding_cache[cache_key] = embedding
        return embedding
    
    def generate_batch_embeddings(self, texts: List[str], context_type: str = 'general') -> List[List[float]]:
        if self.model_type in ['sentence-transformer', 'code-bert']:
            processed_texts = [self._preprocess_by_type(text, context_type) for text in texts]
            return self.model.encode(processed_texts).tolist()
        elif self.model_type.startswith('openai'):
            # OpenAI supports batch embeddings efficiently
            try:
                processed_texts = []
                for text in texts:
                    if context_type == 'code':
                        text = self._preprocess_code(text)
                        text = f"Code: {text}"
                    elif context_type == 'commit':
                        text = self._preprocess_commit_message(text)
                        text = f"Commit message: {text}"
                    processed_texts.append(text[:8000])  # Ensure within token limits
                
                # Process in batches of 100 for OpenAI
                all_embeddings = []
                batch_size = 100
                
                for i in range(0, len(processed_texts), batch_size):
                    batch = processed_texts[i:i + batch_size]
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=batch,
                        encoding_format="float"
                    )
                    batch_embeddings = [data.embedding for data in response.data]
                    
                    # Handle dimension reduction if needed
                    if self.model_type == 'openai' and batch_embeddings and len(batch_embeddings[0]) > 1536:
                        batch_embeddings = [emb[:1536] for emb in batch_embeddings]
                    
                    all_embeddings.extend(batch_embeddings)
                    
                    # Rate limiting
                    if i + batch_size < len(processed_texts):
                        time.sleep(0.1)
                
                return all_embeddings
                
            except Exception as e:
                print(f"Batch embedding failed: {e}")
                # Fallback to individual embeddings
                return [self.generate_embedding(text, context_type) for text in texts]
        else:
            return [self.generate_embedding(text, context_type) for text in texts]
    
    def _preprocess_code(self, code: str) -> str:
        lines = code.split('\n')
        processed_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                processed_lines.append(line)
        
        processed_code = ' '.join(processed_lines)
        
        if len(processed_code) > 1000:
            processed_code = processed_code[:1000]
        
        return processed_code
    
    def _preprocess_commit_message(self, message: str) -> str:
        lines = message.split('\n')
        title = lines[0] if lines else ""
        
        keywords = []
        if 'feat' in message.lower() or 'feature' in message.lower():
            keywords.append('feature')
        if 'fix' in message.lower() or 'bug' in message.lower():
            keywords.append('bugfix')
        if 'refactor' in message.lower():
            keywords.append('refactoring')
        if 'test' in message.lower():
            keywords.append('testing')
        if 'doc' in message.lower():
            keywords.append('documentation')
        
        enhanced_message = f"{title} {' '.join(keywords)} {message}"
        
        return enhanced_message[:500]
    
    def _preprocess_by_type(self, text: str, context_type: str) -> str:
        if context_type == 'code':
            return self._preprocess_code(text)
        elif context_type == 'commit':
            return self._preprocess_commit_message(text)
        return text
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar(self, query_embedding: List[float], 
                    embeddings: List[Tuple[str, List[float]]], 
                    top_k: int = 5, 
                    threshold: float = 0.0) -> List[Tuple[str, float]]:
        similarities = []
        
        for item_id, embedding in embeddings:
            similarity = self.calculate_similarity(query_embedding, embedding)
            if similarity >= threshold:
                similarities.append((item_id, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def create_code_summary_embedding(self, code_diff: str, commit_message: str) -> List[float]:
        code_embedding = self.generate_embedding(code_diff, 'code')
        commit_embedding = self.generate_embedding(commit_message, 'commit')
        
        combined = np.mean([code_embedding, commit_embedding], axis=0)
        
        return combined.tolist()
    
    def cluster_embeddings(self, embeddings: List[List[float]], n_clusters: int = 5) -> List[int]:
        from sklearn.cluster import KMeans
        
        if len(embeddings) < n_clusters:
            n_clusters = len(embeddings)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(embeddings)
        
        return clusters.tolist()
    
    def get_embedding_statistics(self, embeddings: List[List[float]]) -> Dict[str, Any]:
        embeddings_array = np.array(embeddings)
        
        return {
            'count': len(embeddings),
            'dimension': embeddings_array.shape[1] if len(embeddings) > 0 else 0,
            'mean_magnitude': float(np.mean(np.linalg.norm(embeddings_array, axis=1))),
            'std_magnitude': float(np.std(np.linalg.norm(embeddings_array, axis=1))),
            'cache_size': len(self.embedding_cache)
        }


class CodeEmbeddingAnalyzer:
    def __init__(self, embedding_manager: EmbeddingManager):
        self.embedding_manager = embedding_manager
    
    def analyze_code_change(self, before_code: str, after_code: str, 
                           file_path: str) -> Dict[str, Any]:
        before_embedding = self.embedding_manager.generate_embedding(before_code, 'code')
        after_embedding = self.embedding_manager.generate_embedding(after_code, 'code')
        
        similarity = self.embedding_manager.calculate_similarity(before_embedding, after_embedding)
        
        change_magnitude = np.linalg.norm(np.array(after_embedding) - np.array(before_embedding))
        
        return {
            'file_path': file_path,
            'semantic_similarity': similarity,
            'change_magnitude': float(change_magnitude),
            'change_type': self._classify_change(similarity),
            'before_embedding': before_embedding,
            'after_embedding': after_embedding
        }
    
    def _classify_change(self, similarity: float) -> str:
        if similarity > 0.95:
            return 'minor_change'
        elif similarity > 0.8:
            return 'moderate_change'
        elif similarity > 0.5:
            return 'significant_change'
        else:
            return 'major_refactoring'
    
    def analyze_commit_context(self, commit_message: str, 
                              files_changed: List[str],
                              code_diffs: List[str]) -> Dict[str, Any]:
        commit_embedding = self.embedding_manager.generate_embedding(commit_message, 'commit')
        
        file_embeddings = []
        for code_diff in code_diffs[:10]:  
            file_embeddings.append(
                self.embedding_manager.generate_embedding(code_diff, 'code')
            )
        
        if file_embeddings:
            avg_file_embedding = np.mean(file_embeddings, axis=0)
            coherence_score = self.embedding_manager.calculate_similarity(
                commit_embedding, 
                avg_file_embedding.tolist()
            )
        else:
            coherence_score = 0.0
        
        return {
            'commit_message': commit_message,
            'files_changed': len(files_changed),
            'coherence_score': coherence_score,
            'commit_embedding': commit_embedding,
            'interpretation': self._interpret_coherence(coherence_score)
        }
    
    def _interpret_coherence(self, score: float) -> str:
        if score > 0.7:
            return 'High coherence: commit message aligns well with code changes'
        elif score > 0.4:
            return 'Moderate coherence: commit message partially reflects code changes'
        else:
            return 'Low coherence: commit message may not accurately describe changes'
    
    def find_similar_commits(self, query: str, commit_embeddings: List[Tuple[str, List[float]]], 
                            top_k: int = 10) -> List[Tuple[str, float]]:
        query_embedding = self.embedding_manager.generate_embedding(query, 'commit')
        return self.embedding_manager.find_similar(query_embedding, commit_embeddings, top_k)
    
    def identify_semantic_patterns(self, commit_embeddings: List[List[float]], 
                                  n_patterns: int = 5) -> Dict[str, Any]:
        clusters = self.embedding_manager.cluster_embeddings(commit_embeddings, n_patterns)
        
        cluster_counts = {}
        for cluster in clusters:
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        
        return {
            'n_patterns': n_patterns,
            'cluster_assignments': clusters,
            'cluster_sizes': cluster_counts,
            'dominant_pattern': max(cluster_counts, key=cluster_counts.get) if cluster_counts else None
        }