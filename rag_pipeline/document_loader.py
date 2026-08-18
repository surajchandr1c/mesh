import os
from typing import List
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_and_split_documents(
    file_paths: List[str],
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Document]:
    """
    Load text/markdown documents from specified file paths and split into chunks.
    """
    documents: List[Document] = []

    for path in file_paths:
        if not os.path.exists(path):
            continue
        try:
            loader = TextLoader(path, encoding="utf-8")
            loaded_docs = loader.load()
            documents.extend(loaded_docs)
        except Exception as e:
            print(f"Error loading document {path}: {e}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    return text_splitter.split_documents(documents)


def split_text_content(
    text: str,
    source_name: str = "raw_input",
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Document]:
    """
    Split raw string content into LangChain document chunks with metadata.
    """
    doc = Document(page_content=text, metadata={"source": source_name})
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_documents([doc])
