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


- todo:
    - form validation: https://medium.com/@soverignchriss/asynchronous-form-field-validation-with-htmx-and-django-eb721165b5e8
- comment: https://www.youtube.com/watch?v=T5Jfb_LkoV0&list=PL5E1F5cTSTtTAIw_lBp1hE8nAKfCXgUpW&index=14
- reply: https://github.dev/tcxcx/django-webapp/tree/main/a_inbox/templates/a_inbox


### comment에서 one을 post_id 대신 comment_id로
1. json에서 comments를 복사해서, replies를 만들고, user_id는 유지하고, post_id대신 comment_id로 바꾼다.
    - **content 필드만 보내게 된다.**
    ```json
      "replies": [
        {
          "id": 1,
          "content": "this is a reply",
          "created_at": "2022-05-17 16:56:21",
          "updated_at": "2023-05-17 16:56:21",
          "user_id": 2,
          "comment_id": 1
        },
        {
          "id": 2,
          "content": "2번째 답글",
          "created_at": "2022-05-17 16:56:21",
          "updated_at": "2023-05-17 16:56:21",
          "user_id": 1,
          "comment_id": 1
        }
      ],
    ```

2. crud패키지에 전역데이터 replies = []를 선언하여 생성 후, main.py에서 불러오기
    ```python
    # crud/picstargram.py
    # CRUD 함수 정의
    import datetime
    
    from schemas.picstargrams import UserSchema, PostSchema, CommentSchema, LikeSchema, TagSchema, PostTagSchema, \
        ImageInfoSchema
    from utils.auth import hash_password
    
    users, comments, posts, likes, tags, post_tags = [], [], [], [], [], []
    # 이미지
    image_infos = []
    # 답글
    replis = []
    ```
    ```python
    # main.py
    # 메모리 데이터 모음
    tracks_data = []
    from crud.picstargrams import users, posts, comments, get_users, get_user, create_user, update_user, delete_user, \
        get_posts, get_post, create_post, update_post, delete_post, get_comment, get_comments, create_comment, \
        update_comment, delete_comment, likes, tags, post_tags, create_like, delete_like, get_tags, get_tag, create_tag, \
        update_tag, delete_tag, get_user_by_username, get_user_by_email, \
        image_infos, create_image_info, get_comments_by_post_author, \
        replies
    ```
   
3. Schema 생성 - CommentSchema와 CreateCommentReq를 복사해서 post_id -> comment_id로 변경
    ```python
    class ReplySchema(BaseModel):
        id: Optional[int] = None
        content: str
        created_at: Optional[datetime.datetime] = None
        updated_at: Optional[datetime.datetime] = None
        user_id: int
        comment_id: int
    
        user: Optional['UserSchema'] = None
    
    
    class ReplyCreateReq(BaseModel):
        content: str
    
        @classmethod
        def as_form(
                cls,
                content: str = Form(...),
        ):
            return cls(content=content)
    ```
   

4. 예시데이터 load하여 Schema에 담고 -> lifepsan에서 추가해주기
    ```python
    # main.py
    async def init_picstargram_json_to_list_per_pydantic_model():
    
        picstargram_path = pathlib.Path() / 'data' / 'picstargram2.json'
        with open(picstargram_path, 'r', encoding='utf-8') as f:
    
            picstargram = json.load(f)
    
            # 답글 추가
            replies = [ReplySchema(**reply) for reply in picstargram.get("replies", [])]
    
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        #...
        users_, comments_, posts_, likes_, tags_, post_tags_, replies_ = await init_picstargram_json_to_list_per_pydantic_model()
        #...
        replies.extend(replies_)
    ```

### crud 생성
1. get_comment를 참고해서 get_reply 생성
    - `get_단수`는 자신의 id로 찾되,
    - **one의 fk가 상위도메인(상위도메인은 .many로 가져옮)은 아니지만, `작성자등 항상포함해야하는 필수정보one`의 경우, `many의 get에  with_xxxx`로 받아주기**
    ```python
    def get_reply(reply_id: int, with_user: bool = False):
        reply = next((reply for reply in replies if reply.id == reply_id), None)
        if not reply:
            return None
    
        if with_user:
            user = get_user(reply.user_id)
    
            if not user:
                return None
    
            reply.user = user
    
        return reply
    ```
2. get_replies()로 get_복수 정의하기. 이 때, comment에 딸린 replies들을 찾을 것이기 때문에, comment_id를 받아야한다.
    - **`many의 get_복수`은 `상위도메인one 의id`로 가져오는 경우가 많다. ex> posts/post_id/comments -> get_comments(post_id)**
    - **이 때, 상위도메인 검사method-get_comment는, comment의 상위도메인 post가 .comments를 만들때 사용되어, post -> get_comments -> `get_comment` -> get_replies -> 내부 `get_comment`로 부모검사**
    - **앞으로 부모검사는 `조회메서드안에 있으면 주석처리 -> 조회전 외부에서 하자.` 상하위도메인의 순수조회 vs 검사용조회가 중복되어 재귀를 발생시킨다.**
    ```python
    def get_replies(comment_id: int, with_user: bool = False):
        # new) path로 부모가 올 경우, 존재검사 -> CUD가 아니므로, raise 대신 []로 처리
        # comment = get_comment(comment_id)
        # if not comment:
        #     return []
    
        # one을 eagerload할 경우, get_replies(,with_user=)를 이용하여 early return
        # -> 아닐 경우, list compt fk조건으로 데이터 반환
        if with_user:
            return [
                get_reply(reply.id, with_user=True) for reply in replies if reply.comment_id == comment.id
            ]
    
        return [reply for reply in replies if reply.comment_id == comment_id]
    ```
   

3. create by data dict
    - `many의 생성`시에는, `모든 one의 존재조건을 확인`한다.
    - try후 생성되면, 서버부여(id, 시간들)한 뒤, 전역데이터 list에 append해준다.
    ```python
    def create_reply(data: dict):
        # many생성시 one존재여부 검사 필수 -> 없으면 404 에러
        user_id = data.get('user_id')
        user = get_user(user_id)
        if not user:
            raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")
    
        comment_id = data.get('comment_id')
        comment = get_comment(comment_id)
        if not comment:
            raise Exception(f"해당 comment(id={comment_id})가 존재하지 않습니다.")
    
        try:
            reply_schema = ReplySchema(**data)
            # id + created_at, updated_at 부여
            reply_schema.id = find_max_id(replies) + 1
            reply_schema.created_at = reply_schema.updated_at = datetime.datetime.now()
    
            replies.append(reply_schema)
    
        except Exception as e:
            raise e
    
        return reply_schema
    ```
   

4. reply는 수정없이 삭제만
    ```python
    def delete_reply(reply_id: int):
        reply = get_reply(reply_id)
        if not reply:
            raise Exception(f"해당 Reply(id={reply_id})가 존재하지 않습니다.")
    
        global replies
        replies = [reply for reply in replies if reply.id != reply_id]
    ```
 

5. **many의 crud가 끝났으면, `one입장에서 .many`를 쓰는지 확인하고, 쓴다면 `Schema`에 추가한다.**
    - **comment.replies를 써서, 순회하며 사용되도록 `comment`위주로 처리될 것이기 때문에 CommentSchema에 many Schema를 추가한다**
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
    ```
   

6. **one입장에서 `가져와야하는 .many`는 `oen의 get메서드에 파라미터로 추가`하고, 항상 True로 넣어주자.**
    - get_comemnts -> get_comment 순으로 추가한다.
    - with가 여러개일 경우, 그만큼 경우의수를 만든다.
    ```python
    def get_comments(post_id: int, with_user: bool = False, with_replies: bool = True):
        
        # if with_user:
        if with_user and not with_replies:
            return [
                get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
            ]
        elif not with_user and with_replies:
            return [
                get_comment(comment.id, with_replies=True) for comment in comments if comment.post_id == post.id
            ]
        elif with_user and with_replies:
            return [
                get_comment(comment.id, with_user=True, with_replies=True) for comment in comments if comment.post_id == post.id
            ]
        
        return [comment for comment in comments if comment.post_id == post_id]
    
    ```
    ```python
    def get_comment(comment_id: int, with_user: bool = False, with_replies:bool=True):
        comment = next((comment for comment in comments if comment.id == comment_id), None)
        if not comment:
            return None
    
        if with_user:
            user = get_user(comment.user_id)
    
            if not user:
                return None
    
            comment.user = user
            
        if with_replies:
            comment.replies = get_replies(comment_id, with_user=True)
    
        return comment
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

   
