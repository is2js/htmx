from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Header, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import engine, SessionLocal
import models

models.Base.metadata.create_all(bind=engine)


# lifespan for init data
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    db = SessionLocal()
    num_films = db.query(models.Film).count()
    if num_films == 0:
        films = [
            {'name': 'Blade Runner', 'director': 'Ridley Scott'},
            {'name': 'Pull Fiction', 'director': 'Quentin Tarantino'},
            {'name': 'Mulholland Drive', 'director': 'David Lynch'},
            {'name': 'Jurassic Park', 'director': 'Steven Spielberg'},
            {'name': 'The Shining', 'director': 'Stanley Kubrick'},
            {'name': 'The Matrix', 'director': 'The Wachowskis'},
        ]

        for film in films:
            db.add(models.Film(**film))
        db.commit()

    else:
        print(f"{num_films} films already in DB.")

    yield

    # shutdown


app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/index/")
async def index(request: Request, response_class=HTMLResponse):
    context = {'request': request}
    return templates.TemplateResponse("index.html", context)


@app.get("/movie/", response_class=HTMLResponse)
async def movie(
        request: Request,
        hx_request: Optional[str] = Header(None),
        page: int = 1,
        db: Session = Depends(get_db),
):
    # films = db.query(models.Film).all()
    N = 2  # 페이지당 갯수
    OFFSET = (page - 1) * N

    films = db.query(models.Film).offset(OFFSET).limit(N).all()

    context = {'request': request, 'films': films, 'page': page}

    if hx_request:
        # 최초렌더: hx_request >> None / hx-get요청: hx_request >> true
        return templates.TemplateResponse('movie/partials/movie-table-tr.html', context)

    return templates.TemplateResponse("movie/index.html", context)
