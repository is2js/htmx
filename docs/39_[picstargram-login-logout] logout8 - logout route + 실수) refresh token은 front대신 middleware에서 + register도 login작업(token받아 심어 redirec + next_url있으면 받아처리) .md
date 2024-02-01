- cookie 인증 유튜브: https://www.youtube.com/watch?v=EO9XWml9Nt0
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html

### logout route

1. fastapi-users에서는 `value=""`의 빈값삽입으로 삭제한다.
    ```python
     def _set_logout_cookie(self, response: Response) -> Response:
            response.set_cookie(
                self.cookie_name,
                "",
                max_age=0,
                path=self.cookie_path,
                domain=self.cookie_domain,
                secure=self.cookie_secure,
                httponly=self.cookie_httponly,
                samesite=self.cookie_samesite,
            )
            return response
    ```
   


2. 나는 redirect()메서드 안에 logout=True시, 각 토큰별로 cookie를 삭제하도록 했으니, redirect만 pic_index의 홈으로 이동시킨다.
    ```python
    @app.post("/picstargram/users/logout")
    async def pic_logout_user(
            request: Request,
    ):
    
        return redirect(request, request.url_for('pic_index'), logout=True)
    
    ```
   

3. base에 로그아웃 버튼을 추가한다.
    ```html
     <li>
        <a hx-get="{{ url_for('pic_hx_form') }}?user-login-or-register&next={{ request.query_params.get('next', '') }}" hx-target="#dialog">
            로그인/회원가입
        </a>
        <a hx-post="{{ url_for('pic_logout_user') }}">
            로그아웃
        </a>
    </li>
    ```
   

4. template에서 `request.state.user`에 있는 UserToken을 편하게 사용하기 위해서 render()안에서 context반영시 추가를 해준다.
    ```python
    def render(request, template_name="", context: dict = {}, status_code: int = 200,
               cookies: dict = None,
               delete_cookies: list = None,
               hx_trigger: dict | str | List[str] = None,
               messages: dict | List[dict] = None,
               oobs: List[tuple] = None,
               ):
        # 추가context가 안들어오는 경우는 외부에서 안넣어줘도 된다.
        ctx = {
            'request': request,
            'user': request.state.user,
            **context
        }
    ```
   
5. pic_index를 render()로 변경해준다
    ```python
    # return templates.TemplateResponse("picstargram/home/index.html", context)
    return render(request, "picstargram/home/index.html", context)
    ```
- 그래도 제대로 작성안한다. 로그인을 눌러도, request.state.user = UserToken을 넣는 작업은 @login_required에서 잘못 이루어지기 때문

### refresh token은 front대신 middleware에서
1. 함수를 수정하기 위해 Token에 None가능성을 위해 Optional을 추가한다.
    ```python
    class Token(BaseModel):
        
        # refresh 할 때, next token이 비워있을 수 있어서 nullable 
        access_token: Optional[str] = None
        refresh_token: Optional[str] = None
    ```
   

2. login_required에 있던 것을, middelware로 옮겨오되, set_user_token_to()를 `set_cookies_token_to`로 변경하고
    - return type을 access, refresh tuple에서, Token모델로 변경한다.
    ```python
    class AccessControl(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            headers = request.headers
            url = request.url.path
            ip = request.headers["x-forwarded-for"] if "x-forwarded-for" in request.headers.keys() else request.client.host
            request.state.ip = ip.split(",")[0] if "," in ip else ip
    
            request.state.user = None
    
            try:
                # check 'access_token', 'refresh_token'in cookies for login
                # if accessable or refreshable -> request.state.user <- UserToken
                # if access_token exp & refreshable -> new Token
                # if not accessable and not refreshable -> return None + request.state.user None
                new_token: Token = await set_cookies_token_to_(request)
    
                response = await call_next(request)
    
                if new_token:
                    await set_new_token_to(response, new_token)
    
                return response
    ```
       

3. 또한, **아래 token decode과정으로 변경한다.**
    1. `access_token 없으면` Token 모델대신 None ealry return
    2. **(access_token 존재) `try` access_token이 유효해서 decode되면 `refresh안하므로 None반환` + `로그인용 user_token 삽입`**
    3. **decode자체 에러 -> 로그인안됨 -> `access_token없는 것과 마찬가지 return None`**
    4. **(access_token 만료) `만료 except`에서 try refresh_token 유효해서 decode되면 `refresh해서 생긴 Token모델반환` + `로그인용 user_token 삽입`**
    5. **(refresh_token 만료 or 에러) `refersh만료는 access_token없는 것과 마찬가지 return None`**
    ```python
    async def set_cookies_token_to_(request: Request):
        """
        1. `access_token 없으면` Token 모델대신 None ealry return
        2. **(access_token 존재) `try` access_token이 유효해서 decode되면 `refresh안하므로 None반환` + `로그인용 user_token 삽입`**
        3. **decode자체 에러 -> 로그인안됨 -> `access_token없는 것과 마찬가지 return None`**
        4. **(access_token 만료) `만료 except`에서 try refresh_token 유효해서 decode되면 `refresh해서 생긴 Token모델반환` + `로그인용 user_token 삽입`**
        5. **(refresh_token 만료 or 에러) `refersh만료는 access_token없는 것과 마찬가지 return None`**
        """
        cookies = request.cookies
    
        access_token = cookies.get("access_token", None)
        refresh_token = cookies.get("refresh_token", None)
    
        if not access_token:
            return None
    
        try:
            access_token_info: dict = decode_token(access_token)
            request.state.user = UserToken(**access_token_info)
            return None
    
        except ExpiredSignatureError:
            try:
                refresh_token_info: dict = decode_token(refresh_token)
    
                user_id = int(refresh_token_info['sub'])
                user: UserSchema = get_user(user_id)
                next_token: dict = user.refresh_token(refresh_token, refresh_token_info['iat'])
    
                request.state.user = UserToken(**decode_token(next_token['access_token']))
    
                return Token(**next_token)
            except Exception:
                return None
    
        except Exception:
            return None
    
    
    # async def set_new_token_to(response, next_access_token, next_refresh_token):
    async def set_new_token_to(response, new_token: Token):
        if new_token.access_token:
            response.set_cookie('access_token', new_token.access_token, httponly=True)
        if new_token.refresh_token:
            response.set_cookie('refresh_token', new_token.refresh_token, httponly=True)
    
    ```
   
#### login_required는 request.state.user만 검사하고 안되면 redirect
```python
def login_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        
        if not request.state.user:
            response = redirect(
                request,
                path=request.url_for('pic_index').include_query_params(next=request.url),
            )
            return response

        return await func(request, *args, **kwargs)

    return wrapper
```


#### 회원가입도 login되도록, token발급 route갔다가, redirect로 cookies에 token 넣어서 로그인
```python
@app.post("/picstargram/users/new")
async def pic_new_user(
        request: Request,
        response: Response,
        hx_request: Optional[str] = Header(None),
        user_create_req: UserCreateReq = Depends(UserCreateReq.as_form),
):
    
    #...
    
    # return render(request, "", context,
    #               cookies=token,
    #               messages=[Message.CREATE.write(f'계정({user.email})')]
    #               )
    token: dict = await pic_get_token(request, UserLoginReq(**dict(email=user_create_req.email, password=user_create_req.password)))
    return redirect(request, request.url_for('pic_index'), cookies=token)
```

- 회원가입 form도 main페이지의 next=를 받아서 회원가입 -> 로그인적용 -> next_url로 이동하도록 한다.
    ```python
    @app.post("/picstargram/users/new")
    async def pic_new_user(
            request: Request,
            response: Response,
            hx_request: Optional[str] = Header(None),
            user_create_req: UserCreateReq = Depends(UserCreateReq.as_form),
            next_url: Union[str, bool] = Query(None, alias='next')
    ):
        #...
        
        token: dict = await pic_get_token(request, UserLoginReq(**dict(email=user_create_req.email, password=user_create_req.password)))
    
        if next_url:
            return redirect(request, next_url, cookies=token)
        
        return redirect(request, request.url_for('pic_index'), cookies=token)
    
    ```
  
- login_or_register_form.html에서 next를 직접 추가해준다.
    ```html
    <span class="selected"
              hx-get="{{ url_for('pic_hx_form') }}?user-login-body&next={{ request.query_params.get('next') }}"
              hx-target=".modal-body"
        >
            로그인
        </span>
        <span class="border-start border-2"
              hx-get="{{ url_for('pic_hx_form') }}?user-register-body&next={{ request.query_params.get('next') }}"
              hx-target=".modal-body"
        >
            회원가입
        </span>
    </span>
    ```
- 각 register_form들에도 추가해준다.
    ```html
    hx-post="{{ url_for('pic_new_user').include_query_params(next=request.query_params.get('next', '')) }}"
    ```