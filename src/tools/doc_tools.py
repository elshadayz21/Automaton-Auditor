from pathlib import Path
from docling.document_converter import DocumentConverter
from langchain_text_splitters import RecursiveCharacterTextSplitter

def ingest_pdf(path: str, chunk_size: int = 2000, chunk_overlap: int = 200) -> list[str]:
    """
    Ingests a PDF document using docling and returns chunked text suitable for RAG-lite queries.
    
    Args:
        path: Path to the PDF file to ingest
        chunk_size: Maximum character count per chunk
        chunk_overlap: Overlap between consecutive chunks to maintain context
        
    Returns:
        List of text chunks extracted from the document
    """
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"PDF document not found at: {path}")
        
    try:
        # Convert document to markdown/text using Docling
        converter = DocumentConverter()
        result = converter.convert(file_path)
        
        # Get the markdown representation of the document
        raw_text = result.document.export_to_markdown()
        
        # Initialize LangChain text splitter for RAG-lite chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        
        # Split text into manageable chunks for the LLM
        chunks = text_splitter.split_text(raw_text)
        return chunks
        
    except Exception as e:
        raise RuntimeError(f"Failed to ingest and chunk PDF '{path}': {str(e)}")
