import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class UserSchema(BaseModel):
    id: Optional[int] = None # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    username: str
    image_url: Optional[str] = None

    created_at: Optional[datetime.datetime] # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime]

    posts: Optional[List['PostSchema']] = [] # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.
    comments: Optional[List['CommentSchema']] = [] # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.



class CommentSchema(BaseModel):
    id: Optional[int] = None
    text: str
    created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime]
    user_id: int
    post_id: int

    user: Optional['UserSchema'] = None



class PostSchema(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    image_url: Optional[str] = None
    created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime]
    user_id: int

    user: Optional[UserSchema] = None
    comments: Optional[List[CommentSchema]] = []
