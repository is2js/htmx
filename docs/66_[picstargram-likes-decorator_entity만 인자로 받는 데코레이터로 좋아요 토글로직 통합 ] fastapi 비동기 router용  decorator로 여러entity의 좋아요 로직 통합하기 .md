- cookie 인증 유튜브: https://www.youtube.com/watch?v=EO9XWml9Nt0
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html
- ImageReq참고: https://github.dev/riseryan89/imizi-api/blob/main/app/middlewares/access_control.py
- **진짜배기 s3 세팅: https://wooogy-egg.tistory.com/77**
- **post개발 이후, s3 다운로드 참고 github: https://github.com/jrdeveloper124/file-transfer/blob/main/main.py#L30**
    - 유튜브: https://www.youtube.com/watch?v=mNwO_z6faAw
- **s3 boto3 드릴 블로그**: https://dschloe.github.io/aws/04_s3/s3_basic/
- **boto3 client말고 session으로 메서드들 정리 튜토리얼: https://thecodinginterface.com/blog/aws-s3-python-boto3/**

- bootstrap + github 인스타클론 참고:
    - 유튜브: https://www.youtube.com/watch?v=ZCvKlyAkjik
    - github: https://github.com/codingvenue/instagram-hompage-clone-bootstrap/blob/master/index.html
- django stream을 포함한 story : https://www.youtube.com/watch?v=5fG5xaIGzoI&list=WL&index=8&t=4s
- jinja2 지존 튜토리얼 블로그: https://ttl255.com/jinja2-tutorial-part-4-template-filters/
    - recursive: https://stackoverflow.com/questions/23657796/sum-a-value-inside-a-loop-in-jinja
    - 누적합: https://stackoverflow.com/questions/7537439/how-to-increment-a-variable-on-a-for-loop-in-jinja-template
    - list변경 map post.likes -> like.user_id
      list로 : https://stackoverflow.com/questions/31895602/ansible-filter-a-list-by-its-attributes
    - loop의 다양한 변수들(나중에 재귀시 재귀레벨
      확인하자): https://stackoverflow.com/questions/57414751/how-to-use-enumeratezipseq1-seq2-in-jinja2
- todo:
    - form
      validation: https://medium.com/@soverignchriss/asynchronous-form-field-validation-with-htmx-and-django-eb721165b5e8
- comment: https://www.youtube.com/watch?v=T5Jfb_LkoV0&list=PL5E1F5cTSTtTAIw_lBp1hE8nAKfCXgUpW&index=14
- reply: https://github.dev/tcxcx/django-webapp/tree/main/a_inbox/templates/a_inbox

- htmx
    - 검증: https://github.com/bigskysoftware/htmx/issues/75


### decorator로 공통로직 통합하기

#### 비동기 router용 데코레이터
1. django 참고 : https://github.dev/tcxcx/django-webapp/tree/main/
    ```python
    def like_toggle(model):
        def inner_func(func):
            def wrapper(request, *args, **kwargs):
                post = get_object_or_404(model, id=kwargs.get('pk'))
                user_exist = post.likes.filter(username=request.user.username).exists()
                
                if post.author != request.user:
                    if user_exist:
                        post.likes.remove(request.user)
                    else:
                        post.likes.add(request.user)
                return func(request, post)
            return wrapper
        return inner_func
    
    @login_required
    @like_toggle(Post)
    def like_post(request, post):
        return render(request, 'snippets/likes.html', {'post' : post})
    
    
    @login_required
    @like_toggle(Comment)
    def like_comment(request, post):
        return render(request, 'snippets/likes_comment.html', {'comment' : comment})
     
    ```
2. 인자를 받는 decorator (3중)를 정의하고, 인자로는 entity(ex> post, reply) 등을 받는다.
    ```python
    def like_toggle(entity):
        def inner_func(func):
            def wrapper(request, *args, **kwargs):
                ...
                return func(request)
            return wrapper
        return inner_func
    
    ```
   
2. **하지만, fastapi의 `비동기 route`에서는 `reutnr되는 func`이 `비동기메서드로서 reutrn await func()`이어야한다.**
    - **또한 `가장 내부 함수` 역시 `async def`로 정의해주고, `@wraps(func)`데코레이터도 같이 사용해줘야한다.**
    - **가장 내부 함수는 `받은 func을 호출해서 반환`해야하는데, fastapi route는 async def이므로 `await 를 붙여서 func호출`해야한다. 또한 post/reply의 route에서 인자로 받는 `id`까지 추가로 인자로 넣어서 반환해줘야한다.**
    ```python
    def like_toggle(entity):
        def inner_func(func):
            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                return await func(request, id_)
            return wrapper
        return inner_func
    ```

#### 통합로직 변환

1. reply like route의 로직을 보면서, 천천히 공통화한다.
    - **일단, `path parameter`의 값은 `kwagrs`에서 꺼내면 된다.**
    ```pyhton
    async def pic_hx_like_reply(
            request: Request,
            reply_id: int
    ):
        #...
    ```
    - **각 entity_name별로 path param으로 오니, `f-string을 이용`해서 get한다.**
    ```python
    def like_toggle(entity):
        def inner_func(func):
            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                # path로 오는 인자값은 kwargs에서 꺼내면 된다.
                id_ = kwargs.get(f'{entity}_id')
                # kwargs >> {'reply_id': 1}
    ```

2. 각 entity를 get/delete/create 메서드 호출은 **일단 함수변수를 만들어서, `if entity==""`마다 get메서드를 `변수에 할당하여 공통 변수로 호출할 준비`를 한다.**
    - **꺼낸 모델은 schema라는 변수에 넣어주고, template_name도 서로 다르니 `if문에서 공통변수`로 받아놓는다.**
    ```python
    reply = get_reply(reply_id, with_user=True, with_likes=True)
    #...
    delete_liked_reply(user_exists_like)
    #...
    like = create_liked_reply(data)
    ```
    ```python
    # TODO: 실제 모델이라면, model.get(id=) 통합메서드
    if entity == 'post':
        getter = get_post
        creater = create_liked_post
        deleter = delete_liked_post
        schema = getter(id_, with_user=True, with_likes=True)
        template_name = "picstargram/post/partials/post_likes_button.html"
    elif entity == 'reply':
        getter = get_reply
        creater = create_liked_reply
        deleter = delete_liked_reply
        schema = getter(id_, with_user=True, with_likes=True)
        template_name = "picstargram/post/partials/reply_likes_button_and_count.html"
    else:
        ...
    ```
   

3. **마지막 return은 각 route에서 처리하도록 하고, 그외 가정은 통합한다.**
    - **return에서는 `await func(request, 추출한 id_)`를 return해서 `async route가 await로 호출`되도록 한다**
    ```python
    def like_toggle(entity):
        def inner_func(func):
            @wraps(func)
            async def wrapper(request, *args, **kwargs):
                # path로 오는 인자값은 kwargs에서 꺼내면 된다.
                id_ = kwargs.get(f'{entity}_id')
                # kwargs >> {'reply_id': 1}
    
                # TODO: 실제 모델이라면, model.get(id=) 통합메서드
                if entity == 'post':
                    getter = get_post
                    creater = create_liked_post
                    deleter = delete_liked_post
                    schema = getter(id_, with_user=True, with_likes=True)
                    template_name = "picstargram/post/partials/post_likes_button.html"
                elif entity == 'reply':
                    getter = get_reply
                    creater = create_liked_reply
                    deleter = delete_liked_reply
                    schema = getter(id_, with_user=True, with_likes=True)
                    template_name = "picstargram/post/partials/reply_likes_button_and_count.html"
                else:
                    ...
                
                schema = getter(id_, with_user=True, with_likes=True)
                likes = schema.likes
                user_id = request.state.user.id
    
                if schema.user.id == user_id:
                    raise BadRequestException(
                        '작성자는 좋아요를 누를 수 없어요🤣',
                        context={f"{entity}": schema},
                        template_name=template_name
                    )
    
                user_exists_like = next((like for like in likes if like.user_id == user_id), None)
    
                if user_exists_like:
                    deleter(user_exists_like)
                    # schema = getter(id_, with_likes=True)
                    # return render(request, template_name=template_name,
                    #               context={f"{entity}": schema},
                    #               messages=Message.DELETE.write('좋아요', text="💔좋아요를 취소했습니다.💔", level=MessageLevel.WARNING),
                    #               )
    
                # 2-2) 좋아요를 안누른상태면, 좋아요를 생성한다.
                else:
                    data = {'user_id':user_id, f"{entity}_id": id_}
                    like = creater(data)
    
                    # schema = getter(id_, with_likes=True)
                    # return render(request, template_name=template_name,
                    #               context={f"{entity}": schema},
                    #               messages=Message.SUCCESS.write('좋아요', text="❤좋아요를 눌렀습니다.❤", level=MessageLevel.SUCCESS),
                    #               )
    
                return await func(request, id_)
    
            return wrapper
    
        return inner_func
    
    ```
   

4. **이제 like 토글 route들에 `@likte_toggle('entity')` 데코레이터를 붙이고, `최신데이터를 조회`후 context에 넣어서 `render`해주는 부분만 남긴다.**
    - **지금까지는 똑같은 message만 전달하게 된다.**
    ```python
    @app.post("/replies/{reply_id}/like")
    @login_required
    @like_toggle('reply')
    async def pic_hx_like_reply(
            request: Request,
            reply_id: int
    ):
        reply = get_reply(reply_id, with_likes=True)
        return render(request, "picstargram/post/partials/reply_likes_button_and_count.html",
                      context=dict(reply=reply),
                      messages=Message.SUCCESS.write('좋아요', text="❤좋아요를 눌렀습니다.❤", level=MessageLevel.SUCCESS),
                      )
   
    @app.post("/posts/{post_id}/like")
    @login_required
    @like_toggle('post')
    async def pic_hx_like_post(
            request: Request,
            post_id: int
    ):
    
        post = get_post(post_id, with_likes=True)
        return render(request, "picstargram/post/partials/post_likes_button.html",
                      context=dict(post=post),
                      messages=Message.SUCCESS.write('좋아요', text="❤좋아요를 눌렀습니다.❤", level=MessageLevel.SUCCESS),
                      oobs=["picstargram/post/partials/post_likes_count.html"]
                      )
    ```

5. **message를 지우던지, `데코레이터에서 is_liked`여부를 받아와야한다.**

#### 데코레이터에서 route의 정해진 param외 값을 전달하려면? -> request.state를 이용

1. `route에서 is_liked:bool`을 추가 -> 데코레이터에서 return await func(request, id_, `is_liked`) 해봤지만,
    - **router의 인자는, Body, Field, `path/get param`등 외의 커스텀인자를 직접 추가할 수 없다.**
    - **생각해낸 방법은 `데코레이터~route를 항시 통과하는 request`에 `.state`에 값을 할당하고, 라우터에서 이용하는 방법이다.**

2. 데코레이터에서 is_liked 여부를 가변변수로 만든 뒤, `request.state.is_liked`에 넣어준다.
    ```python
        is_liked = False
        if user_exists_like:
            deleter(user_exists_like)
            
        else:
            is_liked = True
            data = {'user_id': user_id, f"{entity}_id": id_}
            like = creater(data)
        
        # request.state에 is_liked 값을 추가
        request.state.is_liked = is_liked
        
        return await func(request, id_)
    ```
3. router에서는 request.state.is_liked 여부에 따라 message의 text와 level을 정해서 할당해준다.

    ```python
    @app.post("/replies/{reply_id}/like")
    @login_required
    @like_toggle('reply')
    async def pic_hx_like_reply(
            request: Request,
            reply_id: int,
    ):
        #
        message_text = "❤좋아요를 눌렀습니다.❤" if request.state.is_liked else "💔좋아요를 취소했습니다.💔"
        message_level = MessageLevel.SUCCESS if request.state.is_liked else MessageLevel.WARNING
    
        reply = get_reply(reply_id, with_likes=True)
        return render(request, "picstargram/post/partials/reply_likes_button_and_count.html",
                      context=dict(reply=reply),
                      messages=Message.SUCCESS.write('좋아요', text=message_text, level=message_level),
                      )
    
    @app.post("/posts/{post_id}/like")
    @login_required
    @like_toggle('post')
    async def pic_hx_like_post(
            request: Request,
            post_id: int,
    ):
        message_text = "❤좋아요를 눌렀습니다.❤" if request.state.is_liked else "💔좋아요를 취소했습니다.💔"
        message_level = MessageLevel.SUCCESS if request.state.is_liked else MessageLevel.WARNING
    
        post = get_post(post_id, with_likes=True)
        return render(request, "picstargram/post/partials/post_likes_button.html",
                      context=dict(post=post),
                      messages=Message.SUCCESS.write('좋아요', text=message_text, level=message_level),
                      oobs=["picstargram/post/partials/post_likes_count.html"]
                      )
    
    ```
   
### AWS 명령어 모음

```shell
%UserProfile%\.aws\credentials
%UserProfile%\.aws\config

aws configure list-profiles

# 등록
aws configure --profile {프로젝트명} # ap-northeast-2 # json
# 재사용시
set AWS_PROFILE={프로젝트명}

cat ~\.aws\credentials


# S3
aws s3 ls --profile {프로필명}
aws s3 mb s3://{버킷명}
aws s3 ls --profile {프로필명}


aws s3 cp {파일경로} s3://{버킷명}
aws s3 cp {파일경로} s3://{버킷명}/{폴더명} --acl public-read
```

#### IAM key 변경

1. root사용자 로그인 > IAM > 해당사용자 클릭 > `보안 자격 증명` 탭 > 액세스키
2. 기존 key `비활성화` 후 필요시 삭제 (있다가 cli에서 확인하고 비활성화하면 더 좋을 듯)
3. 새 액세스키 AWS CLI 선택하여 발급
4. 터미널 열어서 `AWS CLI`를 통해 해당프로젝트의 profile key들 덮어쓰기
    ```shell
    aws configure list-profiles # 현재 프로필들 확인
    cat ~\.aws\credentials # 현재 프로필들의 key설정값들 확인 (콘솔에서 비활성화시킨 것과 일치하는지)
    aws configure --picstargram # 특정프로필 key 덮어쓰기 with 콘솔
    ```

5. 프로젝트 .env의 `aws_access_key_id`와 `aws_secret_access_key`를 변경

   


