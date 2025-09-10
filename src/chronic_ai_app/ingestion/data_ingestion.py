import os
import pandas as pd
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_docling.loader import ExportType, DoclingLoader
from docling.chunking import HybridChunker
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from chronic_ai_app.ingestion.embeddings import get_embedding_model
from langchain_community.vectorstores.supabase import SupabaseVectorStore
from supabase.client import create_client


load_dotenv()
supbase_client = create_client(
    str(os.getenv("SUPABASE_URL")), str(os.getenv("SUPABASE_KEY"))
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

load_dotenv()
embedding = get_embedding_model()


def generate_datastore(file_path: str):
    """Load and chunk PDF documents from Docling and store embeddings in Chroma."""

    if embedding is None:
        print("Failed to initialize embedding model.")
        return

    print("Embedding model initialized.")

    vectorstore = None

    loader = DoclingLoader(
        file_path=file_path, export_type=ExportType.MARKDOWN, chunker=HybridChunker()
    )

    docs = loader.load()

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
        ],
    )

    splits = [split for doc in docs for split in splitter.split_text(doc.page_content)]
    splits = [Document(page_content=doc.page_content) for doc in splits]

    if vectorstore is None:
        try:
            vectorstore = SupabaseVectorStore.from_documents(
                documents=splits,
                embedding=embedding,
                client=supbase_client,
                table_name="documents",
                query_name="match_documents",
            )
            print("Documents stored in Supabase vector store.")
        except Exception as e:
            print(f"Error storing documents in Supabase: {e}")


def get_files_from_storage():
    """Retrieve files from the storage directory - SUPBASE BUCKET."""

    supabase = create_client(
        str(os.getenv("SUPABASE_URL")), str(os.getenv("SUPABASE_KEY"))
    )

    file_urls = []
    bucket_name = "diabetes-factsheets-pdfs"

    try:
        files = supabase.storage.from_(bucket_name).list(path="")
        logger.info(f"Retrieved {len(files)} from Supabase bucket {bucket_name}.")
    except Exception as e:
        logger.error(f"Error retrieving files from Supabase bucket: {e}")
        raise

    file_urls = [
        supabase.storage.from_(bucket_name).get_public_url(file["name"])
        for file in files
    ]

    logger.info(
        f"Retrieved {len(file_urls)} file URLs from Supabase bucket {bucket_name}."
    )
    return file_urls


if __name__ == "__main__":
    # data = pd.read_excel("src/chronic_ai_agent_app/data/raw/dataset_urls.xlsx", sheet_name="pdfs")

    urls = get_files_from_storage()

    for url in urls:
        generate_datastore(url)

    """ for url in data['Url']:
        print(f"Processing URL: {url}")
        generate_datastore(url) """

    print("All PDFs processed and stored in Supabase vector store.")
