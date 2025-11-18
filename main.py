import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import create_document, get_documents, db
from schemas import Document

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Elevator Docs API running"}

# Create/upload a document (metadata + file)
@app.post("/api/documents")
async def upload_document(
    brand: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # comma-separated
    file: UploadFile = File(...)
):
    # Validate file size via content-length header if available
    # Note: large files (e.g., 5GB) require client to support streaming upload
    stored_name = f"{ObjectId()}.{file.filename.split('.')[-1]}" if "." in file.filename else str(ObjectId())
    storage_path = os.path.join(STORAGE_DIR, stored_name)

    # Stream to disk in chunks
    try:
        with open(storage_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                f.write(chunk)
    finally:
        await file.close()

    size = os.path.getsize(storage_path)

    doc = Document(
        brand=brand,
        title=title,
        description=description,
        content_type=file.content_type,
        size=size,
        filename=stored_name,
        original_name=file.filename,
        path=storage_path,
        tags=[t.strip() for t in tags.split(',')] if tags else None,
    )

    inserted_id = create_document("document", doc)
    return {"id": inserted_id, "message": "Uploaded"}

class DocumentFilter(BaseModel):
    q: Optional[str] = None
    brand: Optional[str] = None

# List/search documents
@app.get("/api/documents")
async def list_documents(q: Optional[str] = None, brand: Optional[str] = None, limit: int = 100):
    filter_query = {}
    if brand:
        filter_query["brand"] = brand
    # Simple text filter on title/description/tags
    if q:
        filter_query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}}
        ]
    docs = get_documents("document", filter_query, limit)
    # Map IDs to strings and remove path for listing
    for d in docs:
        d["id"] = str(d.pop("_id"))
        d.pop("path", None)
    return {"items": docs}

# Download a file
@app.get("/api/documents/{doc_id}/download")
async def download_document(doc_id: str):
    from bson import ObjectId
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid document id")

    doc = db["document"].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    filename = doc.get("original_name") or doc.get("filename")
    media_type = doc.get("content_type") or "application/octet-stream"
    return FileResponse(path=file_path, filename=filename, media_type=media_type)

# Stream inline viewing (e.g., PDFs)
@app.get("/api/documents/{doc_id}/view")
async def view_document(doc_id: str):
    from bson import ObjectId
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid document id")

    doc = db["document"].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.get("path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    filename = doc.get("original_name") or doc.get("filename")
    media_type = doc.get("content_type") or "application/octet-stream"
    return FileResponse(path=file_path, filename=filename, media_type=media_type)

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        # Try to import database module
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
