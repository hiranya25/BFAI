from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

from app.core.security import validate_api_key
from app.services.rag import list_documents, delete_document

router = APIRouter()

@router.get("/documents")
async def get_documents(api_key: str = Depends(validate_api_key)):
    """Returns a list of all indexed documents."""
    docs = list_documents()
    return {"documents": docs}

@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: str, api_key: str = Depends(validate_api_key)):
    """Deletes a document from the vector store and removes its associated files."""
    success = delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    return {"status": "success", "message": f"Document {doc_id} deleted."}
