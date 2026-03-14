"""
RAG Engine (Retrieval Augmented Generation) with FAISS for L'Arbre à Café.
Provides semantic vector search over the knowledge base.
"""

import os
import json
import pickle
import hashlib
from typing import List, Dict, Tuple
import numpy as np
import faiss
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class RAGEngine:
    """Semantic search engine using embeddings and FAISS."""

    def __init__(self, knowledge_file: str = "larbrecaf_knowledge_industrial_2025.json", force_rebuild: bool = False):
        self.knowledge_file = knowledge_file
        self.embedding_dim = 1536  # Dimension of OpenAI embeddings (text-embedding-ada-002)
        self.cache_file = "embeddings_cache.pkl"

        # Delete the cache if force_rebuild is enabled
        if force_rebuild and os.path.exists(self.cache_file):
            os.remove(self.cache_file)
            print("Embedding cache deleted (force_rebuild=True)")

        # Load the knowledge base data
        self.data = self._load_knowledge()
        self.documents = self._prepare_documents()

        # Initialize the FAISS index
        self.index = None
        self.embeddings = None

    def _load_knowledge(self) -> Dict:
        """Load the knowledge base JSON."""
        with open(self.knowledge_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _prepare_documents(self) -> List[Dict]:
        """Prepare all documents for indexing."""
        documents = []

        # 1. Documents from scraped pages
        pages_categorie = self.data.get('pages_par_categorie', {})
        for category, pages in pages_categorie.items():
            for page in pages:
                if page.get('content'):
                    documents.append({
                        'id': f"page_{len(documents)}",
                        'type': 'page',
                        'category': category,
                        'title': page.get('title', ''),
                        'url': page.get('url', ''),
                        'text': page.get('content', ''),
                        'metadata': {
                            'category': category,
                            'url': page.get('url', '')
                        }
                    })

        # 2. Documents from boutiques
        boutiques = self.data.get('boutiques', [])
        for boutique in boutiques:
            # Extract the city from the name
            name = boutique.get('name', '')
            ville = ''
            if name:
                parts = name.split()
                if len(parts) > 1:
                    ville = ' '.join(parts[1:]).strip()

            # Create a rich text for each boutique
            text_parts = [
                f"Boutique {name}",
                f"Situé à {boutique.get('adresse', '')}",
                f"Ville: {ville}" if ville else "",
                f"Téléphone: {boutique.get('telephone', '')}",
                f"Email: {boutique.get('email', '')}",
            ]

            # Add horaires if available
            horaires = boutique.get('horaires', {})
            if horaires:
                text_parts.append("Horaires d'ouverture:")
                if isinstance(horaires, dict):
                    for jour, heures in horaires.items():
                        text_parts.append(f"{jour}: {heures}")
                else:
                    text_parts.append(str(horaires))

            # Add services
            services = boutique.get('services', [])
            if services:
                text_parts.append(f"Services: {', '.join(services)}")

            # Add URL if available
            url = boutique.get('url', '')
            if url:
                text_parts.append(f'Lien: <a href="{url}" target="_blank">Voir cette boutique</a>')

            text = '\n'.join([p for p in text_parts if p])

            documents.append({
                'id': f"boutique_{boutique.get('name', len(documents))}",
                'type': 'boutique',
                'category': 'boutique',
                'title': name,
                'ville': ville,
                'text': text,
                'metadata': {
                    'adresse': boutique.get('adresse', ''),
                    'telephone': boutique.get('telephone', ''),
                    'email': boutique.get('email', ''),
                    'ville': ville
                }
            })

        # 3. General information
        infos_gen = self.data.get('informations_generales', {})
        if infos_gen:
            text_gen = f"Informations générales larbrecaf:\n{json.dumps(infos_gen, indent=2, ensure_ascii=False)}"
            documents.append({
                'id': 'info_generale',
                'type': 'info_generale',
                'category': 'general',
                'title': 'Informations générales',
                'text': text_gen,
                'metadata': infos_gen
            })

        return documents

    def _get_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding OpenAI for a text."""
        response = client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return np.array(response.data[0].embedding, dtype=np.float32)

    def _get_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for several texts in batch."""
        embeddings = []
        batch_size = 20  # OpenAI limit

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            print(f"  Batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...")
            response = client.embeddings.create(
                input=batch,
                model="text-embedding-ada-002"
            )
            batch_embeddings = [np.array(item.embedding, dtype=np.float32) 
                              for item in response.data]
            embeddings.extend(batch_embeddings)

        return np.array(embeddings)

    def _get_cache_key(self) -> str:
        """Generate a cache key based on the JSON content."""
        with open(self.knowledge_file, 'rb') as f:
            content = f.read()
        return hashlib.md5(content).hexdigest()

    def _build_or_load_index(self):
        """Build the FAISS index or load it from cache."""
        cache_key = self._get_cache_key()

        # Try to load from cache
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)

                if cache_data.get('cache_key') == cache_key:
                    print("Chargement embeddings depuis cache...")
                    self.embeddings = cache_data['embeddings']
                    self.index = faiss.deserialize_index(cache_data['index'])
                    print(f"{len(self.documents)} embeddings charges depuis cache")
                    return
            except Exception as e:
                print(f"Erreur chargement cache: {e}")

        # Build the index from scratch
        print("Construction de l'index FAISS...")

        # Generate embeddings
        texts = [doc['text'][:8002] for doc in self.documents]  # Limit size
        print(f"Génération de {len(texts)} embeddings...")
        self.embeddings = self._get_embeddings_batch(texts)

        # Create the FAISS index
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(self.embeddings)

        # Save to cache
        cache_data = {
            'cache_key': cache_key,
            'embeddings': self.embeddings,
            'index': faiss.serialize_index(self.index)
        }
        with open(self.cache_file, 'wb') as f:
            pickle.dump(cache_data, f)

        print(f"Index construit: {self.index.ntotal} vecteurs")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Semantic search in the knowledge base.

        Args:
            query: User's question
            top_k: Number of results to return

        Returns:
            List of relevant documents with scores
        """
        # Generate embedding of the query
        query_embedding = self._get_embedding(query)
        query_vector = np.array([query_embedding])

        # Search in FAISS
        distances, indices = self.index.search(query_vector, top_k)

        # Prepare the results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                doc = self.documents[idx]

                # Score of similarity (inverse of the L2 distance)
                # Smaller L2 distance = more similar
                similarity_score = 1.0 / (1.0 + distance)

                results.append({
                    'type': doc['type'],
                    'category': doc['category'],
                    'title': doc['title'],
                    'content': doc['text'],
                    'metadata': doc.get('metadata', {}),
                    'score': float(similarity_score),
                    'distance': float(distance),
                    'data': doc
                })

        return results

    def get_context_for_llm(self, query: str, max_context_length: int = 4000) -> str:
        """
        Retrieve the optimal context for the LLM.

        Args:
            query: User's question
            max_context_length: Maximum length of the context

        Returns:
            Formatted context for the LLM
        """
        results = self.search(query, top_k=10)

        context_parts = []
        current_length = 0

        for result in results:
            # Format the document
            doc_text = f"[{result['type'].upper()}] {result['title']}\n{result['content']}\n"
            doc_length = len(doc_text)

            if current_length + doc_length > max_context_length:
                # Truncate if necessary
                remaining = max_context_length - current_length
                if remaining > 200:
                    context_parts.append(doc_text[:remaining] + "...")
                break

            context_parts.append(doc_text)
            current_length += doc_length

        if not context_parts:
            return "Aucune information trouvée dans la base de connaissances."

        return "\n---\n".join(context_parts)


# For direct test
if __name__ == "__main__":
    print("Test RAG Engine\n")

    rag = RAGEngine()

    # Tests
    test_queries = [
        "dans quelles villes etes vous localises ?",
        "boutique à Paris",
        "horaires d'ouverture",
        "café bio",
        "programme fidélité"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

        results = rag.search(query, top_k=3)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['type']}] {result['title']}")
            print(f"   Score: {result['score']:.3f} | Distance: {result['distance']:.3f}")
            print(f"   {result['content'][:200]}...")
