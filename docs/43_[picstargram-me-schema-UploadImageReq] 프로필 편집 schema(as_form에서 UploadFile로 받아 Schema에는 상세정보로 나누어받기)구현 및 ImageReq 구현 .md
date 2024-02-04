- cookie 인증 유튜브: https://www.youtube.com/watch?v=EO9XWml9Nt0
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html
- ImageReq참고: https://github.dev/riseryan89/imizi-api/blob/main/app/middlewares/access_control.py


### me edit form hx-put -> route에서 User 수정하기
1. 일단 hx-post로 신호를 보내는데 put으로 바꿔준다.
    ```html
    
    <form hx-trigger="submit"
          hx-put="{{ url_for('pic_hx_edit_user') }}"
          hx-encoding="multipart/form-data"
    >
    ```
   
2. put route를 만들되, modal CRUD이므로, render()로 빈값 + message를 보내도록 일단 만든다
    ```python
    @app.put("/picstargram/users/edit", response_class=HTMLResponse)
    async def pic_hx_edit_user(
            request: Request,
            hx_request: Optional[str] = Header(None),
    ):
    
        context = {
            'request': request,
        }
        return render(request, "", context=context,
                      # hx_trigger=["postsChanged"],
                      messages=[Message.UPDATE.write("프로필", level=MessageLevel.INFO)]
                      )
    ```
   
3. 이제 req schema를 UserCreateReq + as_form을 참고해서만든다.
    - 다 nullable이라서 Form(...) 대신 Form(None)으로 기본값 None으로 form데이터를 받는다.

    ```python
    class UserEditReq(BaseModel):
        username: Optional[str] = None
        description: Optional[str] = None
        @classmethod
        async def as_form(
                cls,
                username: str = Form(None),
                description: str = Form(None),
        ):
            return cls(username=username, description=description,
    ```

4. route에서 받아준다.
    ```python
    @app.put("/picstargram/users/edit", response_class=HTMLResponse)
    async def pic_hx_edit_user(
            request: Request,
            user_edit_req: UserEditReq = Depends(UserEditReq.as_form)
    ):
        context = {
            'request': request,
        }
    
        print(f"user_edit_req  >> {user_edit_req}")
   
        return render(request, "", context=context,
                      # hx_trigger=["postsChanged"],
                      messages=[Message.UPDATE.write("프로필", level=MessageLevel.INFO)]
                      )
    ```
   

### form의 이미지 input file을 as_form에서 UploadFile type으로 받아서, 상세정보추출 나누어 schema에 생성

1. [imiziapp의 image_schema](https://github.dev/riseryan89/imizi-api/blob/main/app/middlewares/access_control.py)을 기반으로 하되, form이 아닌 json -> `image_base_64:str`를 받아서
    - **resize메서드내부 `Pil의 Image.open()`에 넣기까지의 과정이 `image = Image.open(BytesIO(base64.b64decode(image_base_64)))`의 과정인데**
    - 나의 경우, form -> `as_form` UploadFile => await file.read() -> `image_bytes:bytes`로 받기 때문에, `image = Image.open(BytesIO(image_bytes))`.의 과정이 남게 한다.
    - **추가로, image_file_name을 따로 받는데, 나의 경우, json이 아닌 form의 file_name이 안들어오는 경우, as_form에서 받은 UploadFile객체인 file객체에서 `.filename`를 default값을 채운다.**
    - **`image_bytes`(await file.read()) + `image_file_name`외 `image_group_name`이라고 카테고리name을 default `미분류`로 as_form에서 받는다.**
        - **추후 image_group_id가 form에서 select해서 날라와야할 듯하다.**

    ```python
    class UserEditReq(BaseModel):
        username: Optional[str] = None
        description: Optional[str] = None
    
        image_bytes: Optional[bytes] = None
        image_file_name: Optional[str] = None
        image_group_name: Optional[str] = None
    
        @classmethod
        async def as_form(
                cls,
                username: str = Form(None),
                description: str = Form(None),
    
                # 이미지 업로드 관련
                file: Union[UploadFile, None] = None,
                file_name: str = Form(None, alias='filename'),
                image_group_name: str = Form('미분류', alias='imageGroupName'),
    
        ):
    
            image_bytes = image_file_name = image_group_name = None
            if file:
                image_bytes: bytes = await file.read()
                # filename이 안들어오면 파일객체.filename으로
                image_file_name: str = file_name if file_name else file.filename
                # group_name이 안들어오면, '미분류'가 차있음
                image_group_name: str = image_group_name
    
            return cls(username=username, description=description,
                       image_bytes=image_bytes,
                       image_file_name=image_file_name,
                       image_group_name=image_group_name,
                       )
    
    ```
   


2. **UploadFile외 2개 nullable한 필드까지를 **`UploadImageReq`의 Optional Schema로 UserEditReq Schema가 Optional로 품을 수 있또록**, imiziapp을 참고해서, `UploadImageReq` schema로 따로 추출해서, 처리한다.**

### Form Schema에서 이미지를 업로드할 때 포함시키는 UploadImageReq Schema 추가하기.

1. as_form을 달고 있는 UserEditReq의 내부에는 `Optional[UploadImageReq] = None`을 추가해서 품고 있는다.
    ```python
    class UserEditReq(BaseModel):
        username: Optional[str] = None
        description: Optional[str] = None
        upload_image_req: Optional[UploadImageReq] = None
    
    ```
   
2. as_form()에서, `Depends(UploadImageReq.as_form)`를 통해 upload_image_req를 받을 수 있게 한다.
    ```python
    class UserEditReq(BaseModel):
        username: Optional[str] = None
        description: Optional[str] = None
        upload_image_req: Optional[UploadImageReq] = None
        
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
    ```
   

3. UploadImageReq에서는 기존 Upload처리를 하는 과정을 as_form에서 수행해서 form에서 input[type='file'] 등을 처리할 수 있게 한다.
    - 만약, UploadFile 객체가 안들어오면 None을 반환하여 -> UserEditReq에서 upload_image_req가 None이 되게 한다.
    ```python
    class UploadImageReq(BaseModel):
        image_bytes: bytes
        image_file_name: str
        image_group_name: str
    
        @classmethod
        async def as_form(
                cls,
                # 이미지 업로드 관련
                file: Union[UploadFile, None] = None,
                file_name: str = Form(None, alias='filename'),
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
    ```
   

4. **이제 route에서는 user_edit_req의 정보안에 `upload_image_req`정보가 있는지 파악하고 있을 때, 업로드로직을 추가한다.**
    ```python
    @app.put("/picstargram/users/edit", response_class=HTMLResponse)
    async def pic_hx_edit_user(
            request: Request,
            user_edit_req: UserEditReq = Depends(UserEditReq.as_form)
    ):
        context = {
            'request': request,
        }
    
        print(f"user_edit_req  >> {user_edit_req.username, user_edit_req.description}")
        if user_edit_req.upload_image_req:
            print(
                f"user_edit_req.upload_image_req  >> {user_edit_req.upload_image_req.image_file_name, user_edit_req.upload_image_req.image_group_name}")
        print(f"no upload image request.")
        # user_edit_req  >> ('444444444444', '4555')
        # user_edit_req.upload_image_req  >> ('htmx.gif', '미분류')
        # user_edit_req  >> ('user1', 'This is the description of user1.')
        # no upload image request.
    
        return render(request, "", context=context,
                      # hx_trigger=["postsChanged"],
                      messages=[Message.UPDATE.write("프로필", level=MessageLevel.INFO)]
                      )
    ```