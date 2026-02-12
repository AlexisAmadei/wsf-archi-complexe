"""
Document API endpoints.

Provides CRUD operations, template support, and search for documents.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import DBSession
from app.schemas.document import DocumentCreate, DocumentList, DocumentResponse, DocumentUpdate
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(data: DocumentCreate, db: DBSession) -> DocumentResponse:
    """
    Create a new document.
    
    If template_type is provided and content is empty, the document will be 
    initialized with the template content.
    """
    service = DocumentService(db)
    document = await service.create(data)
    return DocumentResponse.model_validate(document)


@router.get("/search", response_model=DocumentList)
async def search_documents(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search keyword"),
    project_id: str | None = Query(None, description="Filter by project ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> DocumentList:
    """Search documents by keyword in title and content."""
    service = DocumentService(db)
    return await service.search(keyword=q, project_id=project_id, page=page, page_size=page_size)


@router.get("", response_model=DocumentList)
async def list_documents(
    db: DBSession,
    project_id: str | None = Query(None, description="Filter by project ID"),
    template_type: str | None = Query(None, description="Filter by template type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> DocumentList:
    """List documents with optional filters and pagination."""
    service = DocumentService(db)
    return await service.list(
        project_id=project_id, template_type=template_type, page=page, page_size=page_size
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: DBSession) -> DocumentResponse:
    """Get a document by ID."""
    service = DocumentService(db)
    document = await service.get(document_id)
    return DocumentResponse.model_validate(document)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str, data: DocumentUpdate, db: DBSession
) -> DocumentResponse:
    """Update a document (partial update)."""
    service = DocumentService(db)
    document = await service.update(document_id, data)
    return DocumentResponse.model_validate(document)
