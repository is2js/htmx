### tag CRUD

- 일반적인 model의 crud를 수행하면 되므로, user를 참고해서 작성한다
- **조회(get) 정의시, 추후 `post`와 중간테이블을 생성 -> `tag.posts`의 many관계를 load하도록 단일조회시 `with_posts`, 전체조회시 `with_posts`를 boolean으로
  받아 넣어줘야하지만, 일단은 생략하고 기본CRUD부터 수행한다.**

1. crud는 user를 참고하여 바탕으로 관계없이 편하게 정의한다.
    ```python
    def get_tags():
        return tags
    
    
    def get_tag(tag_id: int):
        tag = next((tag for tag in tags if tag.id == tag_id), None)
        if not tag:
            return None
    
        return tag
    
    
    def create_tag(tag_schema: TagSchema):
        try:
            # id 부여
            tag_schema.id = find_max_id(tags) + 1
            # created_at, updated_at 부여
            tag_schema.created_at = tag_schema.updated_at = datetime.datetime.now()
    
            tags.append(tag_schema)
        except Exception as e:
            raise e
    
        return tag_schema
    
    
    def update_tag(tag_id: int, tag_schema: TagSchema):
        tag = get_tag(tag_id)
        if not tag:
            raise Exception(f"해당 tag(id={tag_id})가 존재하지 않습니다.")
    
        # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
        # -> 지금은 업데이트 허용 필드를 직접 할당함.
        tag.name = tag_schema.name
    
        tag.updated_at = datetime.datetime.now()
    
        return tag
    
    
    def delete_tag(tag_id: int):
        tag = get_tag(tag_id)
        if not tag:
            raise Exception(f"해당 tag(id={tag_id})가 존재하지 않습니다.")
    
        global tags
        tags = [tag for tag in tags if tag.id != tag_id]
    ```


2. route
    ```python
    ############
    # picstragram tags
    ############
    @app.get("/tags/", response_model=List[TagSchema])
    async def pic_get_tags(request: Request):
        tags = get_tags()
    
        return tags
    
    
    @app.get("/tags/{tag_id}", response_model=Union[TagSchema, str])
    async def pic_get_tag(
            request: Request,
            tag_id: int,
            response: Response,
    ):
        tag = get_tag(tag_id)
    
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
    async def pic_delete_user(
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
    
    ```

### post_tags CRUD

#### read

- **comments, likes와 달리, 자체적으로는 쓰이지 않은 `순수 중간테이블`으로서 `자체CRUD`는 없을 듯하다.**
    - 하지만, `한쪽one.중간테이블manys`를 get_중간테이블(한쪽one_id) 내부에서 넣어줘야하고
    - 그 중간테이블many의 각 데이터에는 `중간테이블객체.반대편one`의 데이터가 `with_반대편=`여부로 eagerload되어있어야한다.
    - eagerload를 해야하는 경우 단일조회 with_관계 -> 전체조회 with_관계 순으로 정해줬었다.
    - likes는 한쪽one인 post가 주인공이라서 get_likes(post_id)로, `한쪽one에 대해서만 .중간테이블`을 해줬지만
    - **post_tags는 `post.tags`로 post가 주인공일 수도 있고, `tag.posts`로 tag가 주인공 일 수도 있다.**
    - python에서는 같은메서드명으로 여러파라미터를 못만드니, 중간테이블을 가지는 `양쪽이 모두 주인공이 가능한 상황`에서는
        - **단일조회는 자신의id로 2개의 관계를 반영한 `get_post_tag(post_tag_id, with_한쪽one=, with_반대쪽one-)`**
        - **전체(부분)조회 모두 `get_post_tags_by_post_id(, with_tag=) for post.tags`
          와 `get_post_tags_by_tag_id(, with_post=) for tag.posts`
          로 양쪽을 각각 주인공으로서 정의해준다.**

- 실질중간테이블 likes의 CRUD를 참고하여 작성해보자.


1. 단일조회는 중간테이블id를 사용해서 조회하되, `관계 양쪽주인공 모두를 with_`로 반영한다.
    ```python
    def get_post_tag(post_tag_id: int, with_post: bool = False, with_tag: bool = False):
        post_tag = next((post_tag for post_tag in post_tags if post_tag.id == post_tag_id), None)
        if not post_tag:
            return None
    
        if with_post:
            post_tag.post = get_post(post_tag.post_id)
            
        if with_tag:
            post_tag.tag = get_tag(post_tag.tag_id)
    
        return post_tag
    ```

2. 전체(부분)조회에서는, 한쪽one(post).중간테이블many 호출시, 각 중간테이블데이터에 반대쪽one(tag)가 박혀있도록 하기 위해, `by_한쪽one( , with_반대쪽one=True)`의
   전체조회메서드를 정의한다.
    - 양쪽다 주인공이지만, 일단 post를 주인공(post.tags)를 위해 먼저 정의한다.
    ```python
    # post.post_tags -> 각 post_tag에 tag가 박힘 : post.tags 를 위해, 
    # post_id로 post_tags를 찾되, 내부에서 post_tags에서는 with_tags를 eagerload한 것을 불러온다.
    def get_post_tags_by_post_id(post_id: int, with_tag: bool = False):
        # 1) 일단 주인공 fk키의 존재여부 검사 (조회니까 raise 대신 []로 처리)
        post = get_post(post_id)
        if not post:
            return []
    
        # 2) 메모리데이터에서 특정 post_id로 post_tags를 가져오되,
        #    post_tags의 각 데이터마다 tag(반대쪽one)이 박혀있도록 eagerload하기 위해
        #    단일조회메서드(with_tags=True)를 활용한다
        if not with_tag:
            return [post_tag for post_tag in post_tags if post_tag.post_id == post_id]
        else:  # with_tag=True
            return [
                get_post_tag(post_tag.id, with_tag=True) for post_tag in post_tags if
                post_tag.post_id == post_id
            ]
    ```

##### with_반대쪽one(tag) 옵션의 중간테이블 단일/전체 조회 완성 -> 기존의 한쪽one(post) 단일/전체 조회 메서드에 with_옵션 추가 + 삭제시 cascade 삭제 추가

1. 중간테이블의 단일/전체조회 with_반대쪽one(tag) 정의가 끝나면, `get_post + get_posts`와 `delete_post`에, 생겨난 중간테이블many에 대한 옵션을 추가한다.
    - 관계는 조회에서만 일어나며, 단일조회 -> 전체조회시 객체포함조회 및 삭제시 같이 삭제가 되도록 해준다?
    - 참고로 one관계는 fk로 박히기 떄문에 따로 처리안해줘도 된다.

2. 일단 단일조회 get_post( ,with_post_tag=)추가
    ```python
    def get_post(post_id: int, 
                 with_user: bool = True, with_comments: bool = False, with_likes: bool = False, with_post_tags: bool = False):
        post = next((post for post in posts if post.id == post_id), None)
        if not post:
            return None
    
        if with_user:
            post.user = get_user(post.user_id)
            
        # ...
       # likes(중간테이블) 구현후, with_likes 추가
        if with_likes:
            post.likes = [
                get_like(like.id, with_user=True) for like in likes if like.post_id == post.id
            ]
        
        # post_tags(중간테이블) 구현후, with_post_tags 추가
        if with_post_tags:
            post.post_tags = get_post_tags_by_post_id(post.id, with_tag=True)
    
        return post
    ```
3. **하지만, post에는 관계필드로서 PostTagSchema가 아니라, `List[TagSchema]`를 `.tags`로 접근해야한다.**
    - **`likes`는 실질 중간테이블이지만, `post_tags`는 순수 중간테이블로서, 오로지 연결용 -> .xxx 필드나 xxxSchema가 없다.**
    - **그러므로 post_tag의 `get_post_tags_by_주인공`로 받은 post_tags를, post.likes처럼 필드에 넣어주는 것으로 끝나는게
      아니라, `post_tag들마다 eargerload한 .tag를 추출한 tag list`를 post.tags로 넣어주는 작업까지 시행해준다.**
    - 실질 중간테이블과 달리, `순수 중간테이블은 필드/schema도 없고`, **`반대편one을 데이터마다 eagerload한 중간테이블 단일/전체 조회`
      메서드를 `한쪽one(post)에 반대편one을 many(.tags)`주면서 `옵션도 with_반대편s(with_tags)`로 바꿔준다.**
        - **post.post_tags를 만든 상태이므로, list comp + .tag(중간테이블조회시 eagerload된 반대편one)를 추출하여 tags를 만든다.**
    - 즉, `with_post_tags`=True -> `with_tags`=True, post.`post_tags` -> post.`tags`
    ```python
    def get_post(
            post_id: int,
            with_user: bool = True, with_comments: bool = False, with_likes: bool = False,
            # with_post_tags: bool = False
            with_tags: bool = False
    ):
        # post_tags(중간테이블) 구현후, with_post_tags 추가 -> with_tags 추가
        # if with_post_tags:
        #     post.post_tags = get_post_tags_by_post_id(post.id, with_tag=True)
        
        if with_tags:
            post.tags = [post_tag.tag for post_tag in get_post_tags_by_post_id(post.id, with_tag=True)]
    
        return post
    
    ```

4. post 단일 조회 route에서도, with_tags=True를 줘서, /docs에서 태스트한다.
    ```python
    @app.get("/posts/{post_id}", response_model=Union[PostSchema, str])
    async def pic_get_post(
            request: Request,
            post_id: int,
            response: Response,
    ):
        # post = get_post(post_id, with_user=True, with_comments=True)
        # post = get_post(post_id, with_user=True, with_comments=True, with_likes=True)
        post = get_post(post_id, with_user=True, with_comments=True, with_likes=True, with_tags=True)
    
        if post is None:
            response.status_code = 404
            return "Post 정보가 없습니다."
    
        return post
    
    ```

5. post의 전체조회에서도, with_tags를 반영해준다.
    ```python
    def get_posts(
            with_user: bool = False,
            with_comments: bool = False,
            with_likes: bool = False,
            with_tags: bool = False
    ):
        # 중간테이블 post_tags를 many로 추가 -> 조회/삭제시 옵션 추가
        if with_tags:
            for post in posts:
                post.tags = [
                    post_tag.tag for post_tag in get_post_tags_by_post_id(post.id, with_tag=True)
                ]
    
        return posts
    ```
    ```python
    @app.get("/posts/", response_model=List[PostSchema])
    async def pic_get_posts(request: Request):
        # posts = get_posts(with_user=True, with_comments=True)
        posts = get_posts(with_user=True, with_comments=True, with_likes=True, with_tags=True)
        return posts
    ```

6. 도메인모델에 **many관계가 추가된다면, 중간테이블이라도 cascade삭제**를 해준다.?!
    - **`실질 중간테이블인 likes, comments`는 user삭제시 or post삭제시 -> `중간테이블도 many로서 삭제`가 되어야한다.**
    - 반대쪽 one은 살아있다. 순수 중간테이블도 그 데이터가 삭제되어야한다.
    - **양쪽에서 각 삭제시, 다 적용되어야한다.**
    ```python
    def delete_post(post_id: int):
        post = get_post(post_id)
        if not post:
            raise Exception(f"해당 post(id={post_id})가 존재하지 않습니다.")
    
        
        global post_tags
        post_tags = [post_tag for post_tag in post_tags if post_tag.post_id != post_id]
    ```

###### 반대쪽 tag도 주인공으로서 조회 + 삭제시, many로서 중간테이블->_반대편one의 필드 추가 + cascade 삭제

1. 순수중간테이블의 조회메서드에, `by_현재주인공_id`로 단일조회/전체조회를 만든다.
    ```python
    # 순수중간테이블의 주인공2: tag에서 대해서도 전체조회메서드를 만든다.
    # - 단일은 with_로 둘다 반영함.
    def get_post_tags_by_tag_id(tag_id: int, with_post: bool = False):
        # 1) 일단 주인공 fk키의 존재여부 검사 (조회니까 raise 대신 []로 처리)
        tag = get_tag(tag_id)
        if not tag:
            return []
    
        # 2) 메모리데이터에서 특정 tag_id로 post_tags를 가져오되,
        #    post_tags의 각 데이터마다 post(반대쪽one)이 박혀있도록 eagerload하기 위해
        #    단일조회메서드(with_posts=True)를 활용한다
        if not with_post:
            return [post_tag for post_tag in post_tags if post_tag.tag_id == tag_id]
        else:  # with_post=True
            return [
                get_post_tag(post_tag.id, with_post=True) for post_tag in post_tags
                if post_tag.tag_id == tag_id
            ]
    ```

2. 주인공의 단일조회/전체조회 메서드에, many로서 반대편one`s`를 with_옵션과 함께 추가한다.
    ```python
    # def get_tag(tag_id: int):
    def get_tag(tag_id: int, with_posts: bool = False):
        tag = next((tag for tag in tags if tag.id == tag_id), None)
        if not tag:
            return None
    
        if with_posts:
            tag.posts = [post_tag.post for post_tag in get_post_tags_by_tag_id(tag.id, with_post=True)]
    
        return tag
    ```
   ```python
    def get_tags(with_posts: bool = False):
        if with_posts:
            for tag in tags:
                tag.posts = [
                    post_tag.post for post_tag in get_post_tags_by_tag_id(tag.id, with_post=True)
                ]
        return tags
    ```
    
    
3. route에서도 with_posts=True를 줘서, /docs에서 태스트한다.
    ```python
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
    ```


4. 삭제시, many에 해당하는 중간테이블 데이터도 같이 삭제해준다.
    ```python
    def delete_tag(tag_id: int):
        tag = get_tag(tag_id)
        if not tag:
            raise Exception(f"해당 tag(id={tag_id})가 존재하지 않습니다.")
    
        global tags
        tags = [tag for tag in tags if tag.id != tag_id]
    
    
        # post와 중간테이블데이터도 many로서 삭제
        global post_tags
        post_tags = [post_tag for post_tag in post_tags if post_tag.tag_id != tag_id]
    ```