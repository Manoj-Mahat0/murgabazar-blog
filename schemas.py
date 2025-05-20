from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Auth
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):  # 👈 Add this
    email: EmailStr
    password: str
    
# Blog
class BlogBase(BaseModel):
    title: str
    content: Optional[str] = ""
    tags: Optional[str] = ""

class BlogResponse(BlogBase):
    id: int
    image: Optional[str]
    owner_id: int

    class Config:
        orm_mode = True
