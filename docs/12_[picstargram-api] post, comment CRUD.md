### CRUD

#### Post

##### Read

1. **join대신 `관계객체(SchemaModel)을 포함시킬지 말지 파라미터로 결정`하는 것은 동일하나, `one은 get_xxx() or next()`로
   조회하고, `many는 list comp filtering`을 이용한다**
    - 이 때, posts를 조회하다보니, comments를 포함시킬거면, comment의 작성자user도 포함시켜야해서
    - 추후 수정 될 수 있다.
    ```python
    def get_posts(with_user: bool = False, with_comments: bool = False, with_comment_user: bool = False):
        # one은 next()로 찾는 get_user()를 재활용
        if with_user:
            for post in posts:
                post.user = get_user(post.user_id)
    
        # many는 순회
        if with_comments:
            for post in posts:
                post.comments = [
                    comment for comment in comments if comment.post_id == post.id
                ]
                
                if with_comment_user:
                    for comment in post.comments:
                        comment.user = get_user(comment.user_id)
    
        return posts
    ```

2. route도 동시 작성한다.
    ```python
    @app.get("/posts/", response_model=List[PostSchema])
    async def pic_get_posts(request: Request):
        posts = get_posts(with_user=True)
    
        return posts
    ```

3. 단일조회는 post_id를 route path param -> 메서드 param으로 받는다.
    - 단일 조회는 next(, None)으로 조회하고 없으면 None을 return하게 한다.
    - 그 이후는 관계모델을 포함시킬지 말지 결정한다.
    ```python
    def get_post(post_id: int, with_user: bool = True, with_comments: bool = False, with_comment_user: bool = False):
        post = next((post for post in posts if post.id == post_id), None)
        if not post:
            return None
    
        if with_user:
            post.user = get_user(post.user_id)
    
        if with_comments:
            post.comments = [
                comment for comment in comments if comment.post_id == post.id
            ]
    
            if with_comment_user:
                for comment in post.comments:
                    comment.user = get_user(comment.user_id)
        return post
    ``` 

4. route에서는 path로 받는다.
    - 데이터가 없을 경우, `1) 문자열 return을 위한 Union[, str]`를 response_model로 + `2) status_code변경을 위한 response객체 주입`
    ```python
    @app.get("/posts/{post_id}", response_model=Union[PostSchema, str])
    async def pic_get_post(
            request: Request,
            post_id: int,
            response: Response,
    ):
        post = get_post(post_id, with_user=True, with_comments=False, with_comment_user=False)
    
        if post is None:
            response.status_code = 404
            return "Post 정보가 없습니다."
    
        return post
    ```

##### Create

1. 다른 건 user랑 똑같으나, fk로 있는 one의 존재여부 검사를 해야한다.
    - **추가로, many의 생성에선 `one의 존재여부 검사가 필수`이다.**

    ```python
    # new) many생성시, schema 속  fk로 온 one_id -> 파라미터로 + 내부 one존재여부 검사 필수
    def create_post(post_schema: PostSchema):
        # new) one존재여부 검사 필수 -> 없으면 404 에러
        user = get_user(post_schema.user_id)
        if not user:
            raise Exception(f"해당 user(id={post_schema.user_id})가 존재하지 않습니다.")
    
        try:
            # id + created_at, updated_at 부여
            post_schema.id = find_max_id(posts) + 1
            post_schema.created_at = post_schema.updated_at = datetime.datetime.now()
    
            posts.append(post_schema)
    
        except Exception as e:
            raise e
    
        return post_schema
    ```


3. route에서는 기본 status_code가 201로 바뀌고, 존재여부 검사 생략하며, Schema를 받아온다.
    - test는 /docs로 한다.
    - CUD부터는 DB관련 에러로 `내부에서 raise e`에서 `외부에서 try except`한다.
    ```python
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
    ```

##### Update

1. update 함수는 `update Schema가 개발되면 model(**user_schema.model_dump())로 대체`하며, 지금은 서버 부여 `updated_at`과, 수정허용 필드만 직접 할당한다
    ```python
    def update_post(post_id: int, post_schema: PostSchema):
        # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
        user = get_user(post_schema.user_id)
        if not user:
            raise Exception(f"해당 user(id={post_schema.user_id})가 존재하지 않습니다.")
   
        post = get_post(post_id)
        if not post:
            raise Exception(f"해당 post(id={post_id})가 존재하지 않습니다.")
    
        # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
        # -> 지금은 업데이트 허용 필드를 직접 할당함.
        post.title = post_schema.title
        post.content = post_schema.content
        if post_schema.image_url:
            post.image_url = post_schema.image_url
    
        post.updated_at = datetime.datetime.now()
    
        return post
    ```

2. route는 put으로 하고, `post_id` path param + 데이터를 담은 `Schema`를 사용한다.
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
    - **one 삭제시에는, 딸린 many도 같이 삭제한다**
    ```python
    def delete_post(post_id: int):
        post = get_post(post_id)
        if not post:
            raise Exception(f"해당 post(id={post_id})가 존재하지 않습니다.")
    
        global posts
        posts = [post for post in posts if post.id != post_id]
    
        # one 삭제시, many도 모두 삭제한다.(CASCADE)
        global comments
        # Delete associated comments
        comments = [comment for comment in comments if comment.post_id != post_id]
    ```

2. route에서는 특별한게 없다.
    ```python
    @app.delete("/post/{post_id}", )
    async def pic_delete_post(
            request: Request,
            post_id: int,
            response: Response,
    ):
        try:
            delete_post(post_id)
            return "Post 삭제에 성공했습니다."
        except Exception as e:
            response.status_code = 400
            return f"Post 삭제에 실패했습니다.: {e}"
    ```

#### Comment with user eagerload

- user(one) - comment(many)
- user(one) - post(many) (one) - comment(many)
- **비록 post가 comment보다 부모(one)이지만, `comment는 또다른 one인 user를 항상 eagerload`해야하므로 `먼저 get메서드가 정의`되어야 many를 붙일 때 편하게 붙일 수
  있다.**
    - 먼저 정의해놓고 -> post에 .comments의 관계를 붙일 때, 메서드로 user까지 붙이는 게 더 좋았을 법하다.

##### Read with eagerload(user)

1. **항상 user를 eagerload할거면, `단일조회 메서드 with .user eagerload`를 `전체조회보다 먼저` 정의하며, 전체조회시 단일조회메서드를 사용한다**
    ```python
    # new) user, post와 달리, comment는 user를 eagerload해야하므로 전체조회보다 단일조회를 먼저 정의 -> 전체조회시 단일조회 with eagerload로 활용한다 
    def get_comment(comment_id: int):
        comment = next((comment for comment in comments if comment.id == comment_id), None)
        if not comment:
            return None
    
        # new) comment는 one user를 eagerload하기 위해, 존재여부 검사 및 붙혀주기를 항시 한다
        user = get_user(comment.user_id)
        if not user:
            return None
    
        # new) 항상 eagerload할 거면, with_user boolean없이 항상 붙인다.
        comment.user = user
    
        return comment
    ```


2. route도 단일조회부터
    ```python
    @app.get("/comments/{comment_id}", response_model=Union[CommentSchema, str])
    async def pic_get_comment(
            request: Request,
            comment_id: int,
            response: Response,
    ):
        comment = get_comment(comment_id)
    
        if comment is None:
            response.status_code = 404
            return "Comment 정보가 없습니다."
    
        return comment
    ```


3. **기존 user, post의 crud에서, `many comment`를 관계객체로 가져올 때, `user가 eagerload`되어야하는 상황에선 메서드를 바꿔준다.**
    - many 기본 붙이는 방법: fk조건 + list comp
    - many `eagerload` 붙이는 방법: fk조건 + list comp + `get_메서드`
    - **post입장에선 comment를 eagerload해야하지만, user가 comment를 eagerload하게 되면, 내가 쓴 comment에서 `순환 참조 에러 `가 발생한다**
    - **즉, get_comment()도 `with_user`를 달아야한다.**

    ```python
    # new) eagerload를 하더라도 순환참조에러 발생할 수 있으니, with_xxx를 붙여서 처리한다.
    def get_comment(comment_id: int, with_user: bool = False):
        comment = next((comment for comment in comments if comment.id == comment_id), None)
        if not comment:
            return None
    
        if with_user:
            user = get_user(comment.user_id)
            if not user:
                return None
    
            comment.user = user
    
        return comment
    ```
    ```python
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
    ```
4. **post 단독 조회시에는, comment를 붙일 때, `get_comment + with_user`붙인 메서드로 `.many`를 입력시킨다.**
    ```python
    # def get_post(post_id: int, with_user: bool = True, with_comments: bool = False, with_comment_user: bool = False):
    def get_post(post_id: int, with_user: bool = True, with_comments: bool = False):
        post = next((post for post in posts if post.id == post_id), None)
        if not post:
            return None
    
        if with_user:
            post.user = get_user(post.user_id)
    
        if with_comments:
            post.comments = [
                get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
            ]
    
            # if with_comment_user:
            #     for comment in post.comments:
            #         comment.user = get_user(comment.user_id)
    
        return post
    ```
    ```python
    @app.get("/posts/{post_id}", response_model=Union[PostSchema, str])
    async def pic_get_post(
            request: Request,
            post_id: int,
            response: Response,
    ):
        post = get_post(post_id, with_user=True, with_comments=True)
    
        if post is None:
            response.status_code = 404
            return "Post 정보가 없습니다."
    
        return post
    ```
    - posts 전체조회도 바꿔준다.
    ```python
    def get_posts(with_user: bool = False, with_comments: bool = False):
        # one은 next()로 찾는 get_user()를 재활용
        if with_user:
            for post in posts:
                post.user = get_user(post.user_id)
    
        # many는 순회
        if with_comments:
            for post in posts:
                post.comments = [
                    get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
                ]
    
        return posts
    ```

4. **user의 경우, comments를 붙일 때, with_user가 True면 순환참조에러나니, list comp로만 붙인다**
    - 그대로 둠. get_comment(, with_user=True)를 써서 many를 eagerload해서 처리하면 user-comments-user로 순환참조 에러난다.
    ```python
    def get_users(with_posts: bool = False, with_comments: bool = False):
        if with_posts and with_comments:
            for user in users:
                user.posts = [post for post in posts if post.user_id == user.id]
                # user.comments = [comment for comment in comments if comment.user_id == user.id]
                user.comments = [get_comment(comment.id, with_user=True) for comment in comments if comment.user_id == user.id]
    
        elif with_posts:
            for user in users:
                user.posts = [post for post in posts if post.user_id == user.id]
    
        elif with_comments:
            for user in users:
                # user.comments = [get_comment(comment.id, with_user=True) for comment in comments if comment.user_id == user.id]
                # => 순환참조 에러
                user.comments = [comment for comment in comments if comment.user_id == user.id]
    
        return users
    ```


5. **comments는 `부모없이 전체조회`할 일이 없다. `path로 오는 post_id` or `user_id`를 받고, `with_user도 받아서, 내부에서는 get_comment()메서드로만 조회`
   해보자.**
    - user_id별 comments조회를 할 수도 있찌만, 이미 users 조회시 작성한 comment를 넣어줄 수 있으니 일단 post_id로만 구현해본다.
    - **조회시, path로 부모가 온다면, 부모존재여부 검사 -> 없으면 `CUD의 raise` 대신 `[] 빈 list로 반환`**
    - **전체조회지만 **사실상 부분조회**로서 `fk조건 + list comp`로 반환하거나 eagerload시에는 단일조회메서드까지 추가해서 조회하여 반환한다**
    ```python
    # new) comments의 경우, 단독으로 전체조회X -> path param post_id로 조회
    def get_comments(post_id: int, with_user: bool = False):
        # new) path로 부모가 올 경우, 존재검사 -> CUD가 아니므로, raise 대신 []로 처리
        post = get_post(post_id)
        if not post:
            return []
    
        # one을 eagerload할 경우, get_comment(,with_user=)를 이용하여 early return
        # -> 아닐 경우, list compt fk조건으로 데이터 반환
        if with_user:
            return [
                get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
            ]
    
        return [comment for comment in comments if comment.post_id == post.id]
    ```
6. route에서는 user가 부모로 안껴있으니, with_user=True를 주고 조회하도록 한다
   - 이 때, **post가 부모이므로 `posts/{post_id}/commnets`로 url을 구성한다.**
   - **만약 /comments/{post_id}로 주면, 먼저 정의한 단일조회 route와 겹쳐서, 단일조회가 되어버린다.**
       ```python
       @app.get("posts/{post_id}/comments", response_model=List[CommentSchema])
       async def pic_get_comments(
               request: Request,
               post_id: int,
               response: Response,
       ):
           comments = get_comments(post_id, with_user=True)
        
           return comments
       ```

##### Create

1. many 생성시에는, CUD로서 one이 존재하지 않으면 raise한다.
    - id, created_at, updated_at을 서버부여한 뒤, 메모리 데이터에 append한다.
    ```python
    # new) many생성시, schema 속  fk로 온 one_id -> 파라미터로 + 내부 one존재여부 검사 필수
    def create_comment(comment_schema: CommentSchema):
        # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
        user = get_user(comment_schema.user_id)
        if not user:
            raise Exception(f"해당 user(id={comment_schema.user_id})가 존재하지 않습니다.")
        post = get_post(comment_schema.post_id)
        if not post:
            raise Exception(f"해당 post(id={comment_schema.post_id})가 존재하지 않습니다.")
    
        try:
            # id + created_at, updated_at 부여
            comment_schema.id = find_max_id(comments) + 1
            comment_schema.created_at = comment_schema.updated_at = datetime.datetime.now()
    
            comments.append(comment_schema)
    
        except Exception as e:
            raise e
    
        return comment_schema
    ```
   
2. route
    ```python
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
    ```
   

##### Update
1. cud
    ```python
    def update_comment(comment_id: int, comment_schema: CommentSchema):
        # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
        user = get_user(comment_schema.user_id)
        if not user:
            raise Exception(f"해당 user(id={comment_schema.user_id})가 존재하지 않습니다.")
        post = get_post(comment_schema.post_id)
        if not post:
            raise Exception(f"해당 post(id={comment_schema.post_id})가 존재하지 않습니다.")
    
        comment = get_comment(comment_id)
        if not comment:
            raise Exception(f"해당 commemt(id={comment_id})가 존재하지 않습니다.")
    
        # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
        # -> 지금은 업데이트 허용 필드를 직접 할당함.
        comment.text = comment_schema.text
        comment.updated_at = datetime.datetime.now()
    
        return comment
    ```
   
2. route
    ```python
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
    ```
   

##### Delete

1. cud
    ```python
    def delete_comment(comment_id: int):
        comment = get_comment(comment_id)
        if not comment:
            raise Exception(f"해당 comment(id={comment_id})가 존재하지 않습니다.")
    
        global comments
        comments = [comment for comment in comments if comment.post_id != comment_id]
    ```
   
2. route
    ```python
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
    ```