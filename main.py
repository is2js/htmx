import json
import pathlib
from contextlib import asynccontextmanager
from typing import List, Optional, Union

from fastapi import Depends, FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

import models
from database import SessionLocal, engine
from schemas import Track

models.Base.metadata.create_all(bind=engine)

tracks_data = []


# lifespan for init data
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    db = SessionLocal()

    # 1) [movie] dict -> sqlalchemy orm class
    await init_movie_dict_to_db(db)

    # 2) [tracks] json -> dict -> pydantic schema model
    await init_tracks_json_to_list()

    # 3) [EmpDept] dict -> sqlalchemy orm class
    await init_emp_dept_dict_to_db(db)

    yield

    # shutdown


async def init_emp_dept_dict_to_db(db):
    num_departments = db.query(models.Department).count()
    if num_departments == 0:
        departments = [
            {"id": 1, "name": "Accounts"},
            {"id": 2, "name": "Sales"},
            {"id": 3, "name": "Management"},
        ]
        for department in departments:
            db.add(models.Department(**department))
        db.commit()
    else:
        print(f"[EmpDept] : {num_departments} departments already in DB.")
    num_employees = db.query(models.Employee).count()
    if num_employees == 0:
        accounts = db.query(models.Department).filter(models.Department.name == "Accounts").first()
        sales = db.query(models.Department).filter(models.Department.name == "Sales").first()
        management = db.query(models.Department).filter(models.Department.name == "Management").first()

        employees = [
            {
                'id': 1,
                'first_name': 'Jim',
                'surname': 'Halpert',
                'job_title': 'Sales Executive',
                'department_id': sales.id
            },
            {
                'id': 2,
                'first_name': 'Todd',
                'surname': 'Packer',
                'job_title': 'Sales Executive',
                'department_id': sales.id
            },
            {
                'id': 3,
                'first_name': 'Phyllis',
                'surname': 'Vance',
                'job_title': 'Regional Director of Sales',
                'department_id': sales.id
            },
            {
                'id': 4,
                'first_name': 'Angela',
                'surname': 'Martin',
                'job_title': 'Head of Accounting',
                'department_id': accounts.id
            },
            {
                'id': 5,
                'first_name': 'Oscar',
                'surname': 'Martinez',
                'job_title': 'Accountant',
                'department_id': accounts.id
            },
            {
                'id': 6,
                'first_name': 'Dwight',
                'surname': 'Schrute',
                'job_title': 'Assistant to the Regional Manager',
                'department_id': management.id
            },
            {
                'id': 7,
                'first_name': 'Michael',
                'surname': 'Scott',
                'job_title': 'Regional Manager',
                'department_id': management.id
            },
            {
                'id': 8,
                'first_name': 'Kevin',
                'surname': 'Malone',
                'job_title': 'Accountant',
                'department_id': accounts.id
            },
        ]

        for employee in employees:
            db.add(models.Employee(**employee))

        db.commit()

    else:
        print(f"[EmpDept] : {num_employees} employees already in DB.")


async def init_tracks_json_to_list():
    tracks_path = pathlib.Path() / 'data' / 'tracks.json'
    with open(tracks_path, 'r') as f:
        tracks = json.load(f)
        for track in tracks:
            tracks_data.append(Track(**track).model_dump())
    print(f"[tracks] {len(tracks_data)}개의 json 데이터 로드 in tracks_data\n - 예시: {tracks_data[0]}")


async def init_movie_dict_to_db(db):
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
    # track = None
    # for t in tracks_data:
    #     if t['id'] == track_id:
    #         track = t
    #         break
    track = next(
        (t for t in tracks_data if t['id'] == track_id), None
    )

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
    track = next(
        (t for t in tracks_data if t['id'] == track_id), None
    )

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
    # track_index = None
    # for idx, t in enumerate(tracks_data):
    #     if t['id'] == track_id:
    #         track_index = idx
    #         break
    track_index = next(
        (idx for idx, t in enumerate(tracks_data) if t['id'] == track_id), None
    )

    if track_index is None:
        response.status_code = 404
        return "Track not Found"
    # 단일 <index> 조회 로직 끝 (찾은 상태)

    # 삭제 로직 시작
    del tracks_data[track_index]

    return Response(status_code=200)


############
# EmpDept
############
@app.get("/employees/", response_class=HTMLResponse)
def employees(
        request: Request,
        db: Session = Depends(get_db),
):
    # results = db.query(models.Employee).all()
    results = db.execute(
        select(models.Employee, models.Department)
        .where(models.Employee.department_id == models.Department.id)
    ).all()
    # SELECT employees.id, employees.first_name, employees.surname, employees.job_title, employees.department_id, departments.id AS id_1, departments.name
    # FROM employees, departments
    # WHERE employees.department_id = departments.id
    # results >> [(<models.Employee object at 0x000002FD21CA90D0>, <models.Department object at 0x000002FD21CA9190>), (<models.Employee object at 0x000002FD21CA91C0>, <models.Department object at 0x000002FD21CA9190>), (<models.Employee object at 0x000002FD21CA9220>, <models.Department object at 0x000002FD21CA9190>), (<models.Employee object at 0x000002FD21CA9250>, <models.Department object at 0x000002FD21CA9280>), (<models.Employee object at 0x000002FD21CA92B0>, <models.Department object at 0x000002FD21CA9280>), (<models.Employee object at 0x000002FD21CA9310>, <models.Department object at 0x000002FD21CA9340>), (<models.Employee object at 0x000002FD21CA9370>, <models.Department object at 0x000002FD21CA9340>), (<models.Employee object at 0x000002FD21CA95E0>, <models.Department object at 0x000002FD21CA9280>)]
    # => scalars로 수행하면, 첫번째 class만 조회된다. tuple쌍의 장점이 사라짐.
    # ==> results >> [<models.Employee object at 0x0000022419ED9340>, <models.Employee object at 0x0000022419ED93D0>, <models.Employee object at 0x0000022419ED9430>, <models.Employee object at 0x0000022419ED9460>, <models.Employee object at 0x0000022419ED94C0>, <models.Employee object at 0x0000022419ED9730>, <models.Employee object at 0x0000022419ED9790>, <models.Employee object at 0x0000022419ED97F0>]

    # SQLModel과 달리, sqlalchemy의 execute결과인 Row객체 list는 2table형태의 json을 바로 만들 수 없다.
    # - **SQLModel사용시, 2테이블 select execute 후 `jsonable_encoder()`에 넣으면, tuple list -> 1) 2객체가 `묶여서 dict` + 2) `테이블명이 key`로 자동으로 들어간다**
    # - **하지만, `sqlalchemy`사용시, 2테이블 select execute의 결과는**
    #   - tuple모양의 `sqlalchemy.row.Row` object list가 나오는데, 2개의 table이 들어있는 순간 **`jsonable_encoder()에 안넣어진다.`**
    #   - **tuple처럼 반복문에서 a,b로 풀어서 각각을 jsonable_encoder()에 넣어도, `1) 테이블명이 key` + `2) 2개가 합친 dict`가 안나온다.**
    #       - 각각을 jsonable_encoder()에 넣어도, list안에 [ dict, dict ]형태로만 나와서, 전체가 [[dict, dict]]가 된다.
    #       - **하지만 우리가 필요한 형태는 [ dict(테이블명=dict, 테이블2명=dict)]형태로 `짝지어진 2개의 테이블이 1개의 dict안에 테이블명key안에` 들어가있길 원한다**

    # 2 table to dict for json
    employee_data = jsonable_encoder(({t1.__class__.__name__: t1, t2.__class__.__name__: t2}) for t1, t2 in results)
    # [
    #     {'Employee': {
    #           'id': 1,
    #           'surname': 'Halpert',
    #           'department_id': 2,
    #           'job_title': 'Sales Executive',
    #           'first_name': 'Jim'
    #           },
    #      'Department': {
    #           'id': 2,
    #           'name': 'Sales'}
    #           },
    # ]
    departments = set(e['Department']['name'] for e in employee_data)
    # departments >> {'Management', 'Accounts', 'Sales'}

    # <key와 함께 짝을 이룬 dict> list to json
    employees = json.dumps(employee_data)
    # employees >> [{"Employee": {"job_title": "Sales Executive", "id": 1, "first_name": "Jim", "surname": "Halpert", "department_id": 2}, "Department": {"id": 2, "name": "Sales"}}, {"Employee": {"job_title": "Sales Executive", "id": 2, "first_name": "Todd", "surname": "Packer", "department_id": 2}, "Department": {"id": 2, "name": "Sales"}}, {"Employee": {"job_title": "Regional Director of Sales", "id": 3, "first_name": "Phyllis", "surname": "Vance", "department_id": 2}, "Department": {"id": 2, "name": "Sales"}}, {"Employee": {"job_title": "Head of Accounting", "id": 4, "first_name": "Angela", "surname": "Martin", "department_id": 1}, "Department": {"id": 1, "name": "Accounts"}}, {"Employee": {"job_title": "Accountant", "id": 5, "first_name": "Oscar", "surname": "Martinez", "department_id": 1}, "Department": {"id": 1, "name": "Accounts"}}, {"Employee": {"job_title": "Assistant to the Regional Manager", "id": 6, "first_name": "Dwight", "surname": "Schrute", "department_id": 3}, "Department": {"id": 3, "name": "Management"}}, {"Employee": {"job_title": "Regional Manager", "id": 7, "first_name": "Michael", "surname": "Scott", "department_id": 3}, "Department": {"id": 3, "name": "Management"}}, {"Employee": {"job_title": "Accountant", "id": 8, "first_name": "Kevin", "surname": "Malone", "department_id": 1}, "Department": {"id": 1, "name": "Accounts"}}]

    context = {
        'request': request,
        'employees': employees,
        'departments': departments,
    }

    return templates.TemplateResponse("employees/index.html", context)
