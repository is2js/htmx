- 장고+modal+htmx 참고 유튜브: https://www.youtube.com/watch?v=3dyQigrEj8A&list=PLh3mlyFFKnrmo-BsEAUtfc9eazfswjvAc
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html
- tagify 정리
  블로그: https://inpa.tistory.com/entry/Tagify-%F0%9F%93%9A-%ED%95%B4%EC%8B%9C-%ED%83%9C%EA%B7%B8tag-%EC%9E%85%EB%A0%A5%EC%9D%84-%EC%9D%B4%EC%81%98%EA%B2%8C-%EA%B0%84%ED%8E%B8%ED%9E%88-%EA%B5%AC%ED%98%84-%EC%82%AC%EC%9A%A9%EB%B2%95
### gpt에 물어보고 API crud -> 템플릿 new/show/edit/remove를 사용하도록 작명을 사용하자.
```python
from fastapi import FastAPI

app = FastAPI()

# Create (C)
@app.post("/api/posts/create")
def create_post():
    # Logic to create a new post
    return {"message": "Post created successfully"}

# Read (R)
@app.get("/api/posts/{post_id}")
def read_post(post_id: int):
    # Logic to retrieve a post by ID
    return {"message": f"Retrieving post with ID: {post_id}"}

# Update (U)
@app.put("/api/posts/update/{post_id}")
def update_post(post_id: int):
    # Logic to update a post by ID
    return {"message": f"Updating post with ID: {post_id}"}

# Delete (D)
@app.delete("/api/posts/delete/{post_id}")
def delete_post(post_id: int):
    # Logic to delete a post by ID
    return {"message": f"Deleting post with ID: {post_id}"}

# Template Routes
# Create (New)
@app.get("/posts/new")
def new_post_form():
    # Display form to create a new post
    return {"message": "Displaying form to create a new post"}

# Read (Show)
@app.get("/posts/{post_id}")
def show_post(post_id: int):
    # Display a specific post
    return {"message": f"Displaying post with ID: {post_id}"}

# Update (Edit)
@app.get("/posts/edit/{post_id}")
def edit_post_form(post_id: int):
    # Display form to edit a post
    return {"message": f"Displaying form to edit post with ID: {post_id}"}

# Delete (Remove)
@app.get("/posts/remove/{post_id}")
def remove_post_form(post_id: int):
    # Display form to remove a post
    return {"message": f"Displaying form to remove post with ID: {post_id}"}

```

### Schema.as_form을 받는 route 추가
1. 기존 json -> Schmea를 받는 route는 존재하지만, `Schema대신 Depends(Schema.as_form)`을 받는 route는 없으니 `template용 route`를 새로 만들어야한다.
    - **이 때, template에서 modal로 수행한 뒤, `CUD 완료하면 RedirectResponse로 redirect`시켜준다.**
    ```python
    @app.post("/picstargram/posts/new")
    async def pic_new_post(
            request: Request,
            response: Response,
            post_create_req=Depends(PostCreateReq.as_form),
            file: Union[UploadFile, None] = None
    ):
        # 1) form데이터는 crud하기 전에 dict로 만들어야한다.
        data = post_create_req.model_dump()
   
        # 2) file필드는 따로 처리한다. but req schema에는 입력X 처리후 dump된 dict에 반영할 준비를 한다.
        if not file:
    
            image_url = None
        else:
            # 파일처리 -> image_url 입력
            image_url = "images/post-0001.jpeg"
            ...
        data.update({'image_url': image_url})
    
        create_post(data)
    
        # 3) temaplate에서는 생성 성공시 list 화면으로 redirect한다.
        response = RedirectResponse('/picstargram/', status_code=302)
        return response
    ```


2. form의 url도 바꿔준다.
    ```html
    <form class="modal-content"
          action="{{ url_for('pic_new_post') }}"
          method="post"
          enctype="multipart/form-data"
    >
    ```
   

### crud 메서드를 schema 받기 -> data:dict받기로 변경해준다.

1. 현재 유저를 모르기 때문에, 고정적으로 user_id 1을 data에 넣어준다.
2. **서버부여 id외  `created_at, updated_at`도 서버부여지만, Schmea(\*\*data)로 생성시에는 Optional이라도 미리 data에 미리 넣어줘야한다.**
3. **Schema(\*\*)에 들어갈 `Optional인 many`가 있다면, `many의 Schema를 미리 변환` 만들어서 넣어줘야한다.**
4. **Many to Many라면, 각각의 id가 부여된 상황에서 -> 중간테이블 데이터도 생성해놔야한다.**
    ```python
    # def create_post(post_schema: PostSchema):
    def create_post(data: dict):
        # 임시 user TODO: 로그인 구현시 현재 사용자가 들어와야함.
        data.update({'user_id': 1})
    
        # optional이지만 Schema(**)로 생성시에는 optional도 미리 채워놔야한다?!
        # TODO: 모델변환시 삭제
        data.update({
            'created_at': datetime.datetime.now(),
            'updated_at': datetime.datetime.now()
        })
    
    
        # many1) 에 대한 정보는 Optional[List[해당Schema]]로 직접 변환해야함.
        # => 이때, Schmea(**tag_data) 들이 아니라, create_tag(tag_dic)로 만들어서 id등 서버부여완료된 객체여야 함?!
        if data.get('tags'):
            # print(f"data['tags']  >> {data['tags']}")
            # data['tags']  >> [{'name': 'a'}, {'name': 'b'}, {'name': 'c'}]
            data['tags'] = [create_tag(tag_data) for tag_data in data['tags']]
    
        post = PostSchema(**data)
    
        # id + created_at, updated_at 서버 부여
        post.id = find_max_id(posts) + 1
        # post.created_at = post.updated_at = datetime.datetime.now()
    
    
        # many2) TODO: many to many라면 둘다id부여된 이후 중간테이블도 생성해줘야함.
        # create_post_tags()
    
        posts.append(post)
    ```
   
#### Schema에서 Optional에 기본값을 지정안하면, Schema(\*\*data) 생성시 에러난다.
- created_at, updated_at 도 `Optional field지만, 기본값 = None을 지정해서, Schmea(\*\*data)가 가능하게 하기`
```python
 class PostSchema(BaseModel):
    id: Optional[int] = None
    # title: str
    content: str
    image_url: Optional[str] = None
    # Optional필드도 = None을 부여해야, backend에서 Schema(**data)시 필드에러 안난다.
    created_at: Optional[datetime.datetime] = None # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime] = None
    user_id: int
    # ...
```
```python
post = PostSchema(**data)

# id + created_at, updated_at 서버 부여
post.id = find_max_id(posts) + 1
post.created_at = post.updated_at = datetime.datetime.now()
```
### Many To Many에서 한쪽 생성시, 나머지가 포함된다면, id각 부여후 중간테이블도 직접 생성

1. post생성시 tags가 여러개 들어오는데, tags를 순회하며, tag들을 각각 생성하여 id부여 -> post_tags에 저장
    ```python
    def create_post_tags(post, tags):
        try:
            for tag in tags:
                post_tag = PostTagSchema(
                    post_id=post.id,
                    tag_id=tag.id,
                )
    
                post_tag.id = find_max_id(post_tags) + 1
                post_tag.created_at = post_tag.updated_at = datetime.datetime.now()
    
                # 아이디 부여 후, 원본에 append하지 않으면 -> 같은 id로만 부여된다. 조심. 매번 id 수동 부여
                post_tags.append(post_tag)
    
        except Exception as e:
            raise e
    ```
   
2. **이미 tag가 `name`이 이미 존재한다면, 생성하지말고 가져와서 넣어주기**
    ```python
    if data.get('tags'):
        tags = []
        for tag_data in data['tags']:
            if tag := get_tag_by_name(tag_data['name']):
                tags.append(tag)
            else:
                tags.append(create_tag(tag_data))
                
        data['tags'] = tags
    ```
    - get_tag_by_name을 구현한다. **소문자로 서로 변경해서 비교해서 있는 것으로 간주한다.**
    ```python
    def get_tag_by_name(name: str):
        tag = next((tag for tag in tags if tag.name.lower() == name.lower()), None)
        if not tag:
            return None
    
        return tag
    ```
   
3. **아무튼 post.tags가 존재할 때만, create_post_tags를 처리한다.**
    ```python
    def create_post(data: dict):
        #...
            # many2) 가 존재할 때만, 중간테이블 생성 호출! 추가
            if post.tags:
                try:
                    create_post_tags(post, post.tags)
                except Exception as e:
                    raise e
    
            posts.append(post)
    
        except Exception as e:
            raise e
    ```