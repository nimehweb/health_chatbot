import os
import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings

# 1. Set up the embedding model (runs locally)
# This model converts your text into numbers (vectors)
EMBED_MODEL = "all-MiniLM-L6-v2"
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBED_MODEL
)

# 2. Initialize ChromaDB
# This will create a folder named 'vector_store' in your project
client = chromadb.PersistentClient(path=os.path.join(settings.BASE_DIR, "vector_store"))
collection = client.get_or_create_collection(
    name="health_knowledge", 
    embedding_function=embedding_func
)

def index_knowledge_base():
    """Reads .txt files from knowledge_base folder and adds them to ChromaDB"""
    kb_path = os.path.join(settings.BASE_DIR, "chatbot", "knowledge_base")
    
    for filename in os.listdir(kb_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(kb_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                # Use the filename (without .txt) as the ID
                doc_id = filename.replace(".txt", "")
                
                # Add to the vector database
                collection.upsert(
                    documents=[text],
                    ids=[doc_id],
                    metadatas=[{"source": filename}]
                )
    return "Indexing complete!"

def retrieve_context(query_text):
    """Searches the database for the most relevant article"""
    results = collection.query(
        query_texts=[query_text],
        n_results=1 # We only want the most relevant article
    )
    if results['documents']:
        return results['documents'][0][0]
    return ""