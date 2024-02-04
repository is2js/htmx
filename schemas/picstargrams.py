import datetime
import json
from typing import Optional, List, Any, Type, Union

from fastapi import Form, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field, model_validator, validator, field_validator, create_model, ValidationError, \
    EmailStr

from config import settings
from exceptions.template_exceptions import BadRequestException
from utils.auth import create_token


class UserSchema(BaseModel):
    id: Optional[int] = None  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    email: str  # 추가
    hashed_password: str  # 추가
    username: str
    description: Optional[str] = None
    image_url: Optional[str] = None

    created_at: Optional[datetime.datetime] = None  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    updated_at: Optional[datetime.datetime] = None  # None을 줘야, 안들어와도 허용된다.

    posts: Optional[List['PostSchema']] = []  # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.
    comments: Optional[List['CommentSchema']] = []  # None으로 주면, docs에서 예시 전체가 뜨므로, []로 줘서 []만 뜨게 한다.

    def get_token(self):
        "TODO: sqlalchemy User 모델 이관"
        return {
            "access_token": "Bearer " + create_token(
                data=dict(
                    sub=str(self.id),
                    email=self.email,
                    username=self.username,
                    description=self.description,
                    image_url=self.image_url,
                    # staff=self.is_admin),
                    # 그외 exp, iat iss는 create_token 내부에서
                ),
                delta=settings.access_token_expire_minutes,
            ),
            "refresh_token": "Bearer " + create_token(
                data=dict(sub=str(self.id)),  # 그외 exp, iat iss는 create_token 내부에서
                delta=settings.refresh_token_expire_minutes,
            ),
        }

    def refresh_token(self, refresh_token: str, iat: str):
        "TODO: sqlalchemy User 모델 이관"
        now = int(datetime.datetime.utcnow().timestamp())
        iat = int(iat)

        # refresh 발급기간이 만료기간(delta)의 1/2을 넘어선다면, refresh token도 같이 발급
        if now - iat >= settings.refresh_token_expire_minutes * 60 / 2:
            print(f"refresh의 1/2을 지나서, 둘다 재발급 ")
            return self.get_token()  # refresh 절반이 지나면, 둘다 새로 발급
        # 아니라면, access_token만 재발급
        else:
            return {
                "access_token": "Bearer " + create_token(
                    data=dict(
                        sub=str(self.id),
                        email=self.email,
                        description=self.description,
                        username=self.username,
                        image_url=self.image_url,
                        # staff=self.is_admin),
                        # 그외 exp, iat iss는 create_token 내부에서
                    ),
                    delta=settings.access_token_expire_minutes,
                ),
                "refresh_token": refresh_token,
            }


class UserCreateReq(BaseModel):
    email: str
    username: str
    description: Optional[str] = None
    password: str

    @classmethod
    def as_form(
            cls,
            email: EmailStr = Form(...),
            username: str = Form(...),
            description: str = Form(None),
            password1: str = Form(...),
            password2: str = Form(...),
    ):
        # obj array [string] to dict list [python]
        # if tags:
        #     tags = json.loads(tags)
        # error_msg = []
        if password1 != password2:
            # raise Exception("비밀번호가 서로 일치하지 않습니다.")
            raise BadRequestException('비밀번호가 서로 일치하지 않습니다.')

        # if 20 < len(password1) or len(password1) < 8:
        #     error_msg.append("패스워드의 길이는 8자 보다 길고 20자 보다 짧아야 합니다.")
        # if not any(char.isdigit() for char in password1):
        #     error_msg.append("패스워드에 최소한 1개 이상의 숫자가 포함되어야 합니다.")
        # if not any(char.isupper() for char in password1):
        #     error_msg.append("패스워드에 최소한 1개 이상의 대문자가 포함되어야 합니다.")
        # if not any(char.islower() for char in password1):
        #     error_msg.append("패스워드에 최소한 1개 이상의 소문자가 포함되어야 합니다.")
        #
        # if error_msg:
        #     raise Exception("<br>".join(error_msg))

        return cls(email=email, username=username, description=description, password=password1)


class UserLoginReq(BaseModel):
    email: str
    password: str

    @classmethod
    def as_form(
            cls,
            email: EmailStr = Form(...),
            password: str = Form(...),
    ):
        # if password1 != password2:
        #     raise BadRequestException('비밀번호가 서로 일치하지 않습니다.')
        return cls(email=email, password=password)


class Token(BaseModel):
    # refresh 할 때, next token이 비워있을 수 있어서 nullable
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class RefreshToken(BaseModel):
    refresh_token: str


class UserToken(BaseModel):
    # id: int
    id: int = Field(alias='sub')
    email: EmailStr
    description: Optional[str] = None
    # hashed_password: str
    username: str
    image_url: Optional[str] = None


# Upload Image
class UploadImageReq(BaseModel):
    image_bytes: bytes
    image_file_name: str
    image_group_name: str

    @classmethod
    async def as_form(
            cls,
            # 이미지 업로드 관련
            file: Union[UploadFile, None] = None,
            file_name: str = Form(None, alias='fileName'),
            image_group_name: str = Form(None, alias='imageGroupName'),
    ):
        if file:
            image_bytes: bytes = await file.read()
            # file_name 과 image_group_name는 안들어오면 기본값 (file객체.filename / '미분류')을 준다
            image_file_name: str = file_name if file_name else file.filename
            image_group_name: str = image_group_name if image_group_name else '미분류'
            return cls(
                image_bytes=image_bytes,
                image_file_name=image_file_name,
                image_group_name=image_group_name,
            )
        # 다른 schema의 as_form에서 Depends()로 사용될 때, file이 없으면 None으로 들어가게 한다.
        return None


class UserEditReq(BaseModel):
    username: Optional[str] = None
    description: Optional[str] = None

    upload_image_req: Optional[UploadImageReq] = None
    # image_bytes: Optional[bytes] = None
    # image_file_name: Optional[str] = None
    # image_group_name: Optional[str] = None

    @classmethod
    async def as_form(
            cls,
            username: str = Form(None),
            description: str = Form(None),

            upload_image_req: Optional[UploadImageReq] = Depends(UploadImageReq.as_form)
    ):
        return cls(
            username=username, description=description,

            upload_image_req=upload_image_req,
        )


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
    created_at: Optional[datetime.datetime] = None  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
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
    created_at: Optional[datetime.datetime] = None  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
    # Optional도 기본값을 줘야 -> Schema(**)시 기본값 입력이 되며, 안주면 에러가 난다.
    updated_at: Optional[datetime.datetime] = None

    post: Optional[PostSchema] = []  # 중간테이블에선 각각이 one이다.
    tag: Optional[TagSchema] = []
