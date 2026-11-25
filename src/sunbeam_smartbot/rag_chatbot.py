import os
import sys

from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq

from .paths import CHROMA_DIR, PROJECT_ROOT


# Keep unsupported Unicode characters in console output from crashing the CLI.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")


# =====================================================
# LOAD ENV
# =====================================================
load_dotenv(PROJECT_ROOT / ".env")

# =====================================================
# CONFIG
# =====================================================
CHROMA_DIR = str(CHROMA_DIR)
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# =====================================================
# EMBEDDINGS (Local ONNX compatible with existing collection)
# =====================================================
try:
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    class ChromaDefaultWrapper:
        def __init__(self):
            self.fn = DefaultEmbeddingFunction()
        def embed_documents(self, texts):
            return self.fn(texts)
        def embed_query(self, text):
            return self.fn([text])[0]
    embeddings = ChromaDefaultWrapper()
except Exception:
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

# =====================================================
# LOAD VECTOR DB
# =====================================================
vector_db = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings
)

# =====================================================
# RETRIEVER (MMR — TABLE SAFE)
# =====================================================
retriever = vector_db.as_retriever(
    search_type="mmr",
    search_kwargs={
        "k": 8,
        "fetch_k": 25
    }
)


# =====================================================
# LLM (GROQ)
# =====================================================
llm = ChatGroq(
    model=GROQ_MODEL,
    temperature=0.1
)

# =====================================================
# PROMPTS
# =====================================================
SYSTEM_PROMPT = """
You are an AI Assistant powered by Retrieval-Augmented Generation (RAG).

YOUR ROLE:
- Answer the user's question using ONLY the information provided in the retrieved context.
- Be clear, concise, professional, and user-friendly.
- Explain information in simple language so a non-technical user can understand.

STRICT RULES (MUST FOLLOW):
1. DO NOT hallucinate or assume any facts.
2. DO NOT add information that is NOT present in the retrieved context.
3. DO NOT change the topic or introduce unrelated information.
4. If the answer is NOT found in the context, respond EXACTLY:
   "I don’t have enough information to answer that based on the available data."
5. If the question is outside the domain of the data, respond EXACTLY:
   "This question is outside the scope of the available information."

ANSWER STYLE:
- Use complete sentences.
- Prefer bullet points for lists.
- If applicable, explain terms briefly.
- Be polite and helpful.
"""


USER_PROMPT = """
Answer the question using ONLY the context provided below.

CONTEXT:
{context}

QUESTION:
{question}

INSTRUCTIONS:
- Base your answer strictly on the context.
- If the context partially answers the question, answer only that part.
- Do not guess missing information.
"""


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ]
)

# =====================================================
# RAG FUNCTION
# =====================================================
def rag_answer(question: str) -> str:
    docs = retriever.invoke(question)

    if not docs:
        return "I don't have that information."

    context = "\n\n".join(doc.page_content for doc in docs)

    chain = prompt | llm | StrOutputParser()

    return chain.invoke({
        "context": context,
        "question": question
    })

# =====================================================
# CHAT LOOP
# =====================================================
def main() -> None:
    print("🤖 Sunbeam SmartBot (RAG)")
    print("Ask about Sunbeam, internships, batches, fees, courses, etc.")
    print("Type 'exit' to quit\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break

        answer = rag_answer(user_input)
        print("\nBot:", answer)
        print("-" * 60)


if __name__ == "__main__":
    main()
