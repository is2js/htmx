- 참고유튜브: https://www.youtube.com/watch?v=8SPF6TBVj28&list=PL-2EBeDYMIbSppj2GYHnvpZ9W69qmkInS&index=2

1. sqlalchemy 패키지 설치 및 루트에 `database.py` 생성

2. [fastapi SQL database 문서 ](https://fastapi.tiangolo.com/tutorial/sql-databases/?h=database)에서 필요한 코드들 복붙
    ```python
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sqlite.db"
    # SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"
    
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base = declarative_base()
    ```


3. 루트에 models.py 생성 후, 공식문서에서 User 예제 복붙
    - 예제 Item모델을 안쓰기 위해, relationship 관련은 다 삭제
    - is_active boolean칼럼 삭제
    - **같은 경로의 database.py를 사용하는 `.database`에서 Base객체를 가져와 정의함.**
    ```python
    from sqlalchemy import Boolean, Column, Integer, String
    
    from database import Base
    
    
    class User(Base):
        __tablename__ = "users"
    
        id = Column(Integer, primary_key=True, index=True)
        email = Column(String, unique=True, index=True)
        hashed_password = Column(String)
        is_active = Column(Boolean, default=True)
    
    ```

4. User는 안쓰므로, Film으로 변경 + id칼럼외 name + director로 칼럼 변경
    ```python
    class Film(Base):
        __tablename__ = "films"
    
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String, unique=True)
        director = Column(String)
    
    ```


5. fastapi문서 toc에서 Main FastApI app > Create the database tables를 참고하여, table 생성
    - main.py의 app객체 생성 전 create_all을 쳐준다.
    ```python
    # from .database import engine
    # from . import models
    from database import engine
    import models
   
    models.Base.metadata.create_all(bind=engine)
    
    app = FastAPI()
    ```
    - 재실행하면 sqlite.db 새엇ㅇ

6. fastapi 문서 같은 메뉴에서, Create a dependency를 보고 session dependency를 만든다.
    - main.py의 route들 등장전에 선언하고 사용할 준비를 한다.
    ```python
    app = FastAPI()
    
    templates = Jinja2Templates(directory="templates")
    
    
    # Dependency
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @app.get("/index/")
    ```
    ```python
    @app.get("/movie/", response_class=HTMLResponse)
    async def movie(
            request: Request,
            hx_request: Optional[str] = Header(None),
            db: Session = Depends(get_db)
    ):
    ```


7. 여기서는 `session(db).query(모델class)` + `.all()`의 문법을 쓴다.
    ```python
    @app.get("/movie/", response_class=HTMLResponse)
    async def movie(
            request: Request,
            hx_request: Optional[str] = Header(None),
            db: Session = Depends(get_db)
    ):
    
        # films = [
        #     {'name': 'Blade Runner', 'director': 'Ridley Scott'},
        #     {'name': 'Pull Fiction', 'director': 'Quentin Tarantino'},
        #     {'name': 'Mulholland Drive', 'director': 'David Lynch'},
        # ]
    
        films = db.query(models.Film).all()
        print(f"films >> {films}")
    ```


8. 이제 startup을 이용해서 count가 0일 때만, dict list를 add commit해서 예시데이터를 만든다.
    - lifespan은 app객체 생성시 필요하므로, 위쪽에 정의한다.
    - 데이터가 count쳐서 0이면, dict list를 순회하면서 add 후 commit한다
    - 이미 데이터가 존재하여 0이 아니면, 데이터가 있다고 print
    ```python
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
   
    # 6 films already in DB.
    ```

9. **load more는 사실상 pagination인데, fastapi에서는 Query Param을 route의 파라미터에 `default 1`을 지정한체 바로 받을 수 있다.**
    ```python
    @app.get("/movie/", response_class=HTMLResponse)
    async def movie(
            request: Request,
            hx_request: Optional[str] = Header(None),
            db: Session = Depends(get_db),
            page: int = 1
    ):
        print(f"page >> {page}")
        # >..
    # http://localhost:8000/movie/ -> page = 1
    # http://localhost:8000/movie/?page=2 -> page = 2
    ```

10. **`view에서는 현재페이지를 알아야 다음페이지인 page + 1을 쿼리파라미터로 전달`할 수 있기 때문에, context에 현재 page를 변수로 넘겨준다.**
    - **즉 pagination을 위해서라면, `default 1인 쿼리파라미터 page를 받고, context로 넘겨주는 작업까지`가 필요하다.**
    ```python
    @app.get("/movie/", response_class=HTMLResponse)
    async def movie(
            request: Request,
            hx_request: Optional[str] = Header(None),
            page: int = 1,
            db: Session = Depends(get_db),
    ):
        films = db.query(models.Film).all()
    
        context = {'request': request, 'films': films, 'page': page}
    ```
11. **view에서도 hx-get 요청시 `현재페이지 + 1`을 `쿼리파라미터로 지정해준다.**
    - route 먼저 page 파라미터 받게 + 현재 page 전달까지 동시에 설정해놓고, view에서 요청해야 에러가 안남.
    - **url_for는 쿼리파라미터를 직접 지원안함(path -> route에서 {}로 받음), `{{url_for()}}` + `쿼리파라미터={{ 값 }}`으로 처리해야한다.**
    ```html
    <button class="px-3 py-1 bg-blue-600 text-white ml-4"
            hx-get="{{ url_for('movie') }}?page={{page + 1}}"
            hx-target="#movie-table-body"
            hx-swap="beforeend"
    >
        Load more
    </button>
    ```
    - /movie로만 입력해서 들어갈 경우 -> route에서 page = default 1 -> 템플릿에 page 1로 드감 -> ?page= 1+1 이 Loadmore에
      ![img.png](../images/08.png)
    - /movie?page=2로 드감 -> load more에는 movie?page=3이
      ![img_1.png](../images/09.png)


12. **남은 문제는, Load more의 page값(현재 page + 1)값이, htmx호출해도 증가하지 않은체 그대로 존재하는 것이다.**
    - htmx호출 이후 `같이 바뀌어야할 것`으로서 Load more버튼도 같이 바뀌어야한다.(내부 데이터가)
    - **그러므로 Load more도 partials에 포함되어 `최초렌딩 include` + `htmx호출시마다 렌딩`되어야한다**
    - **button을 tbody 내부 child로 들어갈려면, `tr > td1개지만 colspan="칼럼갯수"`로서 넣어줘야한다.**

    ```html
    {% for film in films %}
    <tr>
        <td class="border">{{ film.name }}</td>
        <td class="border">{{ film.director }}</td>
    </tr>
    {% endfor %}
    
    
    <tr>
        <td colspan="2">
            <button class="px-3 py-1 bg-blue-600 text-white ml-4"
                    hx-get="{{ url_for('movie') }}?page={{page + 1}}"
                    hx-target="#movie-table-body"
                    hx-swap="beforeend"
            >
                Load more
            </button>
        </td>
    </tr>
    ```
    ![img.png](../images/10.png)
    - 하지만 문제점은 htmx 호출시 Loadmore이 반복해서 나타나게 된다.
      ![img.png](../images/11.png)
    - **맨마지막 `tr의 LoadMore 자체`를 `partials 자체`를 체인지시켜야한다.**


13. **`데이터 추가 요소가 data for문 밖의 맨마지막 자식`일시 `hx-swap`을 `beforeend to outerHTML`으로 `자기자신을 partials로 변경`**
    - **swap될 `hx-target`은 `htmx를 호출하는 나 자신의 최상위태그`인 `closest tr`을 활용한다**
        - 부모를 target로 계속 지정해놓으면 append개념이 자체바뀜(outerHTML)로 바뀌면서, 아예 통째로 갈아져버린다.
        - swap의 target은, 나 자신이 바뀌어야하며, 나 자신이 button태그가 아니라, 데이터단위 최상위 태그인 tr태그다.
    ```html
    {% for film in films %}
    <tr>
        <td class="border">{{ film.name }}</td>
        <td class="border">{{ film.director }}</td>
    </tr>
    {% endfor %}
    
    
    <tr>
        <td colspan="2">
            <button class="px-3 py-1 bg-blue-600 text-white ml-4"
                    hx-get="{{ url_for('movie') }}?page={{page + 1}}"
                    hx-target="closest tr"
                    hx-swap="outerHTML"
            >
                Load more
            </button>
        </td>
    </tr>
    ```
    ![img.png](../images/12.png)


14. 이제 백엔드에서 최초렌딩을 page당 갯수만큼 보여주는 pagination을 수행하여, load more시 해당하는 페이지당 갯수를 던져지도록 한다.
    - **page당 갯수 N을 상수로 미리 정해놓고**
    - **`OFFSET`은, `(page - 1) * N`으로 2번째부터는 N개를 건너띄고, 처음에는 건너띄는 것 없이 `limit(N)`으로 N개를 보여주면 된다.**
    ```python
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
    
    ```