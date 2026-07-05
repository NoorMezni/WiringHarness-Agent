import datetime
import uuid
import io
import sys
import hashlib
from dotenv import load_dotenv
import os
import json
import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from pathlib import Path
from openai import OpenAI

load_dotenv()
#############################################################################
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
collection_name = "Wiring_harness_collection"

if not qdrant.collection_exists(collection_name):
    qdrant.create_collection( collection_name=collection_name,        
                             vectors_config=VectorParams(size=1536, distance=Distance.COSINE), )

        #vectors_config=VectorParams(size=768, distance=Distance.COSINE), )

openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)
#############################################################################
# DRIVE
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
drive_service = build(
    "drive", "v3",
    credentials=service_account.Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/drive.readonly"] ))  

#############################################################################
converter = DocumentConverter()
chunker = HybridChunker()
SUPPORTED = {
    "pdf", "docx", "xlsx", "pptx", "epub", "md", "adoc", "tex", "html", "xhtml", "csv", "png", "jpeg", "tiff", "bmp", "webp",
    "wav", "mp3", "m4a", "aac", "ogg", "flac", "mp4", "avi", "mov","vtt", "xml", "json"}
TRACK_FILE = "processed_files.json"
#############################################################################
# EMBEDDING
#def encode(text):
    #return ollama.embeddings(model="nomic-embed-text", prompt=text)["embedding"]

def encode(text):
    response = openrouter_client.embeddings.create(
        model="openai/text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def build_embedding_text(c):
    title = c.get("title", "")
    text = c.get("text", "")
    return f"{title} {text}"

#############################################################################
# FILE TRACKING 
def load_registry():
    if not os.path.exists(TRACK_FILE):
        return {}
    with open(TRACK_FILE, "r") as f:
        return json.load(f)

def save_registry(data):
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f)

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read():
            h.update(chunk)
    return h.hexdigest()
#############################################################################
def download_from_drive(file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    temp_path = str(Path(__file__).resolve().parent / "documents" / file_name)
    with io.FileIO(temp_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return temp_path
################################################
def ingest_file(temp_path, file_name, processed):
    ext = os.path.splitext(file_name)[1][1:].lower()
    if ext not in SUPPORTED:
        print(f"Unsupported: {file_name}")
        return

    current_hash = file_hash(temp_path)
    if file_name in processed and processed[file_name] == current_hash:
        print(f"Already processed: {file_name}")
        return

    print(f"Processing: {file_name}")
    try:
        doc = converter.convert(temp_path).document
        chunks = []

        for chunk in chunker.chunk(doc):
            text = getattr(chunk, "text", str(chunk))
            headings = getattr(chunk, "headings", None)
            title = " > ".join(headings) if headings else file_name
            chunks.append({"text": text, "title": title})

        points = [
            PointStruct(
                id=uuid.uuid5(uuid.NAMESPACE_URL, f"{file_name}_{c['text']}"),
                vector=encode(build_embedding_text(c)), 
                payload={
                    "text": c["text"],
                    "title": c["title"],
                    "file_name": file_name,
                    "file_type": ext,
                    "ingestion_time": str(datetime.datetime.now()), } )
            for c in chunks  ]

        if points:
            qdrant.upsert(collection_name=collection_name, points=points)
        # Save hash
        processed[file_name] = current_hash
        os.remove(temp_path)
    except Exception as e:
        print(f"Error processing {file_name}: {e}")
#############################################################################
def run_single(file_name, file_id):
    # Called by n8n with a specific file
    processed = load_registry()
    temp_path = download_from_drive(file_id, file_name)
    ingest_file(temp_path, file_name, processed)
    save_registry(processed)

def run_batch():
    # Run manually to process everything in the Drive folder
    processed = load_registry()
    files = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute().get("files", [])

    for f in files:
        temp_path = download_from_drive(f["id"], f["name"])
        ingest_file(temp_path, f["name"], processed)
    save_registry(processed)
    print("Batch done")
#############################################################################
file_name = sys.argv[1] if len(sys.argv) > 1 else None
file_id   = sys.argv[2] if len(sys.argv) > 2 else None

if file_name and file_id:
    run_single(file_name, file_id)
else:
    run_batch()
