1. CRUD를 작성해야하는데, main.py에 너무 많이 나올 것 같아서 `crud폴더` > picstragrams.py를 만들어서 처리하자
    - 조회: 전체 조회는 `전역변수 users list`를 `return`해주면 되고, / 단일 조회는 `next(, None) + id를 해당하는 조건`으로 가져온다.
        - 만약, 관계모델을 미리 load하지 않은 상황이면, one부모: next / many자식: list comp로 가져와서 할당해준다.
    - 생성: 데이터를 하나하나 받는게 아니라, SchemaModel단위로 request에서 들어온다고 생각하고, **`생성`은 Schema 모델을 `전역변수 users list에 append`만 한다**
        - 존재여부 확인을 위해, get_user() 등의 단일조회 메서드를 사용한다.
        - **one부모 관계 ex> comment -> user도 있고, post도 있어야함 -> `if 관계1 and 관계2`조회가 되었을 때만, 관계를 추가한 뒤, `반대 관계도 추가해줘야한다`.
          하나라도 없으면 return None or False**
    - 수정: `모든 필드가 다 올필요 없기`때문에, `수정가능한 필드만 Optional로 받는 Schema`를 따로 정의해서, `단일조회 -> 수정`을 해준다.

2. **일단 `crud 함수들을 route가 존재하는 main.py에서 뺏다`면, `전역변수 메모리 데이터도 crud하는 곳으로 빼야`한다**
    - crud/picstragrams.py에 `전역변수 users, comments, posts`를 가져오고
        ```python
        # crud/picstragrams.py
        # CRUD 함수 정의
        users, comments, posts = [], [], []
        ```

    - main.py에서는 `crud 함수들을 import`해서 사용한다.
        ```python
        # main.py
        from crud.picstargrams import users, posts
       ```

    - 데이터 load함수에서는 **`import한 list변수.extend()`로 추가해준다.**
         ```python
         @asynccontextmanager
         async def lifespan(app: FastAPI):
             # 4) [Picstragram] dict -> pydantic schema model
             # global users, comments, posts
             users_, comments_, posts_ = await init_picstragram_json_to_list_per_pydantic_model()
             users.extend(users_)
             comments.extend(comments_)
             posts.extend(posts_)
         
             yield
         
             # shutdown
         ```
      
3. user부터 전체조회 -> 단일조회 -> create -> update -> delete순으로 정의해보자

### CRUD
#### User
##### Read 
1. **join대신 관계객체(SchemaModel)을 포함시킬지 말지 파라미터로 결정하게 한다**
    - **1:M관계면 list comp로 / M:1이면 next(, None)으로 가져온다.**
    ```python
    def get_users(with_posts: bool = False, with_comments: bool = False):
        if with_posts and with_comments:
            for user in users:
                user.posts = [post for post in posts if post.user_id == user.id]
                user.comments = [comment for comment in comments if comment.user_id == user.id]
    
        elif with_posts:
            for user in users:
                user.posts = [post for post in posts if post.user_id == user.id]
    
        elif with_comments:
            for user in users:
                user.comments = [comment for comment in comments if comment.user_id == user.id]
    
        return users
    ```

2. route도 동시 작성한다.
    - route는 다른 도메인의 user도 있을 수 있으니 `pic_`을 앞에 붙혔다.
    - response_model을 생략해도 되지만 SchemaModel을 명시했다.
    ```python
    @app.get("/users/", response_model=List[UserSchema])
    async def pic_get_users(request: Request):
        users = get_users(with_posts=True, with_comments=True)
    
        return users
    ```
    
3. 단일조회는 user_id를 route path param -> 메서드 param으로 받는다.
    - 단일 조회는 next(, None)으로 조회하고 없으면 None을 return하게 한다.
    - 그 이후는 관계모델을 포함시킬지 말지 결정한다.
    ```python
    def get_user(user_id: int, with_posts: bool = False, with_comments: bool = False):
        
        user = next((user for user in users if user.id == user_id), None)
        if not user:
            return None
        
        if with_posts and with_comments:
            user.posts = [post for post in posts if post.user_id == user.id]
            user.comments = [comment for comment in comments if comment.user_id == user.id]
        
        elif with_posts:
            user.posts = [post for post in posts if post.user_id == user.id]
            
        elif with_comments:
            user.comments = [comment for comment in comments if comment.user_id == user.id]
            
        return user
    ``` 

4. route에서는 path로 받는다.
    - 데이터가 없을 경우, `1) 문자열 return을 위한 Union[, str]`를 response_model로  + `2) status_code변경을 위한 response객체 주입`
    ```python
    @app.get("/users/{user_id}", response_model=Union[UserSchema, str])
    async def pic_get_user(
            request: Request,
            user_id: int,
            response: Response,
    ):
        user = get_user(user_id, with_posts=True, with_comments=True)
    
        if user is None:
            response.status_code = 404
            return "User 정보가 없습니다."
    
        return user
    ```
 

##### Create
1. 일단 `기존 data list의 max id를 구해서, +1을 한 id`를 찾는 유틸을 먼저 저장한다.
    - **이 때, `max( ,default=0`을 둬서, `+1하면 1이 처음 시작`되도록 한다.**
    ```python
    def find_max_id(model_list):
        return max([model.id for model in model_list], default=0)
    ```
2. **어차피 request에서는 `Optional[int]인 id`를 제외하고 채워진 `Schema Model`이 들어올 것이기 때문에, `전역데이터list의 max+1의 id부여` + `전역데이터 list에 append`만 해주면 된다.**
    - **`created_at, updated_at` 도 create시 사실 빼고와야하며, 서버부여 대상으로 여기서 부여해준다.**  
    - **unique칼럼으로 비교하는 존재여부는 생략한다.**
    - **생성부터는, `db에서 실패할 수 있으므로, raise e를 return None`한 뒤, 외부에서 str으로 반환해줄 준비를 한다.**
    ```python
    def create_user(user_schema: UserSchema):
        try:
            # id 부여
            user_schema.id = find_max_id(users) + 1
            # created_at, updated_at 부여
            user_schema.created_at = user_schema.updated_at = datetime.datetime.now()
        
            users.append(user_schema)
        except Exception as e:
            raise e
    
        return user_schema
    ```


3. route에서는 기본 status_code가 201로 바뀌고, 존재여부 검사 생략하며, UserSchema를 받아온다.
    - test는 /docs로 한다.
    - CUD부터는 DB관련 에러로 `내부에서 raise e`에서 `외부에서 try except`한다.
    ```python
    @app.post("/users", response_model=Union[UserSchema, str], status_code=201)
    async def pic_create_user(
            request: Request,
            user_schema: UserSchema,
            response: Response,
    ):
        try:
            user = create_user(user_schema)
            print(f"user >> {user}")
    
            return user
        except Exception as e:
            response.status_code = 400
            return f"User 생성에 실패했습니다.: {e}"
    ```
   
##### Update
1. update 함수는 `update Schema가 개발되면 model(**user_schema.model_dump())로 대체`하며, 지금은 서버 부여 `updated_at`과, 수정허용 필드만 직접 할당한다 
    ```python
    def update_user(user_id: int, user_schema: UserSchema):
        user = get_user(user_id)
        if not user:
            raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")
    
        # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
        # -> 지금은 업데이트 허용 필드를 직접 할당함.
        user.username = user_schema.username
        user.updated_at = datetime.datetime.now()
    
        return user
    ```
   
2. route는 pu으로 하고, `user_id` path param + 데이터를 담은 `Schema`를 사용한다.
    ```python
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
    
    ```
   
##### delete
1. **delete는 조회시 `enumerate를 추가한 index return  next( , None)`를 이용해 del list[index]로 처리할 수도 있지만**
    - **`global을 통한 전역변수 재할당` + `필터링을 위한 list comp`로 처리할 수 있다.**
    - 이렇게 처리하면, `삭제할 데이터가 없어도 에러가 발생하지 않는다.`
    ```python
    def delete_user(user_id: int):
        user = get_user(user_id)
        if not user:
            raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")
        
        global users
        users = [user for user in users if user.id != user_id]
    ```
2. **`1:M관계에 있는 one삭제시 -> many도 CASCADE로서, global + list comp filtering으로 같이 다 삭제`한다**
    ```python
    def delete_user(user_id: int):
        user = get_user(user_id)
        if not user:
            raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")
    
        global users
        users = [user for user in users if user.id != user_id]
    
        # one 삭제시, many도 모두 삭제한다.(CASCADE)
        global posts, comments
        # Delete associated posts
        posts = [post for post in posts if post.user_id != user_id]
        # Delete associated comments
        comments = [comment for comment in comments if comment.user_id != user_id]
    ```
  
3. route에서는 특별한게 없다.
    ```python
    @app.delete("/users/{user_id}", )
    async def pic_update_user(
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
    ```