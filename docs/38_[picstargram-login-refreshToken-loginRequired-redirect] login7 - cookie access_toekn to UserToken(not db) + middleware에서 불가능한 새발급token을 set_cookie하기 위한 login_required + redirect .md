- cookie 인증 유튜브: https://www.youtube.com/watch?v=EO9XWml9Nt0
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html

### middleware에서 cookie decode후 UserToken schema로 로그인 처리되게 하기
1. request의 headers, cookies를 자주 쓰니 변수로 빼놓기
2. request.state.user 초기화하기
3. try 안에서 cookies에서 access_token 확인하여, try로 decode 후 **`ExpiredSignatureError`만 잡아서 refresh token을 처리한다**
    - `decode에 성공한 sub 등의 정보를 담은 dict`를 **db호출 전, 기본 로그인 확인용으로서 User를 대신할 UserToken Schema를 만들어서 정의해주기**
        - sub를 pydantic alias로 id로 받아서 꺼내 쓸 수 있다.
        - password등의 정보가 없으니, 기존 UserSchema에서 필요없는 것은 제외시킨다.
        - user객체대신 로그인용으로 쓰일 것이므로 email도 schema.get_token() 동본한다.
    ```python
    class UserToken(BaseModel):
        # id: int
        id: int = Field(alias='sub')
        email: EmailStr
        # hashed_password: str
        username: str
        image_url: Optional[str] = None
    ```
    - **try로 시도하고, ExpireSignatureError로 exp만료된 token만 except로 잡고, 나머지 e는 바깥쪽에서 잡히게 한다.**
    ```python
    class AccessControl(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            headers = request.headers
            cookies = request.cookies
            ip = request.headers["x-forwarded-for"] if "x-forwarded-for" in request.headers.keys() else request.client.host
            request.state.ip = ip.split(",")[0] if "," in ip else ip
    
            request.state.user = None
    
            try:
                if "access_token" in cookies.keys():
                    access_token = cookies.get("access_token")
                    refresh_token = cookies.get("refresh_token")
    
                    try:
                        access_token_info: dict = decode_token(access_token)
                        request.state.user = UserToken(**access_token_info)
    
                    except ExpiredSignatureError:
    
    ```
    - refresh_token도 exp되었는지 모르니 try안에서 decode -> 바깥에 try가 있으니 raise e 시켜서 에러가 걸리게 한다.
    - **refresh token까지 만료된다면, `로그인 검사==access_token 확인`를 안하는 페이지로 redirect나 render를 해야한다.**

#### refresh token 처리 과정

1. try 안에서 decode_token을 시도한다.
2. refresh_token_info:dict안에는 sub는 무조건 포함되어있어서 int()로 user_id를 만든다.
3. user_id로 db에서 user를 찾는다.
4. user model(현 schema)의 refresh_token메서드를 정의하여, access_token만 재발급한다.
    ```python
    class UserSchema(BaseModel):
        #...
        def refresh_token(self, refresh_token: str):
            "TODO: sqlalchemy User 모델 이관"
            return {
                "access_token": "Bearer " + create_token(
                    data=dict(
                        sub=str(self.id),
                        email=self.email,
                        username=self.username,
                        image_url=self.image_url,
                        # staff=self.is_admin),
                        # 그외 exp, iat iss는 create_token 내부에서
                    ),
                    delta=settings.access_token_expire_minutes,
                ),
                "refresh_token": refresh_token,
            }
    ```
   
5. **조건문에서 `now - iat(발행일)`이 만료기한이 아닌 `refresh의 만료기한/2를 넘긴상태`면, `refresh_token도` access_token과 `같이 재발급`시키기 위해 get_token메서드를 그대로 호출한다**
    ```python
    def refresh_token(self, refresh_token: str, iat: str):
        "TODO: sqlalchemy User 모델 이관"
        now = int(datetime.datetime.utcnow().timestamp())
        iat = int(iat)
        
        # refresh 발급기간이 만료기간(delta)의 1/2을 넘어선다면, refresh token도 같이 발급
        if now - iat >= settings.refresh_token_expire_minutes * 60 / 2:
            print(f"refresh의 1/2을 지나서, 둘다 재발급 ")
            return self.get_token() # refresh 절반이 지나면, 둘다 새로 발급
        # 아니라면, access_token만 재발급
        else:
            return {
                "access_token": "Bearer " + create_token(
                    data=dict(
                        sub=str(self.id),
                        email=self.email,
                        username=self.username,
                        image_url=self.image_url,
                        # staff=self.is_admin),
                        # 그외 exp, iat iss는 create_token 내부에서
                    ),
                    delta=settings.access_token_expire_minutes,
                ),
                "refresh_token": refresh_token,
            }
    
    ```
6. None으로 채워진 가변변수 next_accees_token, next_refresh_token을 선언해놓고
    - refresh 토큰 발급 -> sub -> user_id -> user객체(schema) -> .refresh_token -> Token(schema)
    - 기존 access_token과 발급받은 것이 다르면 next_token 가변변수에 채워주기
7. **재발급받은 next_access_token을 decode_token한 info를 `UserToken(**token_info)`로 만들어서, `request.state.user`에 넣어 `추후 router에서 로그인 여부`를 판단하는데 쓴다.**
    - **db의 유저객체를 매번 조회하지말고, UserToken을 쓰다가, 필요시 db에서 가져온다**
8. refrehs토큰도 만료되면, `로그인여부검사X 로그인 해야하는 곳`으로 추후 redirect시켜야한다.
    - 그외에 error는 raise e해준다.

9. **새로발급받은 token들은 cookie에 넣어줘야하는데, `response = await call_next(request)`로 route호출후 응답에다가 추가해준다.**
    - 이 때 가변변수가 None이 아니라 들어가있을때, set_cookie를 httponly로 넣어준다.
    ```python
    class AccessControl(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            headers = request.headers
            cookies = request.cookies
            ip = request.headers["x-forwarded-for"] if "x-forwarded-for" in request.headers.keys() else request.client.host
            request.state.ip = ip.split(",")[0] if "," in ip else ip
    
            request.state.user = None
    
            try:
                
                next_access_token = None
                next_refresh_token = None
                if "access_token" in cookies.keys():
                    access_token = cookies.get("access_token")
                    refresh_token = cookies.get("refresh_token")
    
                    try:
                        access_token_info: dict = decode_token(access_token)
                        request.state.user = UserToken(**access_token_info)
                        
                    except ExpiredSignatureError:
                        print(f"access_token 만료되어서 refresh token 사용")
                        try:
                            refresh_token_info: dict = decode_token(refresh_token)
    
                            user_id = int(refresh_token_info['sub'])
                            user: UserSchema = get_user(user_id)
    
                            next_token: dict = user.refresh_token(refresh_token, refresh_token_info['iat'])
    
                            next_access_token = next_token['access_token']
                            next_refresh_token = next_token['refresh_token'] if next_token['refresh_token'] != refresh_token \
                                else None
    
                            request.state.user = UserToken(**decode_token(next_access_token))
                            print(f"재발급과 동시에 login 완료 >> {request.state.user}")
                            print(f"next_access_token  >> {next_access_token}")
    
                        except ExpiredSignatureError:
                            # TODO: login 검사안하는 곳(home에 로그인검사안하도록 적용 후)으로 redirect
                            raise NotAuthorized('토큰이 만료되었습니다. 다시 시작해주세요.')
                        except Exception as e:
                            raise e
    
                response = await call_next(request)
                if next_access_token:
                    response.set_cookie('access_token', next_access_token, httponly=True)
                if next_refresh_token:
                    response.set_cookie('refresh_token', next_refresh_token, httponly=True)
                return response
            
            except Exception as e:
                # 템플릿 오류 -> oob render(status code 200<= <400 + 204제외만 oob swap)
                if isinstance(e, TemplateException):
                    return render(request, "",
                                  messages=[Message.FAIL.write('', text=f'{str(e)}', level=MessageLevel.ERROR)],
                                  )
                # 그외 오류
                else:
                    # return JSONResponse({"message": str(e)}, status_code=500)
                    raise e
    ```
   
10. test는 get_token메서드에서
    - delta를 `-` 달아서 access_token만료를 테스트한다.
    - refresh_token도 마찬가지로 `-`를 달아서 테스트한다.
    ```python
       def get_token(self):
            "TODO: sqlalchemy User 모델 이관"
            return {
                "access_token": "Bearer " + create_token(
                    data=dict(
                        sub=str(self.id),
                        email=self.email,
                        username=self.username,
                        image_url=self.image_url,
                    ),
                    delta= (-settings.access_token_expire_minutes), # test를 위해 -로 대입
                ),
                "refresh_token": "Bearer " + create_token(
                    data=dict(sub=str(self.id)), # 그외 exp, iat iss는 create_token 내부에서
                    delta=settings.refresh_token_expire_minutes,
                ),
            }
    ```
    
11. 메서드를 추출해서, 리팩토링한다.
    ```python
    class AccessControl(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            headers = request.headers
            ip = request.headers["x-forwarded-for"] if "x-forwarded-for" in request.headers.keys() else request.client.host
            request.state.ip = ip.split(",")[0] if "," in ip else ip
    
            request.state.user = None
    
            try:
                # set 로그인(UserToken)을 위한 request cookies token들 검사
                next_access_token, next_refresh_token = await self.set_user_token_to(request)
    
                response = await call_next(request)
                
                # token 만료시, 재발급되는 token들을 response cookies에 set
                await self.set_new_token_to(response, next_access_token, next_refresh_token)
                
                return response
    
            except Exception as e:
                # 템플릿 오류 -> oob render(status code 200<= <400 + 204제외만 oob swap)
                if isinstance(e, TemplateException):
                    return render(request, "",
                                  messages=[Message.FAIL.write('', text=f'{str(e)}', level=MessageLevel.ERROR)],
                                  )
                # 그외 오류
                else:
                    # return JSONResponse({"message": str(e)}, status_code=500)
                    raise e
    ```

### 모든 request를 로그인검사하지말자.
#### 특정 url을 제외하고 로그인검사 
1. 현재상태에서는 모든 static 요청들도 다 로그인 검사를 하게 된다.
    ```
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    INFO:     127.0.0.1:63587 - "GET /images/post-0004.jpeg HTTP/1.1" 200 OK
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    INFO:     127.0.0.1:63584 - "GET /js/hx_toast.js HTTP/1.1" 200 OK
    INFO:     127.0.0.1:63587 - "GET /js/hx_dialog.js HTTP/1.1" 200 OK
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    INFO:     127.0.0.1:63587 - "GET /picstargram/posts/show HTTP/1.1" 200 OK
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    INFO:     127.0.0.1:63587 - "GET /images/user1.png HTTP/1.1" 200 OK
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    INFO:     127.0.0.1:63584 - "GET /images/post-0001.jpeg HTTP/1.1" 200 OK
    INFO:     127.0.0.1:63583 - "GET /images/user2.png HTTP/1.1" 200 OK
    로그인 된 상태 UserToken >>  <class 'schemas.picstargrams.UserToken'>
    INFO:     127.0.0.1:63587 - "GET /images/post-0002.jpeg HTTP/1.1" 200 OK
    INFO:     127.0.0.1:63594 - "GET /manifest.json HTTP/1.1" 404 Not Found
    ```
   
2. utils/https.py에 url패턴체크 메서드를 정의한다.
    ```python
    async def url_pattern_check(path, pattern):
        result = re.match(pattern, path)
        return True if result else False    
    ```
   

3. `LOGIN_EXCEPT_PATH_REGEX`를 정규표현식으로 작성해준다.
    - `^( url1 | url2 | ...)`형식으로 특정 url(path)로 시작하면 로그인검사 제외다.
    ```python
    LOGIN_EXCEPT_PATH_REGEX = "^(/docs|/redoc|/static|/favicon.ico|/uploads|/auth|/api/v[0-9]+/auth)"
    ```
   
4. `await url_pattern_check(url, regex)`를 호출하여 `not`을 달면 login_required다.
    - flag변수를 만들어, `if login_rquired`일 때만 cookie검사를 하고, decode후, user_token을 request에 삽입 + 새로운 토큰을 response에 삽입한다.
    ```python
    login_required = not await url_pattern_check(url, LOGIN_EXCEPT_PATH_REGEX)
    
    try:
        if login_required:
            # set 로그인(UserToken)을 위한 request cookies token들 검사
            next_access_token, next_refresh_token = await self.set_user_token_to(request)
    
        response = await call_next(request)
    
        # token 만료시, 재발급되는 token들을 response cookies에 set
        if login_required:
            await self.set_new_token_to(response, next_access_token, next_refresh_token)
    
        return response
    ```
   

5. **이제 회원가입/로그인/로그아웃 route들을 모두 `/auth`를 붙혀서, cookie검사를 없앤다.**
    - login/register 할 땐, 로그인여부를 검사할 필요없다.
    - logout시에는 필요하지만, template에서 이미 if user로 판단해놓을 것이다.
    - **또한, `"/"`의 메인 또한 필요없다. 지금의 메인은 `"/picstargram"`이므로 `단독 검사`를 추가한다.**

    ```python
    app_name: str = "picstargram"
    LOGIN_EXCEPT_PATH_REGEX = f"^(/docs|/redoc|/static|/favicon.ico|/uploads|/auth|/api/v[0-9]+/auth|/{app_name}/auth)"
    
    
    class AccessControl(BaseHTTPMiddleware):
    
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            #...
            login_required = not await url_pattern_check(url, LOGIN_EXCEPT_PATH_REGEX) \
                             or (url != "/") or (url != f"/{app_name}")
    ```
   

#### 이런식으로하면, htmx요청 url들을 모두 직접 제외되어야한다. -> route별로 데코레이터로 처리하자.
- 인젝션을 하면 response에 set_cookie가 안되므로
- 데코레이터 -> return func()을 response = func()  + return response로 나눠서, set_cookie해보자.

1. root에 `decorators.py`에 login_required 데코레이터를 정의한다.
    - 내부에서 `await func(request, *args, **kawrgs)`를 호출할 때, route view function으로서 **파라미터가 일치해야한다.**
    ```python
    from functools import wraps
    
    from jose import ExpiredSignatureError
    from starlette.requests import Request
    from starlette.responses import RedirectResponse
    
    from crud.picstargrams import get_user
    from schemas.picstargrams import UserToken, UserSchema
    from utils.auth import decode_token
    
    
    def login_required(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                # 1) access_token가 있으면, 로그인 된 상태라고 판단 -> next토큰 2개 + request.state.user = UserToken()
                # 2) access_token이 없는 경우 -> None, None 반환 + request.state.user = None 상태
                next_access_token, next_refresh_token = await set_user_token_to(request)
            except ExpiredSignatureError:
                # 3) access_token이 있어도, refresh_token 만료 -> 직접 로그인하도록 redirect
                # TODO: obb로 메세지 + HX-Location으로 redirect?
                response = RedirectResponse(f"{request.url_for('pic_index')}?next={request.url}")
                return response
                # raise e # 이대로 두면, middleware에서 render하는데, modal용 noContent 트리거로만 간다?
    
            # 4) acess_token이 없어서 request.state.user = None상태 -> 직접 로그인하도록 redirect
            if not request.state.user:
                # TODO: login 페이지 GET route가 생기면 그것으로 redirect
                response = RedirectResponse(f"{request.url_for('pic_index')}?next={request.url}")
                return response
    
            response = await func(request, *args, **kwargs)
    
            # 5) access_token이 있지만, 만료되어 재발급 -> next_token들이 None, None 아니라면, response.set_cookie에 삽입
            await set_new_token_to(response, next_access_token, next_refresh_token)
    
            return response
    
        return wrapper
    
    ```

#### redirect요청이 hx요청이라면 RedirectResponse로 안되니, is_htmx를 판단해서 redirect해주는 메서드
1. 일반 redirect는 RedirectResponse로 / htmx request는 `headers에 HX-Redirect`로 해야한다.
    - 판단해주는 모듈을 https.py에 정의하고 redirect()메서드도 만든다.
    - logout시에는 무조건 redirect에 cookie에 token들을 지워야하니, 파라미터를 추가해주고
    - cookies: dict 파라미터를 추가해준다
    
    ```python
    def is_htmx(request: Request):
        return request.headers.get("hx-request") == 'true'
    
    
    def redirect(request: Request, path, cookies: dict = None, logout=False):
        is_request_htmx = is_htmx(request)
    
        # 1) htmx 요청 -> Response + 302 + HX-Redirect에 path
        if is_request_htmx:
            response: Response = Response(status_code=status.HTTP_302_FOUND)
            response.status_code = status.HTTP_302_FOUND
            response.headers['HX-Redirect'] = str(path) if not isinstance(path, str) else path
    
        # 2) 일반 요청 -> RedirectResponse
        else:
            response = RedirectResponse(path, status_code=status.HTTP_302_FOUND)
    
        if cookies:
            for k, v in cookies.items():
                response.set_cookie(key=k, value=v, httponly=True)
    
        if logout:
            # response.set_cookie(key='session_ended', value=str(1), httponly=True)
            response.delete_cookie('Authorization')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
    
        return response
    
    ```
   

2. login_required에 request를 받은 `redirect()`로 리다이렉트하도록 수정해준다.
    ```python
    def login_required(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                # 1) access_token가 있으면, 로그인 된 상태라고 판단 -> next토큰 2개 + request.state.user = UserToken()
                # 2) access_token이 없는 경우 -> None, None 반환 + request.state.user = None 상태
                next_access_token, next_refresh_token = await set_user_token_to(request)
                
            # refresh token까지 만료인 경우
            except ExpiredSignatureError:
                # 3) access_token이 있어도, refresh_token 만료 -> 직접 로그인하도록 redirect
                # response = RedirectResponse(f"{request.url_for('pic_index')}?next={request.url}")
                response = redirect(
                    request,
                    path=f"{request.url_for('pic_index')}?next={request.url}",
                )
    
                return response
                # raise e # 이대로 두면, middleware에서 render하는데, modal용 noContent 트리거로만 간다?
    
            # 4) acess_token이 없어서 request.state.user = None상태 -> 직접 로그인하도록 redirect
            if not request.state.user:
                response = redirect(
                    request,
                    path=f"{request.url_for('pic_index')}?next={request.url}",
                )
    
            response = await func(request, *args, **kwargs)
    
            # 5) access_token이 있지만, 만료되어 재발급 -> next_token들이 None, None 아니라면, response.set_cookie에 삽입
            await set_new_token_to(response, next_access_token, next_refresh_token)
    
            return response
    
        return wrapper
    ```
   
3. **로그인이 필요한 곳에서 로그인이 안되어 redirect할 땐, 해당 `request.url`을 `next=`의 쿼리파라미터를 달아서 redirect시켜주는게 좋다**
    - 이 [스택오버플로우](https://stackoverflow.com/questions/70656412/how-to-redirect-to-dynamic-url-inside-a-fastapi-endpoint)에서 `.include_query_params()`메서드로 처리할 수 있게 알려줬다.
    - request.url_for()에 체이닝으로 호출해주면 된다.
    ```python
    # path=f"{request.url_for('pic_index')}?next={request.url}",
    path=request.url_for('pic_index').include_query_params(next=request.url),
    ```

#### 로그인 페이지 없는 htmx modal login 때문에 복잡해진 next_url
1. **next의 query_param은 login route에서 받아줘서, 있으면 render가 아니라, redirect시킨다.**
    - **이 때, next:str = None 대신, `next_url: str = Query(None, alias="next")`로 python 빌드인 next와 겹치지 않게 한다**
    - redirect시킬 때는 cookies에 로그인과정에서 얻은 token dict를 넣어준다.
    ```python
    @app.post("/picstargram/users/login")
    async def pic_login_user(
            request: Request,
            user_login_req: UserLoginReq = Depends(UserLoginReq.as_form),
            next_url: str = Query(None, alias='next')
    ):
        token: dict = await pic_get_token(request, user_login_req)
    
        context = {
            'request': request,
        }
    
        if next_url:
            return redirect(request, next_url, cookies=token)
    
        return render(request, "", context,
                      cookies=token,
                      messages=[Message.CREATE.write(entity=f"유저", text="로그인에 성공했습니다.")]
                      )
    ```
   
2. 현재 `@login_required`에 의해,  main페이지에 ?next=가 들어가게 되는데, **문제는 `로그인요청은 modal의 내부 form에서 발생`한다**
    - main페이지의 next는 못가져오고 main -> hx modal을 채우는 요청의 request를 파싱하게 된다.
    - **main -> modal 띄울 때 next를 파싱해서 같이 넘겨줘야한다.**
    - **request 파싱은 [여기](https://stackoverflow.com/questions/70477787/how-to-get-current-path-in-fastapi-with-domain)를 참고하자.**
    ```
    domain = request.base_url
    path = request.url.path
    query_params = request.query_params
    value = request.query_params.get('key')
    ```
  - 이 때, 로그인 페이지가 아니라, `메인페이지?next=` 내부의 `모달로 form`을 쏘기 때문에 `login 쏘는 modal의 hx-post`에서 들어가야한다.


3. base.html에서 form name외에 next=를 추가해서 modal 요청을 보내게 한다.
    - `{{ request.query_params.get('next') }}`를 활용한다.
    ```html
    <li>
        <a hx-get="{{ url_for('pic_hx_form') }}?user-login-or-register&next={{ request.query_params.get('next') }}"
           hx-target="#dialog">
            로그인/회원가입
        </a>
    </li>
    ```
   

4. form body를 넘겨주는 route에서는 next를  next_url로 받는다. like 로그인 라우터
    - **이 때, htmx 부분html을 넘겨주는 response라서, main페이지의 next=를 추출못하는 상황이다**
    - **request.query_params는 .get()만 존재하고 set은 없는데, `.__setattr__()`을 이용해서 next= 쿼리파람을 강제로 추가한다.**
    ```python
    @app.get("/picstargram/form", response_class=HTMLResponse)
    async def pic_hx_form(
            request: Request,
            next_url: str = Query(None, alias='next')
    ):
        # htmx modal body반환인데, 내부 ?next=를 넘겨서, [main페이지의 next=를 추출못하는 상황]에서 로그인 form에서 next를 추출할 수 있게 한다
        request.query_params.__setattr__('next', next_url)
        context = {
            'request': request,
        }
    
        
        qp = request.query_params
        # qp  >> post-create=
    
        if any(name in qp for name in ['post-create', 'post_create']):
            return templates.TemplateResponse("picstargram/post/partials/create_form.html", context)
        elif any(name in qp for name in ['user-register', 'user_register']):
            return templates.TemplateResponse("picstargram/user/partials/register_form.html", context)
        elif any(name in qp for name in ['user-login', 'user_login']):
            return templates.TemplateResponse("picstargram/user/partials/login_form.html", context)
    
        elif any(name in qp for name in ['user-login-or-register', 'user_login_or_register']):
            return templates.TemplateResponse("picstargram/user/partials/login_or_register_form.html", context)
        elif any(name in qp for name in ['user-login-body', 'user_login_body']):
            return templates.TemplateResponse("picstargram/user/partials/login_or_register_form_login_part.html", context)
        elif any(name in qp for name in ['user-register-body', 'user_register_body']):
            return templates.TemplateResponse("picstargram/user/partials/login_or_register_form_register_part.html",
                                              context)
        else:
            return '준비되지 않은 modal입니다.'
    ```
   

5. 이제 modal body 중 login part들에서, {{request.query_params.get('next')}}를 next가 있을때만 추출하여, login route로 hx-post보낸다.
    - **하지만, front에서 next=None(python)이 string "None"으로 들어가기 때문에, route에서 존재하는 것으로 판단하기 때문에, `.get('next', '')`으로 입력한다.**
    ```html
    <a hx-get="{{ url_for('pic_hx_form') }}?user-login-or-register&next={{ request.query_params.get('next', '') }}"
       hx-target="#dialog"
    >
        로그인/회원가입
    </a>
    ```
    ```html
    <form hx-trigger="submit"
          hx-post="{{ url_for('pic_login_user').include_query_params(next=request.query_params.get('next', ''))}}"
          {#hx-encoding="multipart/form-data" #}
    >
    ```
   
6. login form을 붜오는 모든 hx-get / hx-post는 next처리 해준다.
 

### 페이지 라우터에 거는 @login_required는 일반 요청 ->hx 요청이 아니면 messages(toast)를 담당하는 oob 또는 hx-trigger로 loginModal 오픈이 안된다.
1. login_required내부에서 hx request인지 확인해야하는데, route의 파라미터 `hx_request: Optional[str] = Header(None)`를 쓸 수 없으니, 
    - **직접 headers에서 꺼내서 확인하는 함수를 만든다. `request.headers`에서 get으로 꺼내고, javascript의 lower `true` string를 가지고 판단한다**
    ```python
    def is_htmx(request: Request):
        return request.headers.get("hx-request") == 'true'
    ```
   

2. 내부에서는 is_htmx일때만, error toast를 render()해주는 TemplateException을 raise한다.
    ```python
    def login_required(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not request.state.user:
                if is_htmx(request):
                    raise NotAuthorized('로그인이 필요합니다.')
                else:
                    response = redirect(
                        request,
                        path=request.url_for('pic_index').include_query_params(next=request.url),
                    )
                    return response
        return wrapper
    ```
   
### modal을 띄우는 hx-request에서 toast는 뜨는데 modal이 noContent가 hx-response로 가는데도 안닫힌다?
#### 문제점
1. is_htmx request로서 render("")로 hx-trigger noContent가 포함되지만, `modal.hide()가 먹히지 않는다`?
2. **hx_dialog.js를 살펴보니**
    - noContent에 대한 htmx.on은 바로 작동한다.
    ```js
    htmx.on("noContent", (evt) => {
        const currentModal = bootstrap.Modal.getInstance(modalElement)
        // if (currentModal && modalElement.classList.contains("show")) {
        if (currentModal || modalElement.classList.contains("show")) {
            currentModal.hide();
        }
    ```
   - **하지만, modal을 띄우는 `.show()`는, `hide()가 작동하는 시점(htmx.on - hx-trigger)`보다 더 이후인 `htmx.on( afterSwap )`에서 작동하기 때문에**
       - **modal.hide() 가 먼저 작동 -> swap -> modal.show() 순서로 작동되기 때문이다.**
```js
// modal이 열리는 것은 response -> swap완료(html교체) -> modal show
htmx.on('htmx:afterSwap', function (evt) {
    if (evt.detail.target.id === 'dialog') {
        const currentModal = bootstrap.Modal.getInstance(modalElement)
        currentModal.show();
    }
// modal이 닫히는 것은 response -> hx-trigger -> modal hide 
htmx.on("noContent", (evt) => {
    const currentModal = bootstrap.Modal.getInstance(modalElement)
    if (currentModal && modalElement.classList.contains("show")) {
        currentModal.hide();

    }
}
// => afterSwap보다 먼저 작동하여, [클릭 -> response -> hx-trigger modal hide -> swap -> afterSwap: modal hide]로
// => response시 닫아라고 명령했는데, 열리는 것보다 먼저 닫히는 동작을 수행하여
// => 계속 열려있게 된다.    

```

#### 해결법
1. 모달이 열리는 동작(afterSwap)은, 닫히는 동작(trigger)에 비해에 늦으니
    - **닫히는 동작일 땐, 먼저 작동하는 hide 대신, `뒤늦게 show가 안되도록 미리 modal객체를 dispose`를 미리하고**
    - **평상시 show 동작은 dispose되서, modal객체가 존재하지 않으면 -> (열여선안되겠다) 판단하고, show는하지말고, 다시 살려두기만**
    - 다시 살려둬야, 닫히는 동작없는 열리는 동작에선 바로 show를 할 것이다.
2. 이 때, 더이상 **`.show`를 닫히는 조건을 동시에 주면 안된다..**
    - 열리는 것(느림) 동`작 따로 `-> 닫히는 `동작 따로`(빠름.but 다른 동작 ex> submit or 취소)가 구분되어있었지만
    - **이제부터는 열림과 동시에 닫아야하는데, 동시작동할 땐, .show가 안붙은 상황에서는 닫기(dispose)를 해야하기 때문이다.**
3. **즉, 닫아야하는 `noContent trigger`가 들어왔을 때,**
    - **이전 동작에서 이미 show(느림)을 미리 해놓았다면 ex> 모달열어서 submit/cancel 대기 -> `.show` 확인 후, `modal.hide()`만**
    - **이전 동작에서 show하는게 아니라, 열림과 동시에 닫힘해야한다면, ex> 로그인필요하여 안열여야함. -> 동시 동작에서는 열리는게 느려 `.show가 없음`을 확인 후 `modal.dispose()`로 열리는것 미리 막기**

    ```js
    const modalElement = document.getElementById('modal');
    let modal = new bootstrap.Modal(modalElement);
   
    htmx.on("noContent", (evt) => {
        // 초기화 / show에서 이미 modal객체를 생성해놨는데, 혹시나 오류에 의해 객체가 없을 수 있으니
        // 없으면 생성해서 modal객체 무조건 획득은 상태
        modal = bootstrap.Modal.getOrCreateInstance(modalElement)
        
        if (modalElement.classList.contains("show")) {
            // 1) 열림(느리지만 이전) -> 닫힘(빠름)이 구분동작여서 이미 열려있다면
            //  -> 닫기만
            modal.hide();
        } else {
            // 2) 열림->닫힘 동시동작인데, 느린 열람 때문에, 닫기에서 미리 못열리게 hide대신 dispose로 안열리게, modal객체 소멸시키기
            //    -> 열려고 할 때, modal객체가 dispose로 죽어있으면, 살리기만 하고 끝나서 안열린다.
            modal.dispose();
        }
    ```
    ```js
    htmx.on('htmx:afterSwap', function (evt) {
        if (evt.detail.target.id === 'dialog') {
                modal = bootstrap.Modal.getInstance(modalElement)
                if (modal) {
                    // 1) 열림과 동시에 닫힘이 아니라면, dipose안되어있으니, 열기만
                    modal.show();
                } else {
                    // 2) 열림과 동시에 닫혀야해서, 먼저 일어나는 닫기에서 hide대신 dispose로 막나왔으면
                    // -> 다음 열림을 위해 modal객체 생성만 해두기
                    modal = new bootstrap.Modal(modalElement);
                }
            }
    ```