import os
import chromadb
from chromadb.utils import embedding_functions


# ─── Configuration ───────────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"

# Resolve the vector store path relative to this file
# so it always lands inside the Django project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "vector_store")
KNOWLEDGE_BASE_PATH = os.path.join(BASE_DIR, "chatbot", "knowledge_base")


def _get_collection():
    """
    Returns the ChromaDB collection.
    Called lazily so we don't initialise ChromaDB at import time
    (which would fail during Django migrations or tests).
    """
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)
    collection = client.get_or_create_collection(
        name="health_knowledge",
        embedding_function=embedding_func,
    )
    return collection


def index_knowledge_base():
    """
    Reads every .txt file from chatbot/knowledge_base/ and upserts it
    into the ChromaDB vector store.

    Safe to call multiple times — upsert means it will update existing
    documents if the file content has changed.

    Returns a summary string.
    """
    if not os.path.isdir(KNOWLEDGE_BASE_PATH):
        return f"Knowledge base folder not found at: {KNOWLEDGE_BASE_PATH}"

    collection = _get_collection()
    indexed = []

    for filename in os.listdir(KNOWLEDGE_BASE_PATH):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(KNOWLEDGE_BASE_PATH, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().strip()

        if not text:
            continue

        # Use the filename without extension as a stable document ID
        doc_id = filename[:-4]  # strip ".txt"

        collection.upsert(
            documents=[text],
            ids=[doc_id],
            metadatas=[{"source": filename, "path": file_path}],
        )
        indexed.append(filename)

    return f"Indexed {len(indexed)} articles: {', '.join(indexed)}"


def retrieve_context(query_text, n_results=2):
    """
    Searches the vector store for the most relevant knowledge-base articles
    given a free-text query (e.g. a list of symptoms the user reported).

    Parameters
    ----------
    query_text : str
        The search query — typically the user's symptom description or a
        comma-separated list of matched symptom names.
    n_results : int
        How many articles to return (default 2 keeps the LLM prompt compact).

    Returns
    -------
    str
        The concatenated text of the top matching articles, separated by a
        divider line.  Returns an empty string if the store is empty or the
        query fails.
    """
    if not query_text or not query_text.strip():
        return ""

    try:
        collection = _get_collection()

        # If the collection is empty, bail out gracefully
        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[query_text],
            n_results=min(n_results, collection.count()),
        )

        documents = results.get("documents", [[]])[0]
        if not documents:
            return ""

        return "\n\n---\n\n".join(documents)

    except Exception as e:
        # Never crash the main guidance flow because of RAG
        print(f"[RAG] retrieval error: {e}")
        return ""