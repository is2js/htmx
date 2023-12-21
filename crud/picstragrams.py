# CRUD 함수 정의
import datetime

from schemas.picstagrams import UserSchema, PostSchema, CommentSchema

users, comments, posts = [], [], []


def find_max_id(model_list):
    return max([model.id for model in model_list], default=0)


def get_users(with_posts: bool = False, with_comments: bool = False):
    if with_posts and with_comments:
        for user in users:
            user.posts = [post for post in posts if post.user_id == user.id]
            # user.comments = [comment for comment in comments if comment.user_id == user.id]
            user.comments = [get_comment(comment.id, with_user=True) for comment in comments if
                             comment.user_id == user.id]

    elif with_posts:
        for user in users:
            user.posts = [post for post in posts if post.user_id == user.id]

    elif with_comments:
        for user in users:
            # user.comments = [get_comment(comment.id, with_user=True) for comment in comments if comment.user_id == user.id]
            # => 순환참조 에러
            user.comments = [comment for comment in comments if comment.user_id == user.id]

    return users


def get_user(user_id: int, with_posts: bool = False, with_comments: bool = False):
    user = next((user for user in users if user.id == user_id), None)
    if not user:
        return None

    if with_posts:
        user.posts = [post for post in posts if post.user_id == user.id]

    if with_comments:
        user.comments = [comment for comment in comments if comment.user_id == user.id]

    return user


def create_user(user_schema: UserSchema):
    try:
        # id 부여
        user_schema.id = find_max_id(users) + 1
        # created_at, updated_at 부여
        user_schema.created_at = user_schema.updated_at = datetime.datetime.now()

        users.append(user_schema)
    except Exception as e:
        raise e

    return user_schema


def update_user(user_id: int, user_schema: UserSchema):
    user = get_user(user_id)
    if not user:
        raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")

    # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
    # -> 지금은 업데이트 허용 필드를 직접 할당함.
    user.username = user_schema.username
    if user_schema.image_url:
        user.image_url = user_schema.image_url
    user.updated_at = datetime.datetime.now()

    return user


def delete_user(user_id: int):
    user = get_user(user_id)
    if not user:
        raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")

    global users
    users = [user for user in users if user.id != user_id]

    # one 삭제시, many도 모두 삭제한다.(CASCADE)
    global posts, comments
    # Delete associated posts
    posts = [post for post in posts if post.user_id != user_id]
    # Delete associated comments
    comments = [comment for comment in comments if comment.user_id != user_id]


def get_posts(with_user: bool = False, with_comments: bool = False):
    # one은 next()로 찾는 get_user()를 재활용
    if with_user:
        for post in posts:
            post.user = get_user(post.user_id)

    # many는 순회
    if with_comments:
        for post in posts:
            post.comments = [
                get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
            ]

    return posts


# def get_post(post_id: int, with_user: bool = True, with_comments: bool = False, with_comment_user: bool = False):
def get_post(post_id: int, with_user: bool = True, with_comments: bool = False):
    post = next((post for post in posts if post.id == post_id), None)
    if not post:
        return None

    if with_user:
        post.user = get_user(post.user_id)

    if with_comments:
        post.comments = [
            get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
        ]

        # if with_comment_user:
        #     for comment in post.comments:
        #         comment.user = get_user(comment.user_id)

    return post


# new) eagerload를 하더라도 순환참조에러 발생할 수 있으니, with_xxx를 붙여서 처리한다.
def get_comment(comment_id: int, with_user: bool = False):
    comment = next((comment for comment in comments if comment.id == comment_id), None)
    if not comment:
        return None

    if with_user:
        user = get_user(comment.user_id)
        print(f"user >> {user}")

        if not user:
            return None

        comment.user = user

    return comment


# new) comments의 경우, 단독으로 전체조회X -> path param post_id로 조회
def get_comments(post_id: int, with_user: bool = False):
    # new) path로 부모가 올 경우, 존재검사 -> CUD가 아니므로, raise 대신 []로 처리
    post = get_post(post_id)
    if not post:
        return []

    # one을 eagerload할 경우, get_comment(,with_user=)를 이용하여 early return
    # -> 아닐 경우, list compt fk조건으로 데이터 반환
    if with_user:
        return [
            get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
        ]

    return [comment for comment in comments if comment.post_id == post.id]


# new) many생성시, schema 속  fk로 온 one_id -> 파라미터로 + 내부 one존재여부 검사 필수
def create_post(post_schema: PostSchema):
    # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    user = get_user(post_schema.user_id)
    if not user:
        raise Exception(f"해당 user(id={post_schema.user_id})가 존재하지 않습니다.")

    try:
        # id + created_at, updated_at 부여
        post_schema.id = find_max_id(posts) + 1
        post_schema.created_at = post_schema.updated_at = datetime.datetime.now()

        posts.append(post_schema)

    except Exception as e:
        raise e

    return post_schema


# new) many생성시, schema 속  fk로 온 one_id -> 파라미터로 + 내부 one존재여부 검사 필수
def create_comment(comment_schema: CommentSchema):
    # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    user = get_user(comment_schema.user_id)
    if not user:
        raise Exception(f"해당 user(id={comment_schema.user_id})가 존재하지 않습니다.")
    post = get_post(comment_schema.post_id)
    if not post:
        raise Exception(f"해당 post(id={comment_schema.post_id})가 존재하지 않습니다.")

    try:
        # id + created_at, updated_at 부여
        comment_schema.id = find_max_id(comments) + 1
        comment_schema.created_at = comment_schema.updated_at = datetime.datetime.now()

        comments.append(comment_schema)

    except Exception as e:
        raise e

    return comment_schema


def update_post(post_id: int, post_schema: PostSchema):
    # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    user = get_user(post_schema.user_id)
    if not user:
        raise Exception(f"해당 user(id={post_schema.user_id})가 존재하지 않습니다.")

    post = get_post(post_id)
    if not post:
        raise Exception(f"해당 post(id={post_id})가 존재하지 않습니다.")

    # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
    # -> 지금은 업데이트 허용 필드를 직접 할당함.
    post.title = post_schema.title
    post.content = post_schema.content
    if post_schema.image_url:
        post.image_url = post_schema.image_url

    post.updated_at = datetime.datetime.now()

    return post


def update_comment(comment_id: int, comment_schema: CommentSchema):
    # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    user = get_user(comment_schema.user_id)
    if not user:
        raise Exception(f"해당 user(id={comment_schema.user_id})가 존재하지 않습니다.")
    post = get_post(comment_schema.post_id)
    if not post:
        raise Exception(f"해당 post(id={comment_schema.post_id})가 존재하지 않습니다.")

    comment = get_comment(comment_id)
    if not comment:
        raise Exception(f"해당 commemt(id={comment_id})가 존재하지 않습니다.")

    # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
    # -> 지금은 업데이트 허용 필드를 직접 할당함.
    comment.text = comment_schema.text
    comment.updated_at = datetime.datetime.now()

    return comment


def delete_post(post_id: int):
    post = get_post(post_id)
    if not post:
        raise Exception(f"해당 post(id={post_id})가 존재하지 않습니다.")

    global posts
    posts = [post for post in posts if post.id != post_id]

    # one 삭제시, many도 모두 삭제한다.(CASCADE)
    global comments
    # Delete associated comments
    comments = [comment for comment in comments if comment.post_id != post_id]


def delete_comment(comment_id: int):
    comment = get_comment(comment_id)
    if not comment:
        raise Exception(f"해당 comment(id={comment_id})가 존재하지 않습니다.")

    global comments
    comments = [comment for comment in comments if comment.post_id != comment_id]
