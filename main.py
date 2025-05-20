from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import shutil, os, traceback

from database import Base, engine
from models import User, Blog
from schemas import UserCreate, Token, BlogResponse
from dependencies import get_db, get_current_user
from auth import hash_password, verify_password, create_access_token
from fastapi.staticfiles import StaticFiles

# Init
app = FastAPI()
Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Custom error handler (for dev)
@app.exception_handler(Exception)
async def custom_exception_handler(request, exc):
    print("ERROR:", traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# ✅ Signup
@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(email=user.email, password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

# ✅ Login
@app.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# ✅ Create Blog
@app.post("/blogs/", response_model=BlogResponse)
def create_blog(
    title: str = Form(...),
    content: str = Form(""),
    tags: str = Form(""),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image_path = None
    if image:
        try:
            image_path = os.path.join(UPLOAD_DIR, image.filename)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    blog = Blog(title=title, content=content, tags=tags, image=image_path, owner_id=current_user.id)
    db.add(blog)
    db.commit()
    db.refresh(blog)
    return blog

# ✅ Get All Blogs
@app.get("/blogs/", response_model=list[BlogResponse])
def get_blogs(db: Session = Depends(get_db)):
    return db.query(Blog).all()

# ✅ Get Blog Image
@app.get("/images/{filename}")
def get_image(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)

# ✅ Delete Blog
@app.delete("/blogs/{id}")
def delete_blog(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    blog = db.query(Blog).filter(Blog.id == id, Blog.owner_id == current_user.id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found or unauthorized")
    db.delete(blog)
    db.commit()
    return {"message": "Blog deleted"}

# ✅ Update Blog
@app.put("/blogs/{id}", response_model=BlogResponse)
def update_blog(
    id: int,
    title: str = Form(None),
    content: str = Form(None),
    tags: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    blog = db.query(Blog).filter(Blog.id == id, Blog.owner_id == current_user.id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found or unauthorized")

    if title is not None:
        blog.title = title
    if content is not None:
        blog.content = content
    if tags is not None:
        blog.tags = tags
    if image:
        try:
            image_path = os.path.join(UPLOAD_DIR, image.filename)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            blog.image = image_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    db.commit()
    db.refresh(blog)
    return blog


@app.get("/blogs/all", response_model=list[BlogResponse])
def get_all_blogs_with_users(db: Session = Depends(get_db)):
    blogs = db.query(Blog).all()
    return blogs
# ✅ Get Blog by ID
@app.get("/blogs/{id}", response_model=BlogResponse)
def get_blog_by_id(id: int, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.id == id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return blog
