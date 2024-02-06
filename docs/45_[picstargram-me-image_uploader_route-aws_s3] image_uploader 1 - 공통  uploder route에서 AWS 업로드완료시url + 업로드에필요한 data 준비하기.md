- cookie 인증 유튜브: https://www.youtube.com/watch?v=EO9XWml9Nt0
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html
- ImageReq참고: https://github.dev/riseryan89/imizi-api/blob/main/app/middlewares/access_control.py
- aws s3세팅 참고: https://www.youtube.com/watch?v=uqxBsCKW6Gs

### form Schema 내부 UploadImageReq를 pop한 뒤, 공통 upload route에 Schema로 재변환해서 보내서 처리되게 하기

1. upload_image_req (dump결과 dict)를 pop 해놓고, uploader route에 보낼 때는, Schema(\*\*dict)로 재변환해서 Schema로 넣어주기
    - uploader route의 파라미터는 Schema여야하기 때문.
    ```python
    @app.put("/picstargram/users/edit", response_class=HTMLResponse)
    async def pic_hx_edit_user(
            request: Request,
            user_edit_req: UserEditReq = Depends(UserEditReq.as_form)
    ):
        data = user_edit_req.model_dump()
        
        # model_dump()시  내부 포함하는 schema UploadImageReq도 dict화 된다. -> 다른 route로 보낼 수 없음.
        # {..., {'upload_image_req': {'image_bytes': '', 'image_file_name': 'bubu.png', 'image_group_name': '미분류'}}
        # -> user모델 데이터가 아닌 것으로서, 미리 pop으로 빼놓기
        upload_image_req: dict = data.pop('upload_image_req')
        
        # ...
        
        if upload_image_req:
            # pop해놓은 dict를 다시 Schema로 감싸서 보내기
            print(await pic_uploader(request, UploadImageReq(**upload_image_req)))
        # ...
    ```

2. uploader route 정의하되, UploadImageReq를 Schema로 받기. for API
    ```python
    @app.post('/uploader')
    async def pic_uploader(
            request: Request, 
            upload_image_req: UploadImageReq
    ):
        data = upload_image_req.model_dump()
        image_group_name = data['image_group_name']
        image_file_name = data['image_file_name']
        image_bytes = data['image_bytes']
        # ...
    ```

### 공통 Uploader에서 이미지 처리하기

#### image_bytes + PIL로 원본 이미지 size, extension 추출하기

1. upload_image_req Schema 속 `image_bytes`를 `BytesIO()`에 넣어 `_io.BytesIO`를 만들어야 -> PIL의 Image.open() 에 넣을 수 있다.
    - **image객체 `.size`, `.format`으로 image_size, image_extension을 추출한다.**
    ```python
    1. @app.post('/uploader')
    async def pic_uploader(
            request: Request,
            upload_image_req: UploadImageReq
    ):
        data = upload_image_req.model_dump()
        image_group_name = data['image_group_name']
        image_file_name = data['image_file_name']
        image_bytes = data['image_bytes']
    
        # 1) 원본 image객체 만들기
        try:
            image = Image.open(BytesIO(image_bytes))
        except UnidentifiedImageError:
            raise ValueError("Invalid Image")
   
        image_size = image.size  # (357, 343)
        image_extension = image.format  # PNG
    ```


2. size와 extension을 추출하는 부분을 `utils/images.py`로 메서드 추출한다.
    ```python
    async def get_image_size_and_ext(image_bytes: bytes) -> tuple:
        try:
            image = Image.open(BytesIO(image_bytes))
        except UnidentifiedImageError:
            raise ValueError("Invalid Image")
        # 2) 원본 size + ext 추출
        image_size = image.size  # (357, 343)
        image_extension = image.format  # PNG
        return image_size, image_extension
    ```

#### thumbnail image객체 + file_size 추출하기

1. image_bytes를 이용해 새롭게 원본 image객체를 다시 만들어낸 뒤,
    1. **정사각형 image객체를, w!=h일시 crop하여 만들고**
    2. 임의의 thumbnail size로 resize한 image객체로 변환 후
    3. 빈 buffer + image.save(, format="webp") -> buffer.getvalue()+len()으로 file_size를 구한다
    ```python
        # 1) image_bytes -> BytesIO+Image.open() -> image객체
        # -> 원본 image size + ext 추출
        image_size, image_extension = await get_image_size_and_ext(image_bytes)
    
        # 2) 정사각형으로 crop -> thumbnail image 객체 -> .save()를 이용해
        #    -> webp포맷 thumbnail의 buffer + file_size 추출
        image = Image.open(BytesIO(image_bytes))
        # 3-1) 정사각형 아닐 경우, w or h 짧은 쪽기준으로 crop하여 [정사각형 image객체] 만들기
        #    w > h 인 경우, top0,bottom:h로 다쓰고, 좌우는 w-h/2, w+h/2로 긴 w를 중점으로 h만큼간 절반으로 잡아 crop한다.
        #    h > w 인 경우,  left0,right:w로 다쓰고, 반대로 간다.
        #    w == h 인 경우, 그대로 둔다.
        width, height = image.size
        if width != height:
            if width > height:
                left = (width - height) / 2
                right = (width + height) / 2
                top = 0
                bottom = height
            # elif width < height:
            else:
                left = 0
                right = width
                top = (height - width) / 2
                bottom = (height + width) / 2
    
            image = image.crop((int(left), int(top), int(right), int(bottom)))
    
        # 3-2) 원본crop 정사각형 image객체 -> thumbnail image객체로 변환
        thumbnail_size = (200, 200)
        image = image.resize(thumbnail_size)
        # 3-3) thumbnail image객체 -> [format='webp'로 image.save()]를 빈 BytesIO에 할당하여
        #                             thumbnail_buffered를 만들어야, file_size를 추출할 수 있다.
        #      buffer + image.save() -> buffer.get_value()  + len()으로 file_size 추출
        thumbnail_buffered = BytesIO()
        image.save(thumbnail_buffered, format='WEBP')
        thumbnail_file_size = len(thumbnail_buffered.getvalue())  # 8220
    
        # print(f"thumbnail_buffered  >> {thumbnail_buffered}")
        # print(f"thumbnail_file_size  >> {thumbnail_file_size}")
    ```


2. method로 추출하여 get_thumbnail_buffer_and_file_size()로 호출해준다.
    - 이 때, thumbnail_size는 keyword기본값으로 줘서, 외부 입력 가능토록 하자
    ```python
    async def get_thumbnail_image_obj_and_file_size(
            image_bytes,
            thumbnail_size=(200, 200)
    ):
        image = Image.open(BytesIO(image_bytes))
        # 3-1) 정사각형 아닐 경우, w or h 짧은 쪽기준으로 crop하여 [정사각형 image객체] 만들기
        #    w > h 인 경우, top0,bottom:h로 다쓰고, 좌우는 w-h/2, w+h/2로 긴 w를 중점으로 h만큼간 절반으로 잡아 crop한다.
        #    h > w 인 경우,  left0,right:w로 다쓰고, 반대로 간다.
        #    w == h 인 경우, 그대로 둔다.
        width, height = image.size
        if width != height:
            if width > height:
                left = (width - height) / 2
                right = (width + height) / 2
                top = 0
                bottom = height
            # elif width < height:
            else:
                left = 0
                right = width
                top = (height - width) / 2
                bottom = (height + width) / 2
    
            image = image.crop((int(left), int(top), int(right), int(bottom)))
        # 3-2) 원본crop 정사각형 image객체 -> thumbnail image객체로 변환
    
        image = image.resize(thumbnail_size)
        # 3-3) thumbnail image객체 -> [format='webp'로 image.save()]를 빈 BytesIO에 할당하여
        #                             thumbnail_buffered를 만듦.
        #      buffer + image.save() -> buffer.get_value()  + len()으로 file_size 추출
        thumbnail_buffered = BytesIO()
        image.save(thumbnail_buffered, format='WEBP')
        thumbnail_file_size = len(thumbnail_buffered.getvalue())  # 8220

        return image, thumbnail_file_size
    
    ```

    ```python
    @app.post('/uploader')
    async def pic_uploader(
            request: Request,
            upload_image_req: UploadImageReq
    ):
        data = upload_image_req.model_dump()
        image_group_name = data['image_group_name']
        image_file_name = data['image_file_name']
        image_bytes = data['image_bytes']
    
        # 1) image_bytes -> BytesIO+Image.open() -> image객체
        #    -> 원본 image size + ext 추출
        image_size, image_extension = await get_image_size_and_ext(image_bytes)
    
        # 2) 정사각형으로 crop -> thumbnail image 객체 -> .save()를 이용해
        #    -> webp포맷 thumbnail의 buffer + file_size 추출
        thumbnail_image_obj, thumbnail_file_size = await get_thumbnail_image_obj_and_file_size(
            image_bytes,
            thumbnail_size=(200, 200)
        )
    ```

#### 정해진 size들을 돌면서, 정해진 width를 넘어서는 원본은 ratio유지하여 정해진size로 resize한 뒤, dict에 size별 image_obj + file_size 누적하여 모으기
1. 일단 thumbnail의 buffer와 file_size를 `size별 image객체 dict`와 `누적 file_size` 변수에 넣어두고 
2. 정해진 image_convert_sizes들[512, 1024, 1920]을 순회하며,
    - 원본이미지의 width, 해당size보다 클 때마다 ratio유지하며 image.resize()한 image객체 + file_size를 추출하여, 누적변수들에 모아둔다.
    - ex> 원본 (300, 400) -> w 512보다 작음 -> 누적없이 `thumbnail로 끝` -> **업로드는 `thumbnail`만 된다.**
    - ex> 원본 (600, 400) -> w 512보다 큼 -> ratio유지하며 resize하여 `512`에 대한 image객체 + file_size추출 -> 누적변수에 추가
    - ex> 원본 (1500, 400) -> w 512, 1024보다 큼 -> ratio유지하며 resize하여 `512`, `1024`에 대한 buffer + file_size추출 -> 누적변수에 추가
    ```python
        # 3) 정해진 size들을 돌며, thumbnail외 그것보다 큰 것이 나타나면 ratio유지한 resize하여 
        #  -> image객체를 dict에 size별로 모으기 + file_size는 total 누적
        #  -> 사이즈가 커서, 여러size를 resize하면, total_file_size에 누적
        image_objs_per_size = dict(thumbnail=thumbnail_image_obj)
        total_file_size = thumbnail_file_size
    
        image_convert_sizes = [512, 1024, 1920]
        for convert_size in image_convert_sizes:
            # 원본 width가 정해진 size보다 클 때만, ratio resize 후 추가됨.
            # -> 512보다 작으면 only thumbnail만 추가된다.
            if image_size[0] > convert_size:
                current_image = Image.open(BytesIO(image_bytes))
                
                # 정해진 해당size로 resize
                current_width, current_height = image_size
                ratio = current_width / current_height
                current_image = current_image.resize((convert_size, int(convert_size / ratio)))
                
                # webp포맷으로 inplace후, file_size추출
                convert_buffered = BytesIO()
                current_image.save(convert_buffered, format="WEBP")
                current_image_file_size = len(convert_buffered.getvalue())
            
                # 누적변수2개에 각각 추가
                image_objs_per_size[convert_size] = current_image
                total_file_size += current_image_file_size
                total_file_size += len(convert_buffered.getvalue())
    
        print(f"images  >> {image_objs_per_size}")
        print(f"total_file_size  >> {total_file_size}")
    ```
   
2. **여기서는 resized_image_obj + file_size를 추출해주는 부분만 method로 추출한다.**
    - bytes + 변환시킬 w,h의 size를 받아서 처리되게 한다.
    - 원본크기인 image_size는 bytes -> Image.open()에서 추출될 수 있다.
    ```python
    async def resize_and_get_image_obj_and_file_size(image_bytes, convert_size):
        current_image = Image.open(BytesIO(image_bytes))
        
        # 정해진 해당size로 resize
        current_width, current_height = current_image.size
        ratio = current_width / current_height
        current_image = current_image.resize((convert_size, int(convert_size / ratio)))
        
        # webp포맷으로 inplace후, file_size추출
        convert_buffered = BytesIO()
        current_image.save(convert_buffered, format="WEBP")
        current_image_file_size = len(convert_buffered.getvalue())
        
        return current_image, current_image_file_size
    ```
    ```python
    # 3) 정해진 size들을 돌며, thumbnail외 그것보다 큰 것이 나타나면 ratio유지한 resize하여 
    #  -> image객체를 dict에 size별로 모으기 + file_size는 total 누적
    #  -> 사이즈가 커서, 여러size를 resize하면, total_file_size에 누적
    image_objs_per_size = dict(thumbnail=thumbnail_image_obj)
    total_file_size = thumbnail_file_size
   
    image_convert_sizes = [512, 1024, 1920]
    for convert_size in image_convert_sizes:
        # 원본 width가 정해진 size보다 클 때만, ratio resize 후 추가됨.
        # -> 512보다 작으면 only thumbnail만 추가된다.
        if image_size[0] > convert_size:
            resized_image, resized_file_size = await resize_and_get_image_obj_and_file_size(
                image_bytes,
                convert_size
            )

            # 누적변수2개에 각각 추가
            image_objs_per_size[convert_size] = resized_image
            total_file_size += resized_file_size
    ```
   

#### image_objs_per_size를 순회하며 db저장용 size별 s3_업로드완료_url dict + s3 upload를 위한 data dict 만들기
1. uuid4()를 이용하여, `파일명_size.webp` 중 파일명을 차지하게 할 것이다.
    - **s3에는 uuid4_size로 파일명을 구성하고, `image모델객체`에 db저장은 따로 `file_name필드`에 UploadImageReq.image_file_name을 사용할 예정이다.**
    - uuid외, s3업로드완료url을 구성하려면 `AWS_BUCKET_NAME`과 `AWS_REGISON`이 따로 필요하다.

2. image_objs_per_size dict를 .items()로 순회하며 size -> file명 / image객체 -> upload용 데이터로, 완료/업로드용 url을 구성해야한다.
    - `f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_group_name}/{uuid}_{size}.webp"`로 완료 url을 구성한다.
    - upload용 데이터는 image_obj + image_group_name + image_file_name 3개를 dict에 size별로 모은다.
    ```python
        # 4) (1)업로드완료가정 접속url size별dict + (2)업로드에 필요한 데이터 size별dict
        #    (1) s3_urls_per_size: [DB에 size(key)별-저장될 s3_url(value) 저장할 JSON]정보 넣기
        #    (2) to_s3_upload_data_per_size: s3업로드에 필요한 size별-[image객체] + [image_group_name] + [uuid_size.webp의 업로드될파일명] 정보 넣기
        uuid = str(uuid4())  # for s3 file_name
        AWS_BUCKET_NAME = "" # for s3 url
        AWS_REGION = ""
    
        s3_urls_per_size = {}  # for db-json 필드: size별 s3 upload완료되고 접속할 주소들
        to_s3_upload_data_per_size = {}  # for s3 upload: size별 업로드에 필요한 데이터 1) image_obj, 2) 부모폴더명 3) 파일명
    
        for size, image_obj in image_objs_per_size.items():
            # for db json필드
            s3_file_name = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_group_name}/{uuid}_{size}.webp"
            s3_urls_per_size[size] = s3_file_name
    
            # for s3 upload
            to_s3_upload_data_per_size[size] = {
                "image_obj": image_obj,
                "image_group_name": image_group_name,
                "image_file_name": f"{uuid}_{size}.webp"
            }
    ```
   

3. 반복문 내 s3_url을 만드는 것을 `get_s3_url()`메서드로 추출할 건데, file_name은 외부의 uuid + 반복문변수 size로 미리 만들어서 넣어주게 한다.
    ```python
    for size, image_obj in image_objs_per_size.items():
        # for db json필드
        file_name = f"{uuid}_{size}.webp"
        s3_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_group_name}/{file_name}"
        s3_urls_per_size[size] = s3_url
    
        # for s3 upload
        to_s3_upload_data_per_size[size] = {
            "image_obj": image_obj,
            "image_group_name": image_group_name,
            "image_file_name": file_name,
        }
    ```
   
4. **메서드 추출시, AWS_변수들은 환경변수 -> config.py -> settings 변수로 추출될테니, 파라미터에 포함하지 않는다.**
    ```python
    async def get_s3_url(image_group_name, s3_file_name):
        return f"https://{settings.aws_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{image_group_name}/{s3_file_name}"
    ```
    ```python
    for size, image_obj in image_objs_per_size.items():
        # for db json필드
        file_name = f"{uuid}_{size}.webp"
        
        s3_url = await get_s3_url(image_group_name, file_name)
        s3_urls_per_size[size] = s3_url
    
        # for s3 upload
        to_s3_upload_data_per_size[size] = {
            "image_obj": image_obj,
            "image_group_name": image_group_name,
            "image_file_name": file_name,
        }
    ```
   
5. 환경변수에 AWS_변수 추가 -> settings에서 잡아서 import하게 한다.
    ```python
    class Settings(BaseSettings):
        #...
        aws_bucket_name: str 
        aws_region: str
    ```
   
6. 프로필 변경 form에서 이미지를 첨부하여, 주소가 완성되는지 본다
    - aws변수는 막 넣었다. korea/picstargram
    ```python
        print(f"""image_url_data >>
     {s3_urls_per_size}
     
     image_to_upload_data  >> 
     {to_s3_upload_data_per_size}
     """)
    # image_url_data >>
     {'thumbnail': 'https://picstargram.s3.korea.amazonaws.com/미분류/01c2f568-7221-44f3-bdb2-146d7397ba65_thumbnail.webp', 512: 'https://picstargram.s3.korea.amazonaws.com/미분류/01c2f568-7221-44f3-bdb2-146d7397ba65_512.webp', 1024: 'https://picstargram.s3.korea.amazonaws.com/미분류/01c2f568-7221-44f3-bdb2-146d7397ba65_1024.webp'}
     
     image_to_upload_data  >> 
     {'thumbnail': {'image_obj': <PIL.Image.Image image mode=RGB size=200x200 at 0x1CEB21B2C10>, 'image_group_name': '미분류', 'image_file_name': '01c2f568-7221-44f3-bdb2-146d7397ba65_thumbnail.webp'}, 512: {'image_obj': <PIL.Image.Image image mode=RGB size=512x248 at 0x1CEB2372160>, 'image_group_name': '미분류', 'image_file_name': '01c2f568-7221-44f3-bdb2-146d7397ba65_512.webp'}, 1024: {'image_obj': <PIL.Image.Image image mode=RGB size=1024x497 at 0x1CEB23AFE50>, 'image_group_name': '미분류', 'image_file_name': '01c2f568-7221-44f3-bdb2-146d7397ba65_1024.webp'}}
     
    ```
   
7. 이제 to_s3_upload_data_per_size를 이용해 s3에 업로드를 해야한다. 
    - 그 전에 AWS 설정을 끝내야한다.
    - 다음시간에 알아보자.

