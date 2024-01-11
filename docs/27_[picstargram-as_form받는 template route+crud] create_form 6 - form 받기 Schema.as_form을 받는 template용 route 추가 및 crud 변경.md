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
2. 
