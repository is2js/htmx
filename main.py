from __future__ import annotations

import json
import pathlib
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import List, Optional, Union

from fastapi import Depends, FastAPI, Header, Request, UploadFile, Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse

from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

import models
from config import settings
from database import SessionLocal, engine
from decorators import login_required
from enums.messages import Message, MessageLevel
from exceptions.template_exceptions import BadRequestException
from middlewares.access_control import AccessControl
from schemas.picstargrams import UserSchema, CommentSchema, PostSchema, LikeSchema, TagSchema, PostTagSchema, \
    UpdatePostReq, PostCreateReq, UserCreateReq, UserLoginReq, Token
from schemas.tracks import Track
from templatefilters import feed_time
from utils import make_dir_and_file_path, get_updated_file_name_and_ext_by_uuid4, create_thumbnail
from utils.auth import verify_password
from utils.https import render, redirect

models.Base.metadata.create_all(bind=engine)

# 메모리 데이터 모음
tracks_data = []
# users, comments, posts = [], [], []
from crud.picstargrams import users, posts, comments, get_users, get_user, create_user, update_user, delete_user, \
    get_posts, get_post, create_post, update_post, delete_post, get_comment, get_comments, create_comment, \
    update_comment, delete_comment, likes, tags, post_tags, create_like, delete_like, get_tags, get_tag, create_tag, \
    update_tag, delete_tag, get_user_by_username, get_user_by_email

UPLOAD_DIR = pathlib.Path() / 'uploads'


# lifespan for init data
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    db = SessionLocal()

    # 1) [movie] dict -> sqlalchemy orm class
    await init_movie_dict_to_db(db)

    # 2) [tracks] json -> dict -> pydantic schema model
    await init_tracks_json_to_dict_list()

    # 3) [EmpDept] dict -> sqlalchemy orm class
    await init_emp_dept_dict_to_db(db)

    # 4) [Picstargram] dict -> pydantic schema model
    # global users, comments, posts
    users_, comments_, posts_, likes_, tags_, post_tags_ = await init_picstargram_json_to_list_per_pydantic_model()
    users.extend(users_)    
    comments.extend(comments_)
    posts.extend(posts_)
    likes.extend(likes_)
    tags.extend(tags_)
    post_tags.extend(post_tags_)

    yield

    # shutdown


async def init_picstargram_json_to_list_per_pydantic_model():
    """
    json을 도메인(user, post, comment별로 pydantic model list 3개로 나누어 받지만,
    추후, pydantic_model.model_dumps() -> sqlalchemy model(** )로 넣어서 만들면 된다.
    => 왜 dict list 3개가 아니라 pydantic model list 3개로 받냐면
       관계pydantic model을 가지기 위해서이다.
    ===> 추후, 관계 pydantic model을 -> sqlalchemy Model로 변경해줘야한다.
    """
    # picstargram_path = pathlib.Path() / 'data' / 'picstargram.json'
    picstargram_path = pathlib.Path() / 'data' / 'picstargram2.json'

    with open(picstargram_path, 'r', encoding='utf-8') as f:
        picstargram = json.load(f)
        # 단순 순회하며 처음부터 append하는 것은 list comp로 처리한다.
        # + list를 기대하고 dict를 꺼낼 땐 get(, [])로 처리하면 된다.

        users = [UserSchema(**user) for user in picstargram.get("users", [])]

        ## 관계Schema에 집어넣을 땐, next(, None) + pk==fk를 비교하고, 그에 맞는 Schema객체를 넣어준다.
        # M:1관계 - next(, None)으로 1개만 찾기
        # comments = [CommentSchema(**user) for user in picstargram.get("comments", [])]
        comments = [
            CommentSchema(
                **comment,
                # user=next((user for user in users if user.id == comment["user_id"]), None)
            )
            for comment in picstargram.get("comments", [])
        ]

        # M:1(user), 1:M(comments)-list comp로 여러개 찾기
        # posts = [PostSchema(**user) for user in picstargram.get("posts", [])]
        # ==> 1:M관계를 미리채워놓으면, M:1관계 comment(M)- posts(1)이 미리 채워져 있는 경우, dump시 무한 반복된다.
        #     => fk가 주어져있으면 미리 채워놓지 말고, crud에서 채우자.
        posts = [
            PostSchema(
                **post,
                # user=next((user for user in users if user.id == post["user_id"]), None),
                # comments=[comment for comment in comments if comment.post_id == post["id"]]
            )
            for post in picstargram.get("posts", [])
        ]

        # 1:M 관계 2개
        # for user in users:
        # user.posts = [post for post in posts if post.user_id == user.id]
        # user.comments = [comment for comment in comments if comment.user_id == user.id]

    # 다대다 추가
    likes = [LikeSchema(**like) for like in picstargram.get("likes", [])]
    tags = [TagSchema(**tag) for tag in picstargram.get("tags", [])]
    post_tags = [PostTagSchema(**tag) for tag in picstargram.get("post_tags", [])]

    print(
        f"[Picstargram] users-{len(users)}개, comments-{len(comments)}개, posts-{len(posts)}개, likes-{len(likes)}개, tags-{len(tags)}개, post_tags-{len(post_tags)}개"
        f"의 json 데이터, 각 list에 load")
    return users, comments, posts, likes, tags, post_tags


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


async def init_tracks_json_to_dict_list():
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


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
)


@app.exception_handler(RequestValidationError)
async def pydantic_422_exception_handler(request: Request, exc: RequestValidationError):
    """
    custom middleware에서 안잡히는 pydantic 422 입력에러 -> raise customerror -> middleware
    참고: https://stackoverflow.com/questions/58642528/displaying-of-fastapi-validation-errors-to-end-users
    """
    # return JSONResponse(
    #     status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #     content=jsonable_encoder({"detail": exc.errors(), "Error": "Name field is missing"}),
    # )
    # reformatted_message = defaultdict(list)
    reformatted_message = defaultdict(str)
    for pydantic_error in exc.errors():
        loc, msg = pydantic_error["loc"], pydantic_error["msg"]
        filtered_loc = loc[1:] if loc[0] in ("body", "query", "path") else loc
        field_string = ".".join(filtered_loc)  # nested fields with dot-notation
        # reformatted_message[field_string].append('<li>' + msg + '</li>')
        reformatted_message[field_string] += ('<li>' + msg + '</li>')
    # {'email': ['value is not a valid email address: The part after the @-sign contains invalid characters: "\\".']})
    # {'email': '<li>value is not a valid email address: The part after the @-sign contains invalid characters: "\\".</li'})

    raise BadRequestException(f'''
{", ".join(reformatted_message.keys())} 입력 에러(422)가 발생했습니다. 아래사항을 살펴주세요.<br/>
{"".join(reformatted_message.values())}
''')


origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(AccessControl)
app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

# static_directory = pathlib.Path(__file__).resolve().parent / 'static'
app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/uploads', StaticFiles(directory='uploads'), name='uploads')

# template filter 추가
templates.env.filters['feed_time'] = feed_time


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


@app.get("/test", )
@login_required
async def test(
        request: Request,
        # response: Response,
):
    # context = {'request': request}

    # messages = [
    #     Message.SUCCESS.write("새로고침", level=MessageLevel.SUCCESS),
    #     Message.CREATE.write("post", level=MessageLevel.INFO),
    #     Message.DELETE.write("post", level=MessageLevel.ERROR)
    # ]

    # return render(request, context=context, status_code=status.HTTP_204_NO_CONTENT,
    # return render(request, status_code=status.HTTP_204_NO_CONTENT,
    return render(request, template_name="picstargram/_empty.html", status_code=200,
                  # hx_trigger="postsChanged",
                  hx_trigger=["postsChanged"],
                  # messages=messages
                  messages=Message.SUCCESS.write("새로고침", level=MessageLevel.SUCCESS),
                  )
    response.status_code = status.HTTP_204_NO_CONTENT
    response.headers["HX-Trigger"] = json.dumps({
        "postsChanged": None,
        # "showMessage": Message.CREATE.write("포스트", level=MessageLevel.INFO)['text'],
        "messages": messages
    })

    return response

    # return templates.TemplateResponse("picstargram/post/partials/create_form.html", context)


@app.post("/test/post", )
async def test_post(
        request: Request,
        response: Response,
        # body: bytes = Body(...),
        # content: str = Form(...),
        # tags: str = Form(...),
        post_create_req: PostCreateReq = Depends(PostCreateReq.as_form),
        # post_create_req: PostCreateReq,
        file: Union[UploadFile, None] = None
):
    # as_form 반영 전 -> 파라미터에서 따로 받을 수 있음.
    # print(f"file  >> {file}")
    # file  >> <starlette.datastructures.UploadFile object at 0x0000018A11E84C40>
    # post_create_req  >> content='a' tags=[TagCreateReq(name='a'), TagCreateReq(name='b'), TagCreateReq(name='c')]

    # as_form 반영 후 -> post_creat_req에서 필드로서 받음.

    # print(f"content >> {content}")
    # print(f"tags >> {tags}")
    # body >> b'file=&body=asdf&tags=%5B%7B%22value%22%3A%22a%22%7D%2C%7B%22value%22%3A%22b%22%7D%2C%7B%22value%22%3A%22c%22%7D%5D'
    context = {'request': request}
    # print(f"tags >> {tags}")
    print(f"post_create_req  >> {post_create_req}")

    # post_create_req >> content='a' tags=[TagCreateReq(name='a'), TagCreateReq(name='b'), TagCreateReq(name='c')]
    # body >> b'file=&body=sadf&tags=%5B%7B%22name%22%3A%22a%22%7D%2C%7B%22name%22%3A%22b%22%7D%2C%7B%22name%22%3A%22c%22%7D%5D'
    # body >> b'file=&body=asdafas&tags=%5Bobject+Object%5D%2C%5Bobject+Object%5D%2C%5Bobject+Object%5D'

    # body >> {'file': [], 'body': 'a', 'tags': '[object Object],[object Object],[object Object],[object Object]'}
    # tags = body['tags']
    # print(f"json.loads(tags) >> {json.loads(tags)}")
    # json.loads(tags) >> [{'name': 'a', 'value': 'a'}, {'name': 'b', 'value': 'b'}, {'name': 'c', 'value': 'c'}]

    # json.loads(tags) >> [{'name': 'a', 'value': 'a'}, {'name': 'b', 'value': 'b'}, {'name': 'c', 'value': 'c'}]

    # print(f"post_create_req >> {post_create_req}")

    # originalInputValueFormat: valuesArr => JSON.stringify(valuesArr.map(item => { return {name: item.value}})),
    # body >> {'file': [], 'body': 'ㅁㄴ', 'tags': '[{"name":"a"},{"name":"b"},{"name":"c"}]'}

    return templates.TemplateResponse("picstargram/post/partials/create_form.html", context)


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


############
# fileupload
############

@app.get('/upload_file')
async def upload_file(request: Request):
    context = {'request': request}
    return templates.TemplateResponse("upload_file/index.html", context)


@app.post('/upload_file')
async def create_upload_file(file_upload: Union[UploadFile, None] = None):
    # UploadFile의 파라미터명 => input[type="file"]의 name과 일치해야한다!!!

    # 파일이 없는 경우 예외처리
    if not file_upload:
        return {'message': 'No file sent'}

    data = await file_upload.read()

    save_to = UPLOAD_DIR / file_upload.filename
    with open(save_to, 'wb') as f:
        f.write(data)

    return {'filename': file_upload.filename}


@app.post('/upload_files')
async def create_upload_files(file_uploads: list[UploadFile]):
    # UploadFile의 파라미터명 => input[type="file"]의 name과 일치해야한다!!!

    # 파일이 없는 경우 예외처리
    if not file_uploads:
        return {'message': 'No file sent'}

    # for문 추가 for multiple files(file_uploadssss)
    for file_upload in file_uploads:
        data = await file_upload.read()

        save_to = UPLOAD_DIR / file_upload.filename
        with open(save_to, 'wb') as f:
            f.write(data)

    # list comp로 변경 for multiple files
    return {'filenames': [file_upload.filename for file_upload in file_uploads]}


############
# hx fileupload with path parameter(directory name)
############

@app.post('/hx-upload-file/{directory_name}')
@app.post('/hx-upload-file/')
async def hx_upload_file(
        request: Request,
        directory_name: str = 'test',
        file_upload: Union[UploadFile, None] = None
):
    # UploadFile의 파라미터명 => input[type="file"]의 name과 일치해야한다!!!

    # 파일이 없는 경우 예외처리
    if not file_upload:
        # return {'message': 'No file sent'}
        context = {'request': request, 'error_message': '파일이 첨부되지 않았습니다.'}
        return templates.TemplateResponse("upload_file/partials/upload-form.html", context)

    mime_type = file_upload.content_type  # mime_type >> image/png, image/gif, image/jpeg, image/jpeg, image/bmp, image/x-icon

    # 업로드를 이미지로 제한
    if not mime_type in ['image/png', 'image/gif', 'image/jpeg', 'image/bmp', 'image/x-icon']:
        # return {'message': 'File is not image'}
        context = {'request': request, 'error_message': '이미지 파일만 업로드 가능합니다.'}
        return templates.TemplateResponse("upload_file/partials/upload-form.html", context)

    # 업로드 용량을 2MB로 제한
    if file_upload.size > 2048000:
        # return {'message': 'File is too large(plz below 2MB)'}
        context = {'request': request, 'error_message': '2MB 이하의 파일만 업로드 가능합니다.'}
        return templates.TemplateResponse("upload_file/partials/upload-form.html", context)

    data = await file_upload.read()

    # save_to = UPLOAD_DIR / file_upload.filename

    # file_path = make_dir_and_file_path('test', UPLOAD_DIR=UPLOAD_DIR)
    file_path = make_dir_and_file_path(directory_name=directory_name, UPLOAD_DIR=UPLOAD_DIR)
    file_name, file_ext = get_updated_file_name_and_ext_by_uuid4(file_upload)
    # save_to = file_path / (file_name + file_ext)
    # file_name = get_updated_file_name_by_uuid4(file_upload)
    save_to = file_path / file_name

    # image인 경우, PIL로 열어서 resize하고 저장한다.
    if mime_type.startswith('image/'):
        has_thumbnail = create_thumbnail(data, file_path, file_name, mime_type)

    with open(save_to, 'wb') as f:
        f.write(data)

    # TODO: db에 저장
    # 파일 저장 후, db 개통 전, [일회성 파일]로서 url만들어 view에서 확인하기
    # image_url = request.url_for('static', path=save_to) #  'WindowsPath' object has no attribute 'lstrip'
    # -> 'uploads'가 포함되었지만 test로 넣어본 save_to -> WindowPath객체로서 안들어감 #  'WindowsPath' object has no attribute 'lstrip'
    # -> save_to는 file system의 경로 <-> upload(static)폴더 + path= 디렉토리 + 파일명.확장자 경로가 다름
    image_url = request.url_for('uploads', path=directory_name + '/' + file_name) if not has_thumbnail \
        else request.url_for('uploads', path=directory_name + '/' + file_name + '-thumbnail')
    # image_url >> http://127.0.0.1:8000/uploads/test/f15db93682eb40d5a1c9828a8afac2a6.png

    # return {'filename': file_upload.filename}
    # context = {'request': request, 'image_url': image_url}
    context = {'request': request, 'image_url': image_url, 'mime_type': mime_type}

    return templates.TemplateResponse("upload_file/partials/upload-form.html", context)


############
# picstargram
############
############
# picstargram users
############

@app.get("/users/", response_model=List[UserSchema])
async def pic_get_users(request: Request):
    users = get_users(with_posts=True, with_comments=True)

    return users


@app.get("/users/{user_id}", response_model=Union[UserSchema, str])
async def pic_get_user(
        request: Request,
        user_id: int,
        response: Response,
):
    user = get_user(user_id, with_posts=True, with_comments=True)

    if user is None:
        response.status_code = 404
        return f"User(id={user_id}) 정보가 없습니다."

    return user


@app.post("/users", response_model=Union[UserSchema, str], status_code=201)
async def pic_create_user(
        request: Request,
        user_schema: UserSchema,
        response: Response,
):
    try:
        user = create_user(user_schema)

        return user

    except Exception as e:
        response.status_code = 400
        return f"User 생성에 실패했습니다.: {e}"


@app.put("/users/{user_id}", response_model=Union[UserSchema, str])
async def pic_update_user(
        request: Request,
        user_id: int,
        user_schema: UserSchema,
        response: Response,
):
    try:
        user = update_user(user_id, user_schema)
        return user

    except Exception as e:
        response.status_code = 400
        return f"User 수정에 실패했습니다.: {e}"


@app.delete("/users/{user_id}", )
async def pic_delete_user(
        request: Request,
        user_id: int,
        response: Response,
):
    try:
        delete_user(user_id)
        return "User 삭제에 성공했습니다."
    except Exception as e:
        response.status_code = 400
        return f"User 삭제에 실패했습니다.: {e}"


############
# picstargram posts
############

@app.get("/posts/", response_model=List[PostSchema])
async def pic_get_posts(request: Request):
    # posts = get_posts(with_user=True, with_comments=True)
    posts = get_posts(with_user=True, with_comments=True, with_likes=True, with_tags=True)
    return posts


@app.get("/posts/{post_id}", response_model=Union[PostSchema, str])
async def pic_get_post(
        request: Request,
        post_id: int,
        response: Response,
        hx_request: Optional[str] = Header(None)
):
    post = get_post(post_id, with_user=True, with_comments=True, with_likes=True, with_tags=True)

    # edit_form 취소시 개별조회 post를, html과 함께  반환
    if hx_request:
        context = {
            'request': request,
            'post': post,
        }
        return templates.TemplateResponse("picstargram/post/partials/post.html", context)

    if post is None:
        response.status_code = 404
        return "Post 정보가 없습니다."

    return post


@app.post("/posts", response_model=Union[PostSchema, str], status_code=201)
async def pic_create_post(
        request: Request,
        post_schema: PostSchema,
        response: Response,
):
    try:
        post = create_post(post_schema)
        return post

    except Exception as e:
        response.status_code = 400
        return f"Post 생성에 실패했습니다.: {e}"


@app.post("/posts", response_model=Union[PostSchema, str], status_code=201)
async def pic_create_post(
        request: Request,
        post_schema: PostSchema,
        response: Response,
):
    try:
        post = create_post(post_schema)
        return post

    except Exception as e:
        response.status_code = 400
        return f"Post 생성에 실패했습니다.: {e}"


@app.put("/posts/{post_id}", response_model=Union[PostSchema, str])
async def pic_update_post(
        request: Request,
        post_id: int,
        response: Response,
        updated_post_req: UpdatePostReq,  # hx-exc="json-enc"로 오는 form
        # data: dict = Depends(FormTo(UpdatePostReq)), # 순수 form
        hx_request: Optional[str] = Header(None)
):
    data = updated_post_req.model_dump()

    try:
        update_post(post_id, data)
    except Exception as e:
        response.status_code = 400
        return f"Post 수정에 실패했습니다.: {e}"

    post = get_post(post_id, with_user=True, with_comments=True, with_likes=True, with_tags=True)

    if hx_request:
        context = {
            'request': request,
            'post': post,
        }
        # return templates.TemplateResponse("picstargram/post/partials/post.html", context)
        return render(
            request,
            template_name="picstargram/post/partials/post.html",
            context=context,
            # messages=[Message.UPDATE.write("post")],
            oobs=[
                ('picstargram/_toasts.html', dict(messages=[Message.UPDATE.write("post")])),
            ]
        )

    return post


@app.get("/posts/{post_id}/edit_form/", response_class=HTMLResponse)
async def pic_hx_get_edit_form(
        request: Request,
        post_id: int,
        response: Response,
):
    post = get_post(post_id, with_user=True)

    context = {
        'request': request,
        'post': post,
    }

    return templates.TemplateResponse("picstargram/post/partials/edit_form.html", context)


@app.delete("/posts/{post_id}", )
async def pic_delete_post(
        request: Request,
        post_id: int,
        response: Response,
        hx_request: Optional[str] = Header(None)
):
    try:
        delete_post(post_id)
    except Exception as e:
        response.status_code = 400
        return f"Post 삭제에 실패했습니다.: {e}"

    # post 삭제시 빈 html를 반환하여 삭제 처리
    if hx_request:
        context = {
            'request': request
        }
        return render(request, context=context, messages=[Message.DELETE.write("post", MessageLevel.ERROR)])
        # return templates.TemplateResponse("picstargram/_empty.html", context)

    return "Post 삭제에 성공했습니다."


############
# picstargram comments
############
@app.get("/comments/{comment_id}", response_model=Union[CommentSchema, str])
async def pic_get_comment(
        request: Request,
        comment_id: int,
        response: Response,
):
    comment = get_comment(comment_id, with_user=True)

    if comment is None:
        response.status_code = 404
        return "Comment 정보가 없습니다."

    return comment


@app.get("posts/{post_id}/comments", response_model=List[CommentSchema])
async def pic_get_comments(
        request: Request,
        post_id: int,
        response: Response,
):
    comments = get_comments(post_id, with_user=True)

    return comments


@app.post("/comments", response_model=Union[CommentSchema, str], status_code=201)
async def pic_create_comment(
        request: Request,
        comment_schema: CommentSchema,
        response: Response,
):
    try:
        comment = create_comment(comment_schema)
        return comment

    except Exception as e:
        response.status_code = 400
        return f"Comment 생성에 실패했습니다.: {e}"


@app.put("/comments/{comment_id}", response_model=Union[CommentSchema, str])
async def pic_update_comment(
        request: Request,
        comment_id: int,
        comment_schema: CommentSchema,
        response: Response,
):
    try:
        comment = update_comment(comment_id, comment_schema)
        return comment

    except Exception as e:
        response.status_code = 400
        return f"Comment 수정에 실패했습니다.: {e}"


@app.delete("/comments/{comment_id}", )
async def pic_delete_comment(
        request: Request,
        comment_id: int,
        response: Response,
):
    try:
        delete_comment(comment_id)
        return "Comment 삭제에 성공했습니다."
    except Exception as e:
        response.status_code = 400
        return f"Comment 삭제에 실패했습니다.: {e}"


############
# picstargram like
############
@app.post("/like", response_model=Union[LikeSchema, str], status_code=201)
async def pic_create_like(
        request: Request,
        like_schema: LikeSchema,
        response: Response,
):
    try:
        like = create_like(like_schema)
        return like

    except Exception as e:
        response.status_code = 400
        return f"like 생성에 실패했습니다.: {e}"


# TODO: 나중에 로그인 + db 구현후 path param으로 옮겨주기
# @app.post("/posts/{post_id}/likes", response_model=Union[LikeSchema, str], status_code=201)
@app.post("/posts/likes", response_model=Union[LikeSchema, str], status_code=201)
async def pic_create_or_delete_like(
        request: Request,
        # post_id: int, # TODO: db 구현 후 1) post_id : path param + 2) user_id : request.user...
        like_schema: LikeSchema,
        response: Response,
):
    # 현재 post에서 실질중간테입르 likes를 many로 불러온다. 이 때, 반대편one인 user가 포함되어있어서, 결국엔 user list에 접근가능해진다.
    # -> 현재) 특정 post_id -현재의 나 like_schema.user_id
    # -> TODO: 추후) 특정 post_id(path_param) +  post.likes.add( request.user객체-현재의나 ) -> schema 없어도 됨.
    post = get_post(
        like_schema.post_id,
        with_user=True,  # 작성자 <-> 현재의 나 비교
        with_likes=True
    )

    # 1) 일단 좋아요 누른사람(like_schema.user_id)이 작성자(post.user.id)면, pass한다.
    if (author_id := post.user.id) == like_schema.user_id:
        raise Exception(f"자신(id={author_id})의 post(id={post.id})에는 좋아요를 누를 수 없습니다.")

    try:
        # 2) post.likes의 many데이터마다 박혀있는 user들을 list안에  좋아요누른사람의  포함여부(in)를 확인하고
        # -> 포함시 delete / 미포함시 create 작동을 하면 된다.
        if like_schema.user_id in [like.user.id for like in post.likes]:
            delete_like(like_schema)
            return f"이미 좋아요를 누른 게시물이어서, 좋아요를 제거합니다."

        else:
            create_like(like_schema)
            return f"현재 게시물에 좋아요를 눌렀습니다."

    except Exception as e:
        response.status_code = 400
        return f"좋아요를 누른 것에 실패했습니다.: {e}"


############
# picstargram tags
############
@app.get("/tags/", response_model=List[TagSchema])
async def pic_get_tags(request: Request):
    tags = get_tags(with_posts=True)

    return tags


@app.get("/tags/{tag_id}", response_model=Union[TagSchema, str])
async def pic_get_tag(
        request: Request,
        tag_id: int,
        response: Response,
):
    tag = get_tag(tag_id, with_posts=True)

    if tag is None:
        response.status_code = 404
        return f"Tag(id={tag_id}) 정보가 없습니다."

    return tag


@app.post("/tags", response_model=Union[TagSchema, str], status_code=201)
async def pic_create_tag(
        request: Request,
        tag_schema: TagSchema,
        response: Response,
):
    try:
        tag = create_tag(tag_schema)
        return tag

    except Exception as e:
        response.status_code = 400
        return f"Tag 생성에 실패했습니다.: {e}"


@app.put("/tags/{tag_id}", response_model=Union[TagSchema, str])
async def pic_update_tag(
        request: Request,
        tag_id: int,
        tag_schema: TagSchema,
        response: Response,
):
    try:
        tag = update_tag(tag_id, tag_schema)
        return tag

    except Exception as e:
        response.status_code = 400
        return f"Tag 수정에 실패했습니다.: {e}"


@app.delete("/tags/{tag_id}", )
async def pic_delete_tag(
        request: Request,
        tag_id: int,
        response: Response,
):
    try:
        delete_tag(tag_id)
        return "Tag 삭제에 성공했습니다."
    except Exception as e:
        response.status_code = 400
        return f"Tag 삭제에 실패했습니다.: {e}"


############
# picstargram templates
############
@app.get("/picstargram/", response_class=HTMLResponse)
async def pic_index(
        request: Request,
        # hx_request: Optional[str] = Header(None),
):
    posts = get_posts(with_user=True, with_tags=True, with_likes=True, with_comments=True)

    context = {
        'request': request,
        'posts': posts,
    }
    # return templates.TemplateResponse("picstargram/home/index.html", context)
    return render(request, "picstargram/home/index.html", context)


@app.get("/picstargram/posts/show", response_class=HTMLResponse)
async def pic_hx_show_posts(
        request: Request,
        hx_request: Optional[str] = Header(None),
):
    posts = get_posts(with_user=True, with_tags=True, with_likes=True, with_comments=True)

    context = {
        'request': request,
        'posts': posts,
    }
    return templates.TemplateResponse("picstargram/post/partials/posts.html", context)


# @app.get("/picstargram/form/posts/create", response_class=HTMLResponse)
# async def pic_hx_form_post_create(
#         request: Request,
#         hx_request: Optional[str] = Header(None),
# ):
#     context = {
#         'request': request,
#     }
#     return templates.TemplateResponse("picstargram/post/partials/create_form.html", context)

# @app.get("/picstargram/form/{form_name}", response_class=HTMLResponse)
@app.get("/picstargram/form", response_class=HTMLResponse)
async def pic_hx_form(
        request: Request,
        next_url: str = Query(None, alias='next')
):
    # htmx modal body반환인데, 내부 ?next=를 넘겨서, 로그인 form에서 next를 추출할 수 있게 한다
    request.query_params.__setattr__('next', next_url)
    context = {
        'request': request,
    }

    qp = request.query_params
    # qp  >> post-create=

    # Post
    if any(name in qp for name in ['post-create', 'post_create']):
        return templates.TemplateResponse("picstargram/post/partials/create_form.html", context)
    # Login or Register
    elif any(name in qp for name in ['user-register', 'user_register']):
        return templates.TemplateResponse("picstargram/user/partials/register_form.html", context)
    elif any(name in qp for name in ['user-login', 'user_login']):
        return templates.TemplateResponse("picstargram/user/partials/login_form.html", context)

    elif any(name in qp for name in ['user-login-or-register', 'user_login_or_register']):
        return templates.TemplateResponse("picstargram/user/partials/login_or_register_form.html", context)
    elif any(name in qp for name in ['user-login-body', 'user_login_body']):
        return templates.TemplateResponse("picstargram/user/partials/login_or_register_form_login_part.html", context)
    elif any(name in qp for name in ['user-register-body', 'user_register_body']):
        return templates.TemplateResponse("picstargram/user/partials/login_or_register_form_register_part.html",
                                          context)

    # User me
    elif any(name in qp for name in ['me-more', 'me_more']):
        return templates.TemplateResponse("picstargram/user/partials/me_more.html", context)
    elif any(name in qp for name in ['me-edit', 'me_edit']):
        # context.update(user=request.state.user)
        # return templates.TemplateResponse("picstargram/user/partials/me_edit_form.html", context)
        return render(request, "picstargram/user/partials/me_edit_form.html", context)

    else:
        return '준비되지 않은 modal입니다.'


@app.post("/picstargram/posts/new")
async def pic_new_post(
        request: Request,
        response: Response,
        post_create_req=Depends(PostCreateReq.as_form),
        file: Union[UploadFile, None] = None
):
    try:
        # 1) form데이터는 crud하기 전에 dict로 만들어야한다.
        data = post_create_req.model_dump()

        # 임시 user TODO: 로그인 구현시 현재 사용자가 들어와야함.
        data.update({'user_id': 1})

        # 2) file필드는 따로 처리한다. but req schema에는 입력X 처리후 dump된 dict에 반영할 준비를 한다.
        if not file:
            # post_create_req.image_url = None  => schema에 없는 필드는 동적으로 줄 수없다(python obj와 다름)
            image_url = None
        else:
            # 파일처리 -> TODO: 임시 image_url 입력
            image_url = "images/post-0001.jpeg"
        data.update({'image_url': image_url})
        # data  >> {'content': 'a', 'tags': [{'name': 'a'}, {'name': 'b'}, {'name': 'v'}], 'image_url': URL('http://localhost:8000/uploads/images/post-0001.jpeg')}

        post = create_post(data)

        # 4) render함수로 처리한다.
        # return render(request, status_code=status.HTTP_204_NO_CONTENT,
        return render(request, "",
                      hx_trigger=["postsChanged"],
                      messages=[Message.CREATE.write("포스트", level=MessageLevel.INFO)]
                      )

        # 3) temaplate에서는 생성 성공시 list 화면으로 redirect한다. => htmx를 이용해 Nocontent + Hx-Trigger를 응답한다.
        response.status_code = status.HTTP_204_NO_CONTENT
        # response.headers["HX-Trigger"] = "postsChanged"
        response.headers["HX-Trigger"] = json.dumps({
            "postsChanged": None,
            # "showMessage": f"post({post.id}) added."
            "showMessage": Message.CREATE.write("포스트", level=MessageLevel.INFO)['text']
        })
        return response

    except Exception as e:
        # TODO: 템플릿 에러 처리.
        print(f"e  >> {e}")

        raise e

    # response.status_code = 204
    # return response

    # except Exception as e:
    #     response.status_code = 400
    #     return f"Post 생성에 실패했습니다.: {e}"


@app.get("/picstargram/me/", response_class=HTMLResponse)
@login_required
async def pic_me(
        request: Request,
):
    context = {'request': request}
    # return templates.TemplateResponse("picstargram/user/me.html", context)
    return render(request, "picstargram/user/me.html", context=context)


@app.get("/picstargram/users/edit", response_class=HTMLResponse)
async def pic_hx_edit_user(
        request: Request,
        hx_request: Optional[str] = Header(None),
):

    context = {
        'request': request,
    }
    return templates.TemplateResponse("picstargram/post/partials/posts.html", context)




@app.get("/picstargram/users/", response_class=HTMLResponse)
async def pic_users(
        request: Request,
        username: Optional[str] = None,
        hx_request: Optional[str] = Header(None),
):
    context = {'request': request}
    return templates.TemplateResponse("picstargram/user/user.html", context)


@app.post("/picstargram/users/new")
async def pic_new_user(
        request: Request,
        response: Response,
        hx_request: Optional[str] = Header(None),
        user_create_req: UserCreateReq = Depends(UserCreateReq.as_form),
        next_url: Union[str, bool] = Query(None, alias='next')
):
    data = user_create_req.model_dump()
    # data  >> {'email': 'admin@gmail.com', 'username': 'user1', 'password': '321'}
    # data  >> {'email': 'user3@gmail.com', 'username': 'user3', 'description': 'dbwj3', 'password': 'dbwj3'}

    # 검증1: 중복여부(email, username)
    exists_email = get_user_by_email(data['email'])
    if exists_email:
        # return render(request, "", messages=[Message.FAIL.write('회원', text='이미 존재하는 email입니다.', level=MessageLevel.ERROR)])
        raise BadRequestException("이미 존재하는 email입니다")
    exists_username = get_user_by_username(data['username'])
    if exists_username:
        # return render(request, "",
        #               messages=[Message.FAIL.write('회원', text='이미 존재하는 username입니다.', level=MessageLevel.ERROR)])
        raise BadRequestException("이미 존재하는 username입니다.")

    # 실 생성
    user = create_user(data)

    context = {
        'request': request,
    }

    # return render(request, "", context,
    #               cookies=token,
    #               messages=[Message.CREATE.write(f'계정({user.email})')]
    #               )
    token: dict = await pic_get_token(request, UserLoginReq(**dict(email=user_create_req.email, password=user_create_req.password)))

    if next_url:
        return redirect(request, next_url, cookies=token)

    return redirect(request, request.url_for('pic_index'), cookies=token)



@app.post("/picstargram/users/login")
async def pic_login_user(
        request: Request,
        user_login_req: UserLoginReq = Depends(UserLoginReq.as_form),
        next_url: Union[str, bool] = Query(None, alias='next')
):
    #### Schema Dump + 존재/비번검증 -> pic_get_token route로 이관 ####
    token: dict = await pic_get_token(request, user_login_req)

    # 발급한 token -> UserToken -> request에 넣어서 로그인 상태로 만들어놓기
    context = {
        'request': request,
    }

    if next_url:
        return redirect(request, next_url, cookies=token)

    return redirect(request, request.url_for('pic_index'), cookies=token)

    # return render(request, "", context,
    #               cookies=token,
    #               messages=[Message.CREATE.write(entity=f"유저", text="로그인에 성공했습니다.")]
    #               )


# @app.post("/picstargram/get-token", response_model=Token)
@app.post("/picstargram/auth/get-token", response_model=Token)
async def pic_get_token(
        request: Request,
        user_login_req: UserLoginReq,
):
    data: dict = user_login_req.model_dump()

    # 로그인 검증: user존재여부 -> input pw VS 존재user의 hashed_pw verify
    user: UserSchema = get_user_by_email(data['email'])

    if not user:
        raise BadRequestException('가입되지 않은 email입니다.')
    if not verify_password(data['password'], user.hashed_password):
        raise BadRequestException('비밀번호가 일치하지 않습니다.')

    return user.get_token()


@app.post("/picstargram/users/logout")
async def pic_logout_user(
        request: Request,
):

    return redirect(request, request.url_for('pic_index'), logout=True)


