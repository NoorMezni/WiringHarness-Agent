import os
from dotenv import load_dotenv
import ollama
from qdrant_client import QdrantClient
from openai import OpenAI

load_dotenv()


QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

client = QdrantClient( url=QDRANT_URL,api_key=QDRANT_API_KEY,)

collection_name = "Wiring_harness_collection"
openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

"""def encode(text):
    return ollama.embeddings(
        model="nomic-embed-text",
        prompt=text
    )["embedding"]"""

def encode(text):
    response = openrouter_client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def get_context(question_vector):
    results = client.query_points( collection_name=collection_name, query=question_vector, limit=4, with_payload=True ).points
    context = "\n\n---\n\n".join(
        f"""SOURCE FILE: {r.payload.get('file_name', 'unknown')}
        TYPE: {r.payload.get('file_type', 'unknown')}
CONTENT:
{r.payload.get('text', '')}
"""
        for r in results
        if r.payload.get('text') )

    return context



def search_docs(question: str):

    question_vector = encode(question)

    context = get_context(question_vector)

    return context