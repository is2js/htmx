import json
import pathlib
from contextlib import asynccontextmanager
from typing import Optional, List, Union

from fastapi import FastAPI, Request, Header, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import Response

from database import engine, SessionLocal
import models
from schemas import Track

models.Base.metadata.create_all(bind=engine)

tracks_data = []


# lifespan for init data
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    # 1) [movie] dict -> sqlalchemy orm class
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
        print(f"[movie] {num_films} films already in DB.")

    # 2) [tracks] json -> dict -> pydantic schema model
    tracks_path = pathlib.Path() / 'data' / 'tracks.json'

    with open(tracks_path, 'r') as f:
        tracks = json.load(f)
        for track in tracks:
            tracks_data.append(Track(**track).model_dump())

    print(f"[tracks] {len(tracks_data)}개의 json 데이터 로드 in tracks_data\n - 예시: {tracks_data[0]}")

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


############
# movie
############

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


############
# tracks with json
############
@app.get("/tracks/", response_model=List[Track])
def tracks():
    return tracks_data


@app.get("/tracks/{track_id}", response_model=Union[Track, str])
def track(track_id: int, response: Response):
    track = None
    for t in tracks_data:
        if t['id'] == track_id:
            track = t
            break

    if track is None:
        response.status_code = 404
        return "Track not Found"

    return track


@app.post("/tracks/", response_model=Track, status_code=201)
def create_track(track: Track):
    track_dict = track.model_dump()
    # track_dict >> {'id': None, 'title': 'string', 'artist': 'string', 'duration': 0.0, 'last_play': datetime.datetime(2023, 12, 13, 2, 11, 29, 901000, tzinfo=TzInfo(UTC))}

    # 최고 id찾아서 id 부여
    track_dict['id'] = max(tracks_data, key=lambda x: x['id']).get('id') + 1

    # 전역변수에 append( session.add + commit )
    tracks_data.append(track_dict)

    return track_dict


@app.put("/tracks/{track_id}", response_model=Union[Track, str])
def track(track_id: int, updated_track: Track, response: Response):
    # 단일조회 로직 시작
    track = None
    for t in tracks_data:
        if t['id'] == track_id:
            track = t
            break

    if track is None:
        response.status_code = 404
        return "Track not Found"
    # 단일조회 로직 끝 (찾은 상태)

    # 수정 로직 시작
    # 1) schema를 dict로 바꾼뒤 .items()로 순회하며 업데이트한다. (생성시에는 dict로 바꿔서, id부여 + append)
    for key, value in updated_track.model_dump().items():
        # 2) id는 바꾸면 안되므로 continue 시키고 나머지를 재할당하여 업데이트한다.
        if key == 'id':
            continue
        track[key] = value

    # 3) 조회시 track = t로 참조했으므로, track을 업데이트하면 t도 업데이트된다.
    # => t는 dict list안의 dict이며, dict든 list든 참조형으로서 위치(주소)값만 넘기기 때문에, 그 위치의 값들은 같은 곳을 바라봐서
    #    같이 수정된다.

    return track


@app.delete("/tracks/{track_id}")
def track(track_id: int, response: Response):
    # 단일 <index> 조회 로직 시작
    track_index = None
    for idx, t in enumerate(tracks_data):
        if t['id'] == track_id:
            track_index = idx
            break

    if track_index is None:
        response.status_code = 404
        return "Track not Found"
    # 단일 <index> 조회 로직 끝 (찾은 상태)

    # 삭제 로직 시작
    del tracks_data[track_index]

    return Response(status_code=200)
