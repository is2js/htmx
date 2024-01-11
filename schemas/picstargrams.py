import datetime
import json
from inspect import signature
from typing import Optional, List, Any, Type, Union

from fastapi import Form, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field, model_validator, validator, field_validator, create_model, ValidationError


class UserSchema(BaseModel):
    id: Optional[int] = None  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    username: str
    image_url: Optional[str] = None

    created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime]

    posts: Optional[List['PostSchema']] = []  # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.
    comments: Optional[List['CommentSchema']] = []  # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.


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
    # title: str
    content: str
    image_url: Optional[str] = None
    # Optional필드도 = None을 부여해야, backend에서 Schema(**data)시 필드에러 안난다.
    created_at: Optional[datetime.datetime] = None # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime] = None
    user_id: int

    user: Optional[UserSchema] = None
    comments: Optional[List[CommentSchema]] = []

    likes: Optional[List['LikeSchema']] = []
    tags: Optional[List['TagSchema']] = []


class TagCreateReq(BaseModel):
    # value (input[name=""]) -> name (Schmea-field)
    name: str = Field(alias='value')


class PostCreateReq(BaseModel):
    # content: str
    content: str

    # image_url: Optional[str] = None
    # image_url: Optional[str] = None
    # created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    # updated_at: Optional[datetime.datetime]
    # user_id: int

    # user: Optional[UserSchema] = None
    tags: Optional[List[TagCreateReq]]

    @classmethod
    def as_form(
            cls,
            content: str = Form(...),
            tags: str = Form(None),
    ):
        # obj array [string] to dict list [python]
        if tags:
            tags = json.loads(tags)

        return cls(content=content, tags=tags)

    # @field_validator('tags', mode="before")
    # @classmethod
    # def from_literal(cls, data: Any) -> Any:
    #     """Automatically parse '[]' literals
    #     여기서는 input[name='tags'].value로 넘어오는 '[{"value":"1"},{"value":"2"},{"value":"3"},{"value":"4"}]의 string을
    #     json.loads()를 통해, json object list로 변환 => 그 이후 schema의 tags에 list로 입력된다.
    #     """
    #     if isinstance(data, str):
    #         # data >> [{"value":"a"},{"value":"b"},{"value":"c"}]
    #         # type(data)  >> <class 'str'>
    #         converted_data = json.loads(data)
    #         # converted_data  >> [{'value': 'a'}, {'value': 'b'}, {'value': 'c'}]
    #         # t  >> <class 'list'>
    #
    #         return converted_data

    #     assert data.count("|") == 1, "literal requires one | separator"
    #     x, y = data.split("|")
    #     # field type conversion can be handled by pydantic
    #     return dict(x=x, y=y)
    # return data


class UpdatePostReq(BaseModel):
    content: str

    # @classmethod
    # def __get_validators__(cls):
    #     yield cls.validate_to_json
    #
    # @classmethod
    # def validate_to_json(cls, value):
    #     if isinstance(value, str):
    #         return cls(**json.loads(value))
    #     return value


class LikeSchema(BaseModel):
    id: Optional[int] = None
    user_id: int
    post_id: int
    created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.

    user: Optional[UserSchema] = None  # like.user(좋아요 누른사람)


class TagSchema(BaseModel):
    id: Optional[int] = None
    name: str
    created_at: Optional[datetime.datetime]  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime]

    posts: Optional[List[PostSchema]] = []  # tag.posts 해당 tag에 속한 글들


class PostTagSchema(BaseModel):
    id: Optional[int] = None
    post_id: int
    tag_id: int
    created_at: Optional[datetime.datetime] = None # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    # Optional도 기본값을 줘야 -> Schema(**)시 기본값 입력이 되며, 안주면 에러가 난다.
    updated_at: Optional[datetime.datetime] = None

    post: Optional[PostSchema] = []  # 중간테이블에선 각각이 one이다.
    tag: Optional[TagSchema] = []
