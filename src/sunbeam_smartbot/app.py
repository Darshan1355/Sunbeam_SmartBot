import os
import shutil

from .paths import CHROMA_DIR, DOCUMENTS_DIR
from .scraper_util import ScraperManager

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader


# STEP 1: SCRAPE DATA → TXT FILES
print("🚀 Starting scraping process...")
try:
    manager = ScraperManager()
    manager.scrape_all_to_txt()
    manager.close()
    print("✅ All scraped data stored directly in TXT files")
except Exception as e:
    print(f"⚠️ Scraping notice: {e}. Proceeding with existing verified documents.")

# STEP 2: CONFIG
TEXT_FILES = [
    DOCUMENTS_DIR / "sunbeam_about.txt",
    DOCUMENTS_DIR / "sunbeam_internship.txt",
    DOCUMENTS_DIR / "sunbeam_courses.txt",
    DOCUMENTS_DIR / "sunbeam_cdac_courses.txt",
    DOCUMENTS_DIR / "sunbeam_contact_branches.txt",
]

# Remove old DB (avoid duplicate embeddings)
if os.path.exists(CHROMA_DIR):
    shutil.rmtree(CHROMA_DIR)
    print("🧹 Old Chroma DB removed")


# STEP 3: EMBEDDING MODEL (Local ONNX compatible)
print("📦 Loading embedding model...")
try:
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    class ChromaDefaultWrapper:
        def __init__(self):
            self.fn = DefaultEmbeddingFunction()
        def embed_documents(self, texts):
            return self.fn(texts)
        def embed_query(self, text):
            return self.fn([text])[0]
    embedding_model = ChromaDefaultWrapper()
except Exception:
    from langchain_huggingface import HuggingFaceEmbeddings
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


# STEP 4: LOAD TXT DOCUMENTS
documents = []

for file_path in TEXT_FILES:
    if os.path.exists(file_path):
        loader = TextLoader(file_path, encoding="utf-8")
        documents.extend(loader.load())

print(f"📄 Loaded {len(documents)} text documents")


# STEP 5: CHUNK TEXT
text_splitter = RecursiveCharacterTextSplitter(
    separators=[
        "\n----------------------------------------------------------------------------------------------------\n",
        "\n====================================================================================================\n",
        "\nSECTION: ",
        "\nTABLE: ",
        "\n\n",
        "\n",
        " ",
    ],
    chunk_size=700,
    chunk_overlap=80,
)


chunks = text_splitter.split_documents(documents)
print(f"🧩 Created {len(chunks)} chunks")


# STORE EMBEDDINGS IN CHROMA
print("💾 Storing embeddings into Chroma DB...")

vector_db = Chroma.from_documents(
    documents=chunks,
    embedding=embedding_model,
    persist_directory=str(CHROMA_DIR)
)

print("🎉 Embeddings stored successfully in Chroma DB")
print("🚀 FULL TXT → CHROMA PIPELINE COMPLETED")
