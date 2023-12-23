1. `data폴더에 json` or `lifespan에 dictionary`를 초기화한다
    - **메모리 데이터로 쓸 거라, main.py 전역변수로 xxx_data의 list들을 추후 선언해줘야한다.**
    - **관계에 있는 것은 id를 박아둔다.**
    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
       # 4) [Picstragram] dict -> pydantic schema model
        await init_picstragram_json_to_list_per_pydantic_model()
   
    async def init_picstragram_json_to_list_per_pydantic_model():
        """
        json을 도메인(user, post, comment별로 pydantic model list 3개로 나누어 받지만,
        추후, pydantic_model.model_dumps() -> sqlalchemy model(** )로 넣어서 만들면 된다.
        => 왜 dict list 3개가 아니라 pydantic model list 3개로 받냐면
           관계pydantic model을 가지기 위해서이다.
        ===> 추후, 관계 pydantic model을 -> sqlalchemy Model로 변경해줘야한다.
        """
        picstragram_path = pathlib.Path() / 'data' / 'picstragram.json'
        with open(picstragram_path, 'r') as f:
            picstragram = json.load(f)
            # picstragram >> {'users': [{'id': 1, 'username': 'user1', 'created_at': '2018-05-17 16:56:21', 'updated_at': '2018-05-17 16:56:21'}, ...}

    ```
2. `pydantic`을 설치하고, schemas폴더에 `picstragrams.py`를 만들어, User, Post, Comment에 대해서 정의한다.
    - **이 때, json/dict는 이미 완성된 데이터이므로 id가 완성되어있지만, 통신에 의한 전달에 대비해 `id`가 `Optional[int]`로 놓아둔다.(json -> pydantic(검증변환) ->
      model)**
    - **`관계id`와 달리, `관계Model들을 one/many에 따라 Optional[]/Optional[List[]]`로 같이 정의한다.**
    - 그외 `image_url`과 같은, nullable 필드도 `Optional[]`로 정의한다.
    - **sqlalchemy model을 관계 객체와 넣는 것과 달리, `먼저 선언된 것만 관계모델로 넣을 수 있는 상태`기 때문에, 가장 자주 사용될 Post를 Comment보다 뒤에 선언해서 관계객체를 가질
      수 있게 한다.**
    - **이 때, 문자열 ''안에 Schema model명을 넣으면 알아서 처리된다!!!**
        - comment의 경우, one post를 부를 일이 없고, 작성자를 알아야하기 때문에 user만 관계모델로 넣었다.
    - **또한, `관계객체list의 경우, None으로 주면, docs에서 예시 전체`가 뜨므로, `[]로 줘서 []`만 뜨게 한다.**
    - **이 때, `id: Optional[int]`에 `= None`까지 default값으로 줘야, `create시 빼고 올 때` 에러가 안난다.**
    - **비슷하게 `created_at, updated_at` 서버부여 대상 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.**
    ```python
    import datetime
    from typing import Optional, List
    
    from pydantic import BaseModel
    
    
    class UserSchema(BaseModel):
        id: Optional[int] = None # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
        username: str
        created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상. 
        updated_at: Optional[datetime.datetime]
    
        posts: Optional[List['PostSchema']] = [] # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.
        comments: Optional[List['CommentSchema']] = [] # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.
    
    
    
    
    class CommentSchema(BaseModel):
        id: Optional[int] = None # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
        text: str
        created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상. 
        updated_at: Optional[datetime.datetime]
        user_id: int
        post_id: int
    
        user: Optional['UserSchema'] = None
    
    
    
    class PostSchema(BaseModel):
        id: Optional[int] = None # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
        title: str
        content: str
        image_url: Optional[str] = None
        created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상. 
        updated_at: Optional[datetime.datetime]
        user_id: int
    
        user: Optional[UserSchema] = None
        comments: Optional[List[CommentSchema]] = []
    
    ```


3. 다시 lifespan내 함수로 와서, `json` to 각 `도메인별 pydantcmodel list`로 변환한다.
    - **json.load하면, `겉포장들이 dict or list`이기 때문에, 순회하면서 pydantic model을 `**`로 풀어서 append하는데, 처음부터 끝까지 변환로직이므로 list comp로
      해결하며**
    - **각 도메인별로 불러오되, list가 예상되므로, `dict.get(, [])`로 `list응답이면 None 대신 [] 빈리스트를 default값으로 처리`한다**
    ```python
    async def init_picstragram_json_to_list_per_pydantic_model():
    
        picstragram_path = pathlib.Path() / 'data' / 'picstragram.json'
        with open(picstragram_path, 'r') as f:
            picstragram = json.load(f)
            # 단순 순회하며 처음부터 append하는 것은 list comp로 처리한다.
            # + list를 기대하고 dict를 꺼낼 땐 get(, [])로 처리하면 된다.
            users = [UserSchema(**user) for user in picstragram.get("users", [])]
            comments = [CommentSchema(**user) for user in picstragram.get("comments", [])]
            posts = [PostSchema(**user) for user in picstragram.get("posts", [])]
    ```

4. **각 도메인별로 불러오고 끝이 아니라, `관계객체로서, 먼저추출된 Schema객체 list를 순회하며, pk==fk 조건으로 필드에 넣어주기`를 해야한다.**
    - `각 도메인별 list를 기대`하고 dict를 꺼낼 땐 `dict.get(, [])`로 처리하면 된다.
        - **`M:1은 next(, None)`으로 1개만 찾고 / `1:M관계는 list comp로 여러개`를 찾아서 list로 넣어준다.**
    - 단순 순회하며 처음부터 append하는 것은 list comp로 처리한다.
    - **각 json list를 `**json객체`로 Schema Model에 언패킹해서 넣어주되 `먼저 추출된 관계객체list를 순회`하면서, `next(, None) + pk==fk조건`으로 get하여
      찾아서 넣어준다.**
    - **복잡하므로 3개의 데이터를 찾아서 반환까지 해주고, `global`로 전역변수를 땡겨와 재할당해준다.**
    ```python
    async def init_picstragram_json_to_list_per_pydantic_model():
        """
        json을 도메인(user, post, comment별로 pydantic model list 3개로 나누어 받지만,
        추후, pydantic_model.model_dumps() -> sqlalchemy model(** )로 넣어서 만들면 된다.
        => 왜 dict list 3개가 아니라 pydantic model list 3개로 받냐면
           관계pydantic model을 가지기 위해서이다.
        ===> 추후, 관계 pydantic model을 -> sqlalchemy Model로 변경해줘야한다.
        """
        picstragram_path = pathlib.Path() / 'data' / 'picstragram.json'
        with open(picstragram_path, 'r') as f:
            picstragram = json.load(f)
            # 단순 순회하며 처음부터 append하는 것은 list comp로 처리한다.
            # + list를 기대하고 dict를 꺼낼 땐 get(, [])로 처리하면 된다.
    
            users = [UserSchema(**user) for user in picstragram.get("users", [])]
    
            ## 관계Schema에 집어넣을 땐, next(, None) + pk==fk를 비교하고, 그에 맞는 Schema객체를 넣어준다.
            # M:1관계 - next(, None)으로 1개만 찾기
            # comments = [CommentSchema(**user) for user in picstragram.get("comments", [])]
            comments = [
                CommentSchema(
                    **comment,
                    user=next((user for user in users if user.id == comment["user_id"]), None)
                )
                for comment in picstragram.get("comments", [])
            ]
            
            # M:1(user), 1:M(comments)-list comp로 여러개 찾기
            # posts = [PostSchema(**user) for user in picstragram.get("posts", [])]
            posts = [
                PostSchema(
                    **post,
                    user=next((user for user in users if user.id == post["user_id"]), None),
                    comments=[comment for comment in comments if comment.post_id == post["id"]]
                )
                for post in picstragram.get("posts", [])
            ]
            
            # 1:M 관계 2개
            for user in users:
                user.posts = [post for post in posts if post.user_id == user.id]
                user.comments = [comment for comment in comments if comment.user_id == user.id]
    
        print(f"[Picstragram] users-{len(users)}개, comments-{len(comments)}개, posts-{len(posts)}개의 json 데이터, 각 list에 load")
        return users, comments, posts
    ```

    ```python
    # 메모리 데이터 모음
    tracks_data = []
    users, comments, posts = [], [], []
    
    UPLOAD_DIR = pathlib.Path() / 'uploads'
    
    
    # lifespan for init data
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ...
        
        # 4) [Picstragram] dict -> pydantic schema model
        global users, comments, posts
        users, comments, posts = await init_picstragram_json_to_list_per_pydantic_model()
        
        yield
    
        # shutdown
        
        # ...
    ```

5. **추후 발견한 문제점**
    - **1:M까지 미리 채워놓으면, post - comments를 불러올 때 -> M의 개별 comment에도 1 post가 불러져있으니 `schema.model_dump()`시 id`순환 에러`난다.**
    - **`fk만 가지고 있으면 언제든 부를 수 있으니 crud 정의시로 넘긴다`**
    ```python
    async def init_picstragram_json_to_list_per_pydantic_model():
    
        picstragram_path = pathlib.Path() / 'data' / 'picstragram.json'
        with open(picstragram_path, 'r') as f:
            picstragram = json.load(f)
            # 단순 순회하며 처음부터 append하는 것은 list comp로 처리한다.
            # + list를 기대하고 dict를 꺼낼 땐 get(, [])로 처리하면 된다.
    
            users = [UserSchema(**user) for user in picstragram.get("users", [])]
            comments = [
                CommentSchema(
                    **comment,
                    # user=next((user for user in users if user.id == comment["user_id"]), None)
                )
                for comment in picstragram.get("comments", [])
            ]
            posts = [
                PostSchema(
                    **post,
                    # user=next((user for user in users if user.id == post["user_id"]), None),
                    # comments=[comment for comment in comments if comment.post_id == post["id"]]
                )
                for post in picstragram.get("posts", [])
            ]
        print(f"[Picstragram] users-{len(users)}개, comments-{len(comments)}개, posts-{len(posts)}개의 json 데이터, 각 list에 load")
        return users, comments, posts
    ```