"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

# Example schemas (you can keep or remove if not needed):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Elevator document schema (collection name: "document")
class Document(BaseModel):
    brand: str = Field(..., description="Elevator brand, e.g., Otis, KONE, Schindler")
    title: str = Field(..., description="Document title or reference")
    description: Optional[str] = Field(None, description="Optional description/notes")
    content_type: Optional[str] = Field(None, description="MIME type of the file, e.g., application/pdf")
    size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    filename: Optional[str] = Field(None, description="Stored filename on server")
    original_name: Optional[str] = Field(None, description="Original uploaded filename")
    path: Optional[str] = Field(None, description="Filesystem path where file is stored")
    tags: Optional[List[str]] = Field(default=None, description="Search tags")
