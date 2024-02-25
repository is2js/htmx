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

- todo:
    - form
      validation: https://medium.com/@soverignchriss/asynchronous-form-field-validation-with-htmx-and-django-eb721165b5e8
- comment: https://www.youtube.com/watch?v=T5Jfb_LkoV0&list=PL5E1F5cTSTtTAIw_lBp1hE8nAKfCXgUpW&index=14
- reply: https://github.dev/tcxcx/django-webapp/tree/main/a_inbox/templates/a_inbox


### comments_count 셀 때, replies갯수도 반영하기

1. 일단 comments_count route에서, comment마다 .replies에 포함된 갯수를 순회하며 누적한 것도, 코멘트의 갯수에 포함시킨다.
    ```python
    @app.get("/picstargram/posts/{post_id}/comments-count", response_class=HTMLResponse)
    async def pic_hx_show_comments_count(
            request: Request,
            post_id: int,
            hx_request: Optional[str] = Header(None),
    ):
        post = get_post(post_id, with_user=True)
        # comments = get_comments(post_id, with_user=True)
        comments = get_comments(post_id, with_user=True, with_replies=True)
        comments_count = len(comments)
    
        replies_count = sum([len(comment.replies) for comment in comments])
        comments_count += replies_count
    
        context = {
            'request': request,
            'post': post,
            'comments_count': comments_count,
        }
    
        return render(request,
                      "picstargram/post/partials/comments_count_with_post.html",
                      context=context,
                      )
    
    ```
   
2. 여기까지하면, 댓글바뀔때만 바뀐다. **replies입력할 때(new reply route0, comment갯수도 바뀌게 trigger를 추가하여 내려주자.**
    - **commentCountChanged-post_id인데, post를 받을순 없으니 `comment를 조회 -> comment.post_id`로 대체한다.**
    ```python
    @app.post("/picstargram/comments/{comment_id}/replies/new", response_class=HTMLResponse)
    @login_required
    async def pic_new_reply(
            request: Request,
            comment_id: int,
            reply_create_req=Depends(ReplyCreateReq.as_form),
    ):
        try:
            # 1) form데이터는 crud하기 전에 dict로 만들어야한다.
            data = reply_create_req.model_dump()
    
            data['comment_id'] = comment_id
            data['user_id'] = request.state.user.id
    
            reply = create_reply(data)
    
            # 2) comment갯수변화 trigger를 위해 post_id가 필요
            comment = get_comment(comment_id)
            post_id = comment.post_id
    
        except Exception as e:
            raise BadRequestException(f'Reply 생성에 실패함.: {str(e)}')
    
        return render(request, "",
                      hx_trigger={
                          'noContent': False, 
                          f'repliesChanged-{comment_id}': True,
                          f'repliesCountChanged-{comment_id}': True,
                          f'commentsCountChanged-{post_id}': True, # 답글달시 댓글갯수변화도
                      },
                      messages=[Message.CREATE.write("답글", level=MessageLevel.INFO)],
                      )
    
    ```
   
3. **trigger로 count업데이트는 <-> 최초 렌더링시 count계산과 별개로서, 따로 처리해줘야한다.**
    - post.html을 렌더링할 때, comments를 순회하며 comment.replies의 |length를 누적합해서 comments_count에 넣어줘야한다.
    - **하지만, jinja2에서는 평범하게 누적합이 안된다. `for안에서 set을 치면, scope문제로, 가변변수에 누적이 안됨.`**

#### jinja2에서 누적합을 하는 방법: namespace
1. jinja2.0부터 for 바깥 누적가변변수 set에 대하여, for문 내부 set에 적용시 초기화되어버리는 문제를 `namespace(value=)`를 가변변수로 선택해서 해결한다.
    - 이렇게하면, for문 내부에서도 가변변수를 누적시킬 수 있다.
    - **`namespace.value`를 변수처럼 사용해서 for문에서 set으로 누적시키면 된다.**
    ```html
    {% set comments = post.comments %}
    {% set comments_count = comments | length %}
    
    {% set replies_count = namespace(value=0) %}
    {% for comment in comments %}
    {% set replies_count.value = replies_count.value + comment.replies | length %}
    {% endfor %}
    
    {% set comments_count = comments_count + replies_count.value %}
    ```
   
#### 하위도메인을 합하는 상위도메인의 count는 len말고, 개별proeperty를 활용하자
1. `@property`로 comment Schema에서 .replies_count를 정의하고, post Schema에서 .comments_count를 정의하면 될 듯하다.
    - comments는 객체가 아닌 list이므로 한번에 못할 듯.
    ```python
    class CommentSchema(BaseModel):
        id: Optional[int] = None
        content: str
        created_at: Optional[datetime.datetime] = None  # 서버부여 -> 존재는 해야함 but TODO: DB 개발되면, 예제 안뜨게 CreateSchema 분리하여 제거대상.
        updated_at: Optional[datetime.datetime] = None
        user_id: int
        post_id: int
    
        user: Optional['UserSchema'] = None
    
        replies: Optional[List['ReplySchema']] = []
        
        @property
        def replies_count(self):
            return len(self.replies)
    ```
    ```python
    class PostSchema(BaseModel):
    
        comments: Optional[List[CommentSchema]] = []
    
        likes: Optional[List['LikeSchema']] = []
        tags: Optional[List['TagSchema']] = []
    
        image_info: Optional['ImageInfoSchema'] = None
    
        @property
        def comments_count(self):
            comments_count = len(self.comments)
            replies_count = sum(comment.replies_count for comment in self.comments)
            return comments_count + replies_count
    ``` 
   

2. post.html에서는 comments_count를 활용하도록 바꾼다.
    ```html
    {% set comments_count = post.comments_count %}
    ```

3. route에서도 property활용하도록 변경
    ```python
    # post = get_post(post_id, with_user=True)
    # comments = get_comments(post_id, with_user=True)
    # comments = get_comments(post_id, with_user=True, with_replies=True)
    # comments_count = len(comments)
    #
    # replies_count = sum([len(comment.replies) for comment in comments])
    # comments_count += replies_count
    
    post = get_post(post_id, with_user=True, with_comments=True)
    comments_count = post.comments_count
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

   
