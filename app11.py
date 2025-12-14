from fastapi import FastAPI
from sqlalchemy import create_engine, MetaData, Table, select
from fastapi.responses import JSONResponse

engine = create_engine("sqlite:///./flo_data.db", connect_args={"check_same_thread": False})
metadata = MetaData()
clients = Table("clients", metadata, autoload_with=engine)

app = FastAPI(
    title="Clients API",
    version="1.0.0",
    description="전체 clients 데이터를 JSON으로 반환합니다."
)


@app.get("/")
def root():
    return {"message": "FastAPI 서버 정상 동작 중"}


@app.get("/clients")
def read_all_clients(skip: int = 0, limit: int = 100):
    with engine.connect() as conn:
        query = select(clients).offset(skip).limit(limit)
        result = conn.execute(query)
        data = [dict(row._mapping) for row in result]
        return data
