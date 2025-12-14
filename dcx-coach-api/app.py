from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker

# -----------------------------
# DB
# -----------------------------
DATABASE_URL = "sqlite:///./dcx_coach.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    mode = Column(String, nullable=False)  # contest | education | startup
    description = Column(Text, nullable=True)

    last_step = Column(Integer, default=0)

    step0 = Column(Text, nullable=True)
    step1 = Column(Text, nullable=True)
    step2 = Column(Text, nullable=True)
    step3 = Column(Text, nullable=True)
    step4 = Column(Text, nullable=True)
    step5 = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -----------------------------
# Schemas
# -----------------------------
Mode = str  # "contest" | "education" | "startup"

class CreateProjectRequest(BaseModel):
    title: str
    mode: str = Field(..., pattern="^(contest|education|startup)$")
    description: Optional[str] = None

class CreateProjectResponse(BaseModel):
    project_id: str

class ProjectListItem(BaseModel):
    project_id: str
    title: str
    mode: str
    last_step: int
    updated_at: datetime

class ProjectDetail(BaseModel):
    project_id: str
    title: str
    mode: str
    description: Optional[str] = None
    last_step: int
    steps: Dict[str, Optional[str]]

class UpdateProjectStepsRequest(BaseModel):
    last_step: Optional[int] = Field(default=None, ge=0, le=5)
    steps: Optional[Dict[str, Optional[str]]] = None

# -----------------------------
# App
# -----------------------------
app = FastAPI(
    title="DCX Planning Coach API",
    version="1.0.0",
    description="Save and load DCX-based planning projects and step outputs."
)

def now_utc():
    return datetime.utcnow()

def normalize_steps(steps: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {"step0","step1","step2","step3","step4","step5"}
    return {k: steps[k] for k in steps.keys() if k in allowed}

def get_steps_dict(p: Project) -> Dict[str, Optional[str]]:
    return {
        "step0": p.step0,
        "step1": p.step1,
        "step2": p.step2,
        "step3": p.step3,
        "step4": p.step4,
        "step5": p.step5,
    }

def gen_project_id() -> str:
    # 간단 UUID (표준 라이브러리)
    import uuid
    return str(uuid.uuid4())

@app.get("/")
def root():
    return {"message": "DCX Planning Coach API is running"}

@app.post("/projects", response_model=CreateProjectResponse)
def create_project(req: CreateProjectRequest):
    db = SessionLocal()
    try:
        project_id = gen_project_id()
        p = Project(
            project_id=project_id,
            title=req.title,
            mode=req.mode,
            description=req.description,
            last_step=0,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        db.add(p)
        db.commit()
        return {"project_id": project_id}
    finally:
        db.close()

@app.get("/projects", response_model=List[ProjectListItem])
def list_projects(
    query: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None, pattern="^(contest|education|startup)$"),
    limit: int = Query(default=50, ge=1, le=200),
):
    db = SessionLocal()
    try:
        q = db.query(Project)
        if query:
            like = f"%{query}%"
            q = q.filter(Project.title.like(like))
        if mode:
            q = q.filter(Project.mode == mode)
        q = q.order_by(Project.updated_at.desc()).limit(limit)
        rows = q.all()
        return [
            ProjectListItem(
                project_id=r.project_id,
                title=r.title,
                mode=r.mode,
                last_step=r.last_step,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
    finally:
        db.close()

@app.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str):
    db = SessionLocal()
    try:
        p = db.query(Project).filter(Project.project_id == project_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")
        return ProjectDetail(
            project_id=p.project_id,
            title=p.title,
            mode=p.mode,
            description=p.description,
            last_step=p.last_step,
            steps=get_steps_dict(p),
        )
    finally:
        db.close()

@app.patch("/projects/{project_id}")
def update_project_steps(project_id: str, req: UpdateProjectStepsRequest):
    db = SessionLocal()
    try:
        p = db.query(Project).filter(Project.project_id == project_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        if req.last_step is not None:
            p.last_step = req.last_step

        if req.steps:
            steps = normalize_steps(req.steps)
            for k, v in steps.items():
                setattr(p, k, v)

        p.updated_at = now_utc()
        db.commit()
        return {"status": "updated"}
    finally:
        db.close()
