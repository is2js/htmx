- cookie 인증 유튜브: https://www.youtube.com/watch?v=EO9XWml9Nt0 
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html


### create_user(\*\*data) 내부에서 password를 해쉬하여 hashed_password로 저장하기
#### 기존 프로젝트 참고하기
1. fastapi-users 
    - UserManager(생성시 model필요)내부의 password_helper를 사용하는데
    - fastapi_users.password에서 가져올 수 있다.
    - **내부에서 passlib.context의 `CrypContext`을 사용해서 처리한다.**
    ```python
    from app.common.config import JWT_SECRET, config, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    from fastapi_users.password import PasswordHelper, PasswordHelperProtocol
    
    class UserManager(IntegerIDMixin, BaseUserManager[Users, int]):
        reset_password_token_secret = JWT_SECRET
        verification_token_secret = JWT_SECRET
    
        def __init__(self, user_db: BaseUserDatabase[models.UP, models.ID],
                     password_helper: Optional[PasswordHelperProtocol] = None):
            super().__init__(user_db, password_helper)
    
        async def create(self, user_create: schemas.UC, safe: bool = False, request: Optional[Request] = None) -> models.UP:
            """
            Users 생성시, role 추가를 위해 재정의(user_dict)
            """
            # return await super().create(user_create, safe, request)
            await self.validate_password(user_create.password, user_create)
    
            existing_user = await self.user_db.get_by_email(user_create.email)
            if existing_user is not None:
                raise exceptions.UserAlreadyExists()
    
            user_dict = (
                user_create.create_update_dict()
                if safe
                else user_create.create_update_dict_superuser()
            )
            password = user_dict.pop("password")
            user_dict["hashed_password"] = self.password_helper.hash(password)
    ```
    ```python
    RESET_PASSWORD_TOKEN_AUDIENCE = "fastapi-users:reset"
    VERIFY_USER_TOKEN_AUDIENCE = "fastapi-users:verify"
    
    class BaseUserManager(Generic[models.UP, models.ID]):
    
        reset_password_token_secret: SecretType
        reset_password_token_lifetime_seconds: int = 3600
        reset_password_token_audience: str = RESET_PASSWORD_TOKEN_AUDIENCE
    
        verification_token_secret: SecretType
        verification_token_lifetime_seconds: int = 3600
        verification_token_audience: str = VERIFY_USER_TOKEN_AUDIENCE
    
        user_db: BaseUserDatabase[models.UP, models.ID]
        password_helper: PasswordHelperProtocol
        def __init__(
            self,
            user_db: BaseUserDatabase[models.UP, models.ID],
            password_helper: Optional[PasswordHelperProtocol] = None,
        ):
            self.user_db = user_db
            if password_helper is None:
                self.password_helper = PasswordHelper()
            else:
                self.password_helper = password_helper  # pragma: no cover
    ```
    ```python
    from passlib.context import CryptContext
    
    class PasswordHelper(PasswordHelperProtocol):
        def __init__(self, context: Optional[CryptContext] = None) -> None:
            if context is None:
                self.context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            else:
                self.context = context  # pragma: no cover
    
        def verify_and_update(
            self, plain_password: str, hashed_password: str
        ) -> Tuple[bool, str]:
            return self.context.verify_and_update(plain_password, hashed_password)
    
        def hash(self, password: str) -> str:
            return self.context.hash(password)
    
        def generate(self) -> str:
            return pwd.genword()
    
    ```

3. 이미지앱, auth_utils.py에서 bcrypt.hashpw() 모듈로 사용해서 hash 
    - User model에서 생성자에서 hash를 사용
    - 현재의 경우, create_user() 내부에서 사용하자.
    ```python
    import bcrypt
    from datetime import timedelta, datetime
    import jwt
    import random
    import string
    import base64
    import hmac
    from datetime import datetime
    
    from app.exceptions.excpetions import BadRequestException
    from config import get_env
    
    
    def create_token(data: dict, delta: int):
        conf = get_env()
        expire = datetime.utcnow() + timedelta(minutes=delta)
        payload = dict(exp=expire, **data)
        payload["iat"] = datetime.utcnow()
        payload["iss"] = "imizi api"
    
        return jwt.encode(payload, conf.JWT_SECRET_KEY, algorithm=conf.JWT_ALGORITHM)
    
    
    def decode_token(token: str):
        conf = get_env()
        try:
            payload = jwt.decode(token, conf.JWT_SECRET_KEY, algorithms=conf.JWT_ALGORITHM)
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("토큰이 만료되었습니다.")
        except jwt.InvalidTokenError:
            raise Exception("토큰이 유효하지 않습니다.")
    
    
    def hash_password(password: str):
        if 20 < len(password) or len(password) < 8:
            raise BadRequestException("패스워드의 길이는 8자 보다 길고 20자 보다 짧아야 합니다.")
        if not any(char.isdigit() for char in password):
            raise BadRequestException("패스워드에 최소한 1개 이상의 숫자가 포함되어야 합니다.")
        if not any(char.isupper() for char in password):
            raise BadRequestException("패스워드에 최소한 1개 이상의 대문자가 포함되어야 합니다.")
        if not any(char.islower() for char in password):
            raise BadRequestException("패스워드에 최소한 1개 이상의 소문자가 포함되어야 합니다.")
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    
    
    def is_valid_password(password: str, hashed_password: str):
        try:
            is_verified = bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
            return is_verified
        except Exception:
            return False
    
    
    def generate_random_string(length: int = 32):
        letters = string.ascii_letters + string.digits
        return "".join(random.choice(letters) for i in range(length))
    
    
    def parse_params_to_str(params: dict):
        url = "?"
        for key, value in params.items():
            url = url + str(key) + "=" + str(value) + "&"
        return url[1:-1]
    
    
    def hash_string(params: dict, secret_key: str):
        mac = hmac.new(
            bytes(secret_key, encoding="utf8"), bytes(parse_params_to_str(params), encoding="utf-8"), digestmod="sha256"
        )
        digest = mac.digest()
        validating_secret = str(base64.b64encode(digest).decode("utf-8"))
        return validating_secret
    
    
    def get_current_timestamp():
        return int(datetime.utcnow().timestamp())
    
    ```
    ```python
    class Users(Base):
    
        def __init__(self, email, pw, payplan_id=None, is_admin=False):
            self.email = email
            self.pw = hash_password(pw)
            self.payplan_id = payplan_id if payplan_id else 1
            self.is_admin = is_admin
    ```
4. 현재 유튜브 강의 Cookie Auth -> `from passlib.context import CryptContext`로 fastapi-users와 동일한 내부 모듈 사용
    - authSecurity.py에 정의 후, route에서 User모델 생성시 미리 hash하고 넣어줌.
    
    ```python
    from datetime import datetime, timedelta
    from fastapi import Depends, HTTPException, status, APIRouter
    from jose import jwt
    from passlib.context import CryptContext
    from controller import userController
    from sqlalchemy.orm import Session
    from typing import Union
    from database.connection import get_db
    from security.cookie import OAuth2PasswordBearerWithCookie
    from fastapi import Depends, APIRouter, Request, Response, status
    
    
    SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    COOKIE_NAME = "Authorization"
    
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="signin")
    
    authRouter = APIRouter()
    
    
    def get_password_hash(password):
        return pwd_context.hash(password)
    
    
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)
    
    
    def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    
    def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],)
        user: str = userController.get_user_by_username(
            db=db, username=payload.get("sub"))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user.username
    
    
    def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],)
        user: str = userController.get_user_by_username(db=db, username=payload.get("sub"))
        if user and user.is_Admin==True:
            return user.username
        else:
            raise HTTPException(status_code=302, detail="Not authorized", headers={"Location": "/signin"})
    ```
    ```python
    # oauth를 위한 cookie.py
    from typing import  Dict, Optional
    from fastapi.security import OAuth2
    from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
    from fastapi import Request,status,HTTPException
    from fastapi.security.utils import get_authorization_scheme_param
    from starlette.responses import RedirectResponse
    from fastapi.templating import Jinja2Templates
    
    templates=Jinja2Templates(directory="templates/")
    
    class OAuth2PasswordBearerWithCookie(OAuth2):
        def __init__(
            self,
            tokenUrl: str,
            scheme_name: Optional[str] = None,
            scopes: Optional[Dict[str, str]] = None,
            auto_error: bool = True,
        ):
            if not scopes:
                scopes = {}
            flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
            super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)
    
        async def __call__(self, request: Request) -> Optional[str]:
            authorization: str = request.cookies.get("access_token")  #changed to accept access token from httpOnly Cookie
    
            scheme, param = get_authorization_scheme_param(authorization)
            if not authorization or scheme.lower() != "bearer":
                if self.auto_error:
                  raise HTTPException(status_code=302, detail="Not authorized", headers = {"Location": "/signin"} )
                else:
                    return None
            return param
    ```
    ```python
    @userRouter.post("/signup")
    def create_new_user(request:Request,db:Session=Depends(get_db),form_data:OAuth2PasswordRequestForm=Depends()):
        db_user=userController.get_user_by_username(db=db,username=form_data.email)
        if db_user:
            error="E-mail already exist"
            return templates.TemplateResponse("auth/signup.html",{"request":request,"error":error},status_code=301)
        else:
            new_user=User(email=form_data.email,username=form_data.email,password=authSecurity.get_password_hash(form_data.password))
            user=userController.create_user(db=db,signup=new_user)
            return templates.TemplateResponse("auth/signin.html",{"request":request,"user":user},status_code=200)
    
    
    
    @userRouter.post("/signin", response_model=Token)
    def login_for_access_token(response:Response,request:Request,form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)): 
        user = userController.authenticate_user(
            db=db,
            username=form_data.email,
            password=form_data.password
        )
        if not user:
            error ="incorrect account Information "
            return templates.TemplateResponse('auth/signin.html',{"error":error, "request":request}, status_code=301)
    
        access_token_expires = timedelta(minutes=authSecurity.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = authSecurity.create_access_token(
            data={"sub": user.username,"role":user.is_Admin}, expires_delta=access_token_expires
        )
        response = RedirectResponse(url="/index",status_code=status.HTTP_302_FOUND)
    
        # to save token in cookie
        response.set_cookie(key="access_token",value=f"Bearer {access_token}", httponly=True) 
        return response
    ```
   


### hash_password by CryptContext -> 테스트 -> json에 hashed_password로 추가

#### 모듈 정의
1. utils에 auth.py를 만들고, `CryptContext`(공식 + fastapi-users)를 이용한 hash_password()메서드를 정의한다.
    - `passlib` 패키지를 설치한다.
    - **해당하는 backend인 `bcrypt`도 설치해야한다.**
        - MissingBackendError: bcrypt: no backends available -- recommend you install one (e.g. 'pip install bcrypt')
    - bcrypt 스킴으로 만들고, deprecated는 auto준다.
    ```python
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    
    def hash_password(password):
        return pwd_context.hash(password)
    
    
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)
    
    ```
#### 테스트 후, json 데이터에 hashed_password 필드 추가
1. shell.py에 import해서 테스트한다.
    ```python
    # shell.py
    import_target('utils/auth.py', '*')
    ```
    - python shell.py

    ```python
    hashed_password = hash_password("비밀번호")
    hashed_password
    # '$2b$12$x8SwiCONhbMOtHbXqAteo.ONtcgINfwv0wKn0S24/p4v2NWMvVHmi'
    verify_password("비밀번호", hashed_password)
    # True
    ```
   

2. user1, user2의 hashed_password를 만들어서, json에 추가한다.
    ```python
    hash_password("dbwj1")
    # '$2b$12$3T2KieEN5gZpNRyD8ni3c.FAQhEFzYbFKjG41NEeXpQ/Vt0nZML1u'
    hash_password("dbwj2")
    # '$2b$12$5AFZVL.yRMmNJeSPjFV9KOJ1T95tt/MxhaswTT0of0j4fuSbcVemS'
    ```
    ```json
    {
      "users": [
        {
          "id": 1,
          "email": "user1@gmail.com",
          "username": "user1",
          "hashed_password": "$2b$12$3T2KieEN5gZpNRyD8ni3c.FAQhEFzYbFKjG41NEeXpQ/Vt0nZML1u",
          "created_at": "2018-05-17 16:56:21",
          "updated_at": "2018-05-17 16:56:21",
          "image_url": "images/user1.png"
        },
        {
          "id": 2,
          "email": "user2@gmail.com",
          "hashed_password": "$2b$12$5AFZVL.yRMmNJeSPjFV9KOJ1T95tt/MxhaswTT0of0j4fuSbcVemS/Vt0nZML1u",
          "username": "user2",
          "created_at": "2019-05-17 16:56:21",
          "updated_at": "2019-05-17 16:56:21",
          "image_url": "images/user2.png"
        }
      ],
    ```
   
3. json필드추가에 따른, UserSchema에도 추가해주고, Req/Res에 필요하다면 추가해준다.
    ```python
    class UserSchema(BaseModel):
        id: Optional[int] = None  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
        email: str  # 추가
        hashed_password: str # 추가
        #...
    ```
   

### create_user() 메서드 내부에서 hashed_password로 저장하기
1. crud.py의 create_user() 수정
    - schema가 `**dict`를 받을 수 있게 `password`는 pop으로 삭제 / `hashed_password`는 생성해서 넣어준다.
    ```python
    def create_user(data: dict):
        # 해쉬해서 Schema(추후 model의 생성자)에 넣어주기
        password = data.pop('password')
        data['hashed_password'] = hash_password(password)
    
        try:
           
            user = UserSchema(**data)
            # id 부여
            user.id = find_max_id(users) + 1
            # created_at, updated_at 부여
            user.created_at = user.updated_at = datetime.datetime.now()
    
            users.append(user)
    
        except Exception as e:
            raise e
    
        return user
    ```
   
2. route에서 메세지 수정
    ```python
    @app.post("/picstargram/users/new")
    async def pic_new_user(
            request: Request,
            response: Response,
            hx_request: Optional[str] = Header(None),
            user_create_req: UserCreateReq = Depends(UserCreateReq.as_form),
    ):
        data = user_create_req.model_dump()
        # data  >> {'email': 'admin@gmail.com', 'username': 'user1', 'password': '321'}
    
    
        # 검증1: 중복여부(email, username)
        exists_email = get_user_by_email(data['email'])
        if exists_email:
            # return render(request, "", messages=[Message.FAIL.write('회원', text='이미 존재하는 email입니다.', level=MessageLevel.ERROR)])
            raise BadRequestException("이미 존재하는 email입니다")
        exists_username = get_user_by_username(data['username'])
        if exists_username:
            # return render(request, "",
            #               messages=[Message.FAIL.write('회원', text='이미 존재하는 username입니다.', level=MessageLevel.ERROR)])
            raise BadRequestException("이미 존재하는 username입니다.")
    
    
        # 실 생성
        user = create_user(data)
        context = {
            'request': request,
        }
    
        return render(request, "", context,
                      messages=[Message.CREATE.write(f'계정({user.email})')]
                      )
    ```