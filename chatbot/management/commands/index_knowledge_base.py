from django.core.management.base import BaseCommand
from chatbot.rag_service import index_knowledge_base
 
 
class Command(BaseCommand):
    help = "Index the symptom knowledge base articles into ChromaDB for RAG retrieval"
 
    def handle(self, *args, **kwargs):
        self.stdout.write("Indexing knowledge base into ChromaDB...")
        result = index_knowledge_base()
        self.stdout.write(self.style.SUCCESS(result))
        self.stdout.write(
            self.style.SUCCESS(
                "\nDone! The vector store is ready for symptom-context retrieval."
            )
        )
 