"""
MCP Tools for Document management.

Supports document creation with templates:
- Problem Statement
- Product Vision
- Technical Decision Record
- Sprint Retrospective

Tools:
- create_document: Create a document (with optional template)
- get_document: Get document content
- update_document: Update a document
- list_documents: List documents with filters
- search_documents: Search documents by keyword
"""

from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from mcp_server.server import mcp
from mcp_server.shared_services import get_document_service, serialize_response


@mcp.tool()
async def create_document(
    project_id: str,
    title: str,
    content: str = "",
    template_type: str | None = None,
) -> str:
    """Create a new document, optionally from a template.

    Use this tool when the user wants to:
    - Create project documentation
    - Start a document from a template
    - Write a Problem Statement, Product Vision, TDR, or Retrospective

    Available templates:
    - problem_statement: Problem Statement template
    - product_vision: Product Vision template
    - technical_decision: Technical Decision Record template
    - sprint_retrospective: Sprint Retrospective template

    If template_type is provided and content is empty, the document
    will be initialized with the template content.

    Args:
        project_id: The ID of the parent project (required)
        title: Document title (required)
        content: Document content in markdown (optional, uses template if empty)
        template_type: Template type to use (optional)

    Returns:
        JSON with created document details including its ID

    Example:
        create_document(
            project_id="proj_abc123",
            title="GraphQL vs REST Decision",
            template_type="technical_decision"
        )
    """
    async with get_document_service() as service:
        document = await service.create(
            DocumentCreate(
                project_id=project_id,
                title=title,
                content=content,
                template_type=template_type,
            )
        )
        return serialize_response(DocumentResponse.model_validate(document))


@mcp.tool()
async def get_document(document_id: str) -> str:
    """Get a document with its full content.

    Use this tool when the user wants to:
    - Read a document
    - View document content
    - Check what's in a specific document

    Args:
        document_id: The ID of the document to retrieve (required)

    Returns:
        JSON with document details including full content
    """
    async with get_document_service() as service:
        document = await service.get(document_id)
        return serialize_response(DocumentResponse.model_validate(document))


@mcp.tool()
async def update_document(
    document_id: str,
    title: str | None = None,
    content: str | None = None,
) -> str:
    """Update a document's title or content.

    Use this tool when the user wants to:
    - Edit document content
    - Update a document title
    - Fill in a template with actual content
    - Revise documentation

    Args:
        document_id: The ID of the document to update (required)
        title: New title (optional)
        content: New content in markdown (optional)

    Returns:
        JSON with updated document details
    """
    async with get_document_service() as service:
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content

        document = await service.update(document_id, DocumentUpdate(**update_data))
        return serialize_response(DocumentResponse.model_validate(document))


@mcp.tool()
async def list_documents(
    project_id: str | None = None,
    template_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """List documents with optional filters.

    Use this tool when the user wants to:
    - See all documents in a project
    - Filter documents by template type
    - Browse available documentation

    Args:
        project_id: Filter by project ID (optional)
        template_type: Filter by template type (optional)
        page: Page number, starting from 1 (default: 1)
        page_size: Number of documents per page (default: 50, max: 100)

    Returns:
        JSON with list of documents and pagination info
    """
    async with get_document_service() as service:
        result = await service.list(
            project_id=project_id,
            template_type=template_type,
            page=page,
            page_size=page_size,
        )
        return serialize_response(result)


@mcp.tool()
async def search_documents(keyword: str, project_id: str | None = None) -> str:
    """Search documents by keyword in title and content.

    Use this tool when the user wants to:
    - Find documents containing specific information
    - Search for documentation about a topic
    - Locate a document by partial name or content

    Args:
        keyword: Search term to look for in title and content (required)
        project_id: Optional filter by project ID

    Returns:
        JSON with list of matching documents
    """
    async with get_document_service() as service:
        result = await service.search(keyword=keyword, project_id=project_id)
        return serialize_response(result)
