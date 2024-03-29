# CRUD 함수 정의
import datetime

from schemas.picstargrams import UserSchema, PostSchema, CommentSchema, LikeSchema, TagSchema, PostTagSchema, \
    ImageInfoSchema, ReplySchema, LikedPostSchema, ReactionedCommentsSchema, LikedReplySchema
from utils.auth import hash_password

users, comments, posts, tags, post_tags, liked_posts, reactioned_comments, liked_replies = [], [], [], [], [], [], [], []
# 이미지
image_infos = []
# 답글
replies = []


def find_max_id(model_list):
    return max([model.id for model in model_list], default=0)


def get_users(with_posts: bool = False, with_comments: bool = False, with_image_infos: bool = False):
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

    if with_image_infos:
        for user in users:
            user.image_infos = [image_info for image_info in image_infos if image_info.user_id == user.id]

    return users


def get_user(user_id: int,
             with_posts: bool = False,
             with_comments: bool = False,
             with_image_infos: bool = False,
             ):
    user = next((user for user in users if user.id == user_id), None)
    if not user:
        return None

    if with_posts:
        user.posts = [post for post in posts if post.user_id == user.id]

    if with_comments:
        user.comments = [comment for comment in comments if comment.user_id == user.id]

    if with_image_infos:
        user.image_infos = [image_info for image_info in image_infos if image_info.user_id == user.id]

    return user


def get_user_by_username(username: str,
                         with_posts: bool = False,
                         with_comments: bool = False,
                         with_image_infos: bool = False,

                         ):
    user = next((user for user in users if user.username == username), None)
    if not user:
        return None

    if with_posts:
        user.posts = [post for post in posts if post.user_id == user.id]

    if with_comments:
        user.comments = [comment for comment in comments if comment.user_id == user.id]

    if with_image_infos:
        user.image_infos = [image_info for image_info in image_infos if image_info.user_id == user.id]

    return user


def get_user_by_email(email: str, with_posts: bool = False, with_comments: bool = False,
                      with_image_infos: bool = False,
                      ):
    user = next((user for user in users if user.email == email), None)
    if not user:
        return None

    if with_posts:
        user.posts = [post for post in posts if post.user_id == user.id]

    if with_comments:
        user.comments = [comment for comment in comments if comment.user_id == user.id]

    if with_image_infos:
        user.image_infos = [image_info for image_info in image_infos if image_info.user_id == user.id]

    return user


# def create_user(user_schema: UserSchema):
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


# def update_user(user_id: int, user_schema: UserSchema):
#     user = get_user(user_id)
#     if not user:
#         raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")
#
#     # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
#     # -> 지금은 업데이트 허용 필드를 직접 할당함.
#     user.username = user_schema.username
#     if user_schema.image_url:
#         user.image_url = user_schema.image_url
#     user.updated_at = datetime.datetime.now()
#
#     return user

def update_user(user_id: int, data: dict):
    user = get_user(user_id)
    if not user:
        raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")

    for key, value in data.items():
        # create와 달리, nullable한 값을 가지고 오는 edit에서는 None을 제외하고 수정한다.
        if not value:
            continue
        # 하지만, input의 value를 image빼고는 미리 채워놨으니 상관없다?
        setattr(user, key, value)

    # 서버 부여
    user.updated_at = datetime.datetime.now()

    return user


def delete_user(user_id: int):
    user = get_user(user_id)
    if not user:
        raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")

    global users
    users = [user for user in users if user.id != user_id]

    # one 삭제시, many도 모두 삭제한다.(CASCADE)
    global posts, comments, image_infos
    # Delete associated posts
    posts = [post for post in posts if post.user_id != user_id]
    # Delete associated comments
    comments = [comment for comment in comments if comment.user_id != user_id]

    # Delete associated image_infos
    # TODO: s3삭제로직도 미리삭제하도록 추가해야함.
    image_infos = [image_info for image_info in image_infos if image_info.user_id != user_id]


# def get_post(post_id: int, with_user: bool = True, with_comments: bool = False, with_comment_user: bool = False):
# def get_post(post_id: int, with_user: bool = True, with_comments: bool = False):
def get_post(
        post_id: int,
        with_user: bool = True, with_comments: bool = False, with_likes: bool = False,
        # with_post_tags: bool = False
        with_tags: bool = False
):
    post = next((post for post in posts if post.id == post_id), None)
    if not post:
        return None

    if with_user:
        post.user = get_user(post.user_id)

    if with_comments:
        # post.comments = [
        #     get_comment(comment.id, with_user=True) for comment in comments if comment.post_id == post.id
        # ]
        post.comments = get_comments(post_id, with_user=True, with_replies=True)

    # likes(중간테이블) 구현후, with_likes 추가
    if with_likes:
        post.likes = [
            get_liked_post(like.id, with_user=True) for like in liked_posts if like.post_id == post.id
        ]

    # post_tags(중간테이블) 구현후, with_post_tags 추가 -> with_tags 추가
    # if with_post_tags:
    #     post.post_tags = get_post_tags_by_post_id(post.id, with_tag=True)

    if with_tags:
        post.tags = [post_tag.tag for post_tag in get_post_tags_by_post_id(post.id, with_tag=True)]

    return post


def get_posts(
        with_user: bool = False,
        with_comments: bool = False,
        with_likes: bool = False,
        with_tags: bool = False
):
    # one은 next()로 찾는 get_user()를 재활용
    if with_user:
        for post in posts:
            post.user = get_user(post.user_id)

    # many는 순회
    if with_comments:
        for post in posts:
            post.comments = get_comments(post.id, with_user=True, with_replies=True)
            # post.comments = [
            #     get_comment(comment.id, with_user=True, with_replies=True) for comment in comments if
            #     comment.post_id == post.id
            # ]

    # 실질 중간테이블 like를 many로 넣으면 -> 반대편 one(user) list도 many로 써 담기게 된다.
    if with_likes:
        for post in posts:
            post.likes = get_liked_posts(post.id, with_user=True)

    # 중간테이블 post_tags를 many로 추가 -> 조회/삭제시 옵션 추가
    if with_tags:
        for post in posts:
            post.tags = [
                post_tag.tag for post_tag in get_post_tags_by_post_id(post.id, with_tag=True)
            ]

    return posts


# new) many생성시, schema 속  fk로 온 one_id -> 파라미터로 + 내부 one존재여부 검사 필수
# def create_post(post_schema: PostSchema):
def create_post(data: dict):
    # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    # user = get_user(post_schema.user_id)
    # if not user:
    #     raise Exception(f"해당 user(id={post_schema.user_id})가 존재하지 않습니다.")

    try:
        # many1) 에 대한 정보는 Optional[List[해당Schema]]로 직접 변환해야함.
        if data.get('tags'):
            tags = []
            for tag_data in data['tags']:
                if tag := get_tag_by_name(tag_data['name']):
                    tags.append(tag)
                else:
                    tags.append(create_tag(tag_data))

            data['tags'] = tags

        post = PostSchema(**data)

        # id + created_at, updated_at 서버 부여
        post.id = find_max_id(posts) + 1
        post.created_at = post.updated_at = datetime.datetime.now()

        # many2) 가 존재할 때만, 중간테이블 생성 호출! 추가
        if post.tags:
            try:
                create_post_tags(post, post.tags)
            except Exception as e:
                raise e

        posts.append(post)

        return post

    except Exception as e:
        raise e


# def update_post(post_id: int, post_schema: PostSchema):
def update_post(post_id: int, data: dict):
    # new) many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    # user = get_user(data.user_id)
    # if not user:
    #     raise Exception(f"해당 user(id={post_schema.user_id})가 존재하지 않습니다.")

    post = get_post(post_id)
    if not post:
        raise Exception(f"해당 post(id={post_id})가 존재하지 않습니다.")

    # -> 지금은 업데이트 허용 필드를 직접 할당함.
    # data = post_schema.model_dump()
    # post.update(data)
    # post.title = post_schema.title
    # post.content = post_schema.content
    # if post_schema.image_url:
    #     post.image_url = post_schema.image_url

    for key, value in data.items():
        setattr(post, key, value)

    # 서버 부여
    post.updated_at = datetime.datetime.now()

    return post


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

    # new) 중간테이블도 one삭제시 many가 삭제되는 것과 동일하다.
    global liked_posts
    liked_posts = [like for like in liked_posts if like.post_id != post_id]

    global post_tags
    post_tags = [post_tag for post_tag in post_tags if post_tag.post_id != post_id]


# new) eagerload를 하더라도 순환참조에러 발생할 수 있으니, with_xxx를 붙여서 처리한다.
def get_comment(comment_id: int, with_user: bool = False, with_replies: bool = True,
                with_reactions=True
                ):
    comment = next((comment for comment in comments if comment.id == comment_id), None)
    if not comment:
        return None

    if with_user:
        user = get_user(comment.user_id)

        if not user:
            return None

        comment.user = user

    if with_replies:
        comment.replies = get_replies(comment_id, with_user=True, with_likes=True)

    if with_reactions:
        comment.reactions = [
            get_reactioned_comment(reaction.id, with_user=True) for reaction in reactioned_comments
            if reaction.comment_id == comment.id
        ]

    return comment


def get_comments(post_id: int, with_user: bool = False, with_replies: bool = True):
    # new) path로 부모가 올 경우, 존재검사 -> CUD가 아니므로, raise 대신 []로 처리
    post = get_post(post_id)
    if not post:
        return []

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
            get_comment(comment.id, with_user=True, with_replies=True) for comment in comments if
            comment.post_id == post.id
        ]

    return [comment for comment in comments if comment.post_id == post_id]


def get_comments_by_post_author(post_id: int):
    # new) path로 부모가 올 경우, 존재검사 -> CUD가 아니므로, raise 대신 []로 처리
    post = get_post(post_id, with_user=True)
    if not post:
        return []

    author = post.user
    return [
        get_comment(comment.id, with_user=True) for comment in comments
        if comment.post_id == post.id and comment.user_id == author.id
    ]


def create_comment(data: dict):
    # many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    user_id = data.get('user_id')
    user = get_user(user_id)
    if not user:
        raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")

    post_id = data.get('post_id')
    post = get_post(post_id)
    if not post:
        raise Exception(f"해당 post(id={post_id})가 존재하지 않습니다.")

    try:
        comment_schema = CommentSchema(**data)
        # id + created_at, updated_at 부여
        comment_schema.id = find_max_id(comments) + 1
        comment_schema.created_at = comment_schema.updated_at = datetime.datetime.now()

        comments.append(comment_schema)

    except Exception as e:
        raise e

    return comment_schema


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
    comment.content = comment_schema.content
    comment.updated_at = datetime.datetime.now()

    return comment


def delete_comment(comment_id: int):
    comment = get_comment(comment_id)
    if not comment:
        raise Exception(f"해당 comment(id={comment_id})가 존재하지 않습니다.")

    global comments
    comments = [comment for comment in comments if comment.id != comment_id]


def get_liked_post(like_id: int, with_user: bool = False):
    like = next((like for like in liked_posts if like.id == like_id), None)
    if not like:
        return None

    if with_user:
        user = get_user(like.user_id)

        if not user:
            return None

        like.user = user

    return like


def get_liked_posts(post_id: int, with_user: bool = False):
    # new) path로 부모가 올 경우, 존재검사 -> CUD가 아니므로, raise 대신 []로 처리
    # post = get_post(post_id)
    # if not post:
    #     return []

    # one을 eagerload할 경우, get_like(,with_user=)를 이용하여 early return
    # -> 아닐 경우, list compt fk조건으로 데이터 반환
    if with_user:
        return [
            get_liked_post(like.id, with_user=True) for like in liked_posts if like.post_id == post_id
        ]

    return [like for like in liked_posts if like.post_id == post_id]


def create_liked_post(data: dict):
    user = get_user(data['user_id'])
    if not user:
        raise Exception(f"해당 user(id={data['user_id']})가 존재하지 않습니다.")
    post = get_post(data['post_id'])
    if not post:
        raise Exception(f"해당 post(id={data['post_id']})가 존재하지 않습니다.")

    try:
        liked_post_schema = LikedPostSchema(**data)
        # id + created_at, ~~updated_at~~ 부여
        liked_post_schema.id = find_max_id(liked_posts) + 1
        liked_post_schema.created_at = datetime.datetime.now()
        liked_posts.append(liked_post_schema)

    except Exception as e:
        raise e

    return liked_post_schema


# create_or_delete의 판단상황이므로, 삭제를 like_id가 안들어온다.
# -> 누른상태-> get으로 like객체얻은상태 -> schema 통째로 받아 post_id, user_id로 삭제처리한다.
def delete_liked_post(liked_post_schema: LikedPostSchema):
    user = get_user(liked_post_schema.user_id)
    if not user:
        raise Exception(f"해당 user(id={liked_post_schema.user_id})가 존재하지 않습니다.")
    post = get_post(liked_post_schema.post_id)
    if not post:
        raise Exception(f"해당 post(id={liked_post_schema.post_id})가 존재하지 않습니다.")

    global liked_posts

    liked_posts = [like for like in liked_posts if
                   not (like.post_id == liked_post_schema.post_id and like.user_id == liked_post_schema.user_id)]


def get_liked_reply(like_id: int, with_user: bool = False):
    like = next((like for like in liked_replies if like.id == like_id), None)
    if not like:
        return None

    if with_user:
        user = get_user(like.user_id)

        if not user:
            return None

        like.user = user

    return like


def get_liked_replies(reply_id: int, with_user: bool = False):
    # one을 eagerload할 경우, get_like(,with_user=)를 이용하여 early return
    # -> 아닐 경우, list compt fk조건으로 데이터 반환
    if with_user:
        return [
            get_liked_reply(like.id, with_user=True) for like in liked_replies if like.reply_id == reply_id
        ]

    return [like for like in liked_replies if like.reply_id == reply_id]


def create_liked_reply(data: dict):
    user = get_user(data['user_id'])
    if not user:
        raise Exception(f"해당 user(id={data['user_id']})가 존재하지 않습니다.")
    reply = get_reply(data['reply_id'])
    if not reply:
        raise Exception(f"해당 reply(id={data['reply_id']})가 존재하지 않습니다.")

    try:
        liked_reply_schema = LikedReplySchema(**data)
        # id + created_at, ~~updated_at~~ 부여
        liked_reply_schema.id = find_max_id(liked_replies) + 1
        liked_reply_schema.created_at = datetime.datetime.now()
        print(f"len(liked_replies)  >> {len(liked_replies)}")

        liked_replies.append(liked_reply_schema)
        print(f"len(liked_replies)  >> {len(liked_replies)}")

    except Exception as e:
        raise e

    return liked_reply_schema


def delete_liked_reply(liked_reply_schema: LikedReplySchema):
    user = get_user(liked_reply_schema.user_id)
    if not user:
        raise Exception(f"해당 user(id={liked_reply_schema.user_id})가 존재하지 않습니다.")
    reply = get_reply(liked_reply_schema.reply_id)
    if not reply:
        raise Exception(f"해당 reply(id={liked_reply_schema.reply_id})가 존재하지 않습니다.")

    global liked_replies

    liked_replies = [like for like in liked_replies if
                     not (like.reply_id == liked_reply_schema.reply_id and like.user_id == liked_reply_schema.user_id)]


def get_reactioned_comment(reaction_id: int, with_user: bool = False):
    reaction = next((reaction for reaction in reactioned_comments if reaction.id == reaction_id), None)
    if not reaction:
        return None

    if with_user:
        user = get_user(reaction.user_id)

        if not user:
            return None

        reaction.user = user

    return reaction


def get_reactioned_comments(comment_id: int, with_user: bool = False):
    if with_user:
        return [
            get_reactioned_comment(reaction.id, with_user=True) for reaction in reactioned_comments if
            reaction.comment_id == comment_id
        ]

    return [like for like in liked_posts if like.comment_id == comment_id]


def create_reactioned_comment(data: dict):
    user = get_user(data['user_id'])
    if not user:
        raise Exception(f"해당 user(id={data['user_id']})가 존재하지 않습니다.")
    comment = get_comment(data['comment_id'])
    if not comment:
        raise Exception(f"해당 comment(id={data['comment_id']})가 존재하지 않습니다.")

    try:
        reactioned_comment_schema = ReactionedCommentsSchema(**data)
        # id + created_at, ~~updated_at~~ 부여
        reactioned_comment_schema.id = find_max_id(reactioned_comments) + 1
        reactioned_comment_schema.created_at = datetime.datetime.now()
        reactioned_comments.append(reactioned_comment_schema)

    except Exception as e:
        raise e

    return reactioned_comment_schema


def delete_reactioned_comment(reactioned_comment_schema: LikedPostSchema):
    user = get_user(reactioned_comment_schema.user_id)
    if not user:
        raise Exception(f"해당 user(id={reactioned_comment_schema.user_id})가 존재하지 않습니다.")
    comment = get_comment(reactioned_comment_schema.comment_id)
    if not comment:
        raise Exception(f"해당 comment(id={reactioned_comment_schema.comment_id})가 존재하지 않습니다.")

    global reactioned_comments

    reactioned_comments = [reaction for reaction in reactioned_comments if
                           not (reaction.comment_id == reactioned_comment_schema.comment_id
                                and reaction.user_id == reactioned_comment_schema.user_id
                                and reaction.emoji == reactioned_comment_schema.emoji
                                )]


# def get_tag(tag_id: int):
def get_tag(tag_id: int, with_posts: bool = False):
    tag = next((tag for tag in tags if tag.id == tag_id), None)
    if not tag:
        return None

    if with_posts:
        tag.posts = [post_tag.post for post_tag in get_post_tags_by_tag_id(tag.id, with_post=True)]

    return tag


def get_tag_by_name(name: str):
    tag = next((tag for tag in tags if tag.name.lower() == name.lower()), None)
    if not tag:
        return None

    return tag


def get_tags(with_posts: bool = False):
    if with_posts:
        for tag in tags:
            tag.posts = [
                post_tag.post for post_tag in get_post_tags_by_tag_id(tag.id, with_post=True)
            ]
    return tags


# def create_tag(tag_schema: TagSchema):
def create_tag(data: dict):
    try:
        # optional인 created_at을 data dict에 미리 넣어줘야 **로 생성된다?!
        # data.update({
        #     'created_at': datetime.datetime.now(),
        #     'updated_at': datetime.datetime.now()
        # })

        tag = TagSchema(**data)

        # 서버부여
        tag.id = find_max_id(tags) + 1
        tag.created_at = tag.updated_at = datetime.datetime.now()

        tags.append(tag)
    except Exception as e:
        raise e

    return tag


def update_tag(tag_id: int, tag_schema: TagSchema):
    tag = get_tag(tag_id)
    if not tag:
        raise Exception(f"해당 tag(id={tag_id})가 존재하지 않습니다.")

    # TODO: update Schema가 개발되면 model(**user_schema.model_dump())로 대체
    # -> 지금은 업데이트 허용 필드를 직접 할당함.
    tag.name = tag_schema.name

    tag.updated_at = datetime.datetime.now()

    return tag


def delete_tag(tag_id: int):
    tag = get_tag(tag_id)
    if not tag:
        raise Exception(f"해당 tag(id={tag_id})가 존재하지 않습니다.")

    global tags
    tags = [tag for tag in tags if tag.id != tag_id]

    # post와 중간테이블데이터도 many로서 삭제
    global post_tags
    post_tags = [post_tag for post_tag in post_tags if post_tag.tag_id != tag_id]


def get_post_tag(post_tag_id: int, with_post: bool = False, with_tag: bool = False):
    post_tag = next((post_tag for post_tag in post_tags if post_tag.id == post_tag_id), None)
    if not post_tag:
        return None

    if with_post:
        post_tag.post = get_post(post_tag.post_id)

    if with_tag:
        post_tag.tag = get_tag(post_tag.tag_id)

    return post_tag


def create_post_tags(post, tags):
    try:
        for tag in tags:
            post_tag = PostTagSchema(
                post_id=post.id,
                tag_id=tag.id,
            )

            post_tag.id = find_max_id(post_tags) + 1
            post_tag.created_at = post_tag.updated_at = datetime.datetime.now()

            # 아이디 부여 후, 원본에 append하지 않으면 -> 같은 id로만 부여된다. 조심. 매번 id 수동 부여
            post_tags.append(post_tag)

    except Exception as e:
        raise e


# post.post_tags -> 각 post_tag에 tag가 박힘 : post.tags 를 위해,
# post_id로 post_tags를 찾되, 내부에서 post_tags에서는 with_tags를 eagerload한 것을 불러온다.
def get_post_tags_by_post_id(post_id: int, with_tag: bool = False):
    # 1) 일단 주인공 fk키의 존재여부 검사 (조회니까 raise 대신 []로 처리)
    post = get_post(post_id)
    if not post:
        return []

    # 2) 메모리데이터에서 특정 post_id로 post_tags를 가져오되,
    #    post_tags의 각 데이터마다 tag(반대쪽one)이 박혀있도록 eagerload하기 위해
    #    단일조회메서드(with_tags=True)를 활용한다
    if not with_tag:
        return [post_tag for post_tag in post_tags if post_tag.post_id == post.id]
    else:  # with_tag=True
        return [
            get_post_tag(post_tag.id, with_tag=True) for post_tag in post_tags if
            post_tag.post_id == post_id
        ]


# 순수중간테이블의 주인공2: tag에서 대해서도 전체조회메서드를 만든다.
# - 단일은 with_로 둘다 반영함.
def get_post_tags_by_tag_id(tag_id: int, with_post: bool = False):
    # 1) 일단 주인공 fk키의 존재여부 검사 (조회니까 raise 대신 []로 처리)
    tag = get_tag(tag_id)
    if not tag:
        return []

    # 2) 메모리데이터에서 특정 tag_id로 post_tags를 가져오되,
    #    post_tags의 각 데이터마다 post(반대쪽one)이 박혀있도록 eagerload하기 위해
    #    단일조회메서드(with_posts=True)를 활용한다
    if not with_post:
        return [post_tag for post_tag in post_tags if post_tag.tag_id == tag_id]
    else:  # with_post=True
        return [
            get_post_tag(post_tag.id, with_post=True) for post_tag in post_tags
            if post_tag.tag_id == tag_id
        ]


def create_image_info(data: dict):
    # many생성시 one존재여부 검사 필수 -> 없으면 404 에러
    user_id = data.get('user_id')
    user = get_user(user_id)
    if not user:
        raise Exception(f"해당 user(id={user_id})가 존재하지 않습니다.")

    try:
        image_info = ImageInfoSchema(**data)

        # id + created_at, updated_at 서버 부여
        image_info.id = find_max_id(image_infos) + 1
        image_info.created_at = image_info.updated_at = datetime.datetime.now()
        image_infos.append(image_info)

        return image_info

    except Exception as e:
        raise e


# def get_reply(reply_id: int, with_user: bool = False):
def get_reply(reply_id: int, with_user: bool = False, with_likes: bool = False):
    reply = next((reply for reply in replies if reply.id == reply_id), None)
    if not reply:
        return None

    if with_user:
        user = get_user(reply.user_id)

        if not user:
            return None

        reply.user = user

    # likes(중간테이블) 구현후, with_likes 추가
    if with_likes:
        reply.likes = [
            get_liked_reply(like.id, with_user=True) for like in liked_replies if like.reply_id == reply.id
        ]

    return reply


def get_replies(comment_id: int, with_user: bool = False, with_likes: bool = False):
    #### get_복수에서는 부모검사하지말자! 재귀발생하게 됨.
    # get_comment는, post.comments 만들 때 쓰는데, 여기서도 또 쓴다.
    # => 앞으로 부모검사는 `조회메서드안에 있으면 주석처리 -> 조회전 외부에서 하자.` 상하위도메인의 순수조회 vs 검사용조회가 중복되어 재귀를 발생시킨다.
    # comment = get_comment(comment_id)
    # if not comment:
    #     return []

    # one을 eagerload할 경우, get_replies(,with_user=)를 이용하여 early return
    # -> 아닐 경우, list compt fk조건으로 데이터 반환
    # if with_user:
    #     return [
    #         get_reply(reply.id, with_user=True) for reply in replies if reply.comment_id == comment_id
    #     ]

    if with_user and not with_likes:
        return [
            get_reply(reply.id, with_user=True) for reply in replies if reply.comment_id == comment_id
        ]
    elif not with_user and with_likes:
        return [
            get_reply(reply.id, with_likes=True) for reply in replies if reply.comment_id == comment_id
        ]
    elif with_user and with_likes:
        return [
            get_reply(reply.id, with_user=True, with_likes=True) for reply in replies if reply.comment_id == comment_id
        ]

    return [reply for reply in replies if reply.comment_id == comment_id]


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


def delete_reply(reply_id: int):
    reply = get_reply(reply_id)
    if not reply:
        raise Exception(f"해당 Reply(id={reply_id})가 존재하지 않습니다.")

    global replies
    replies = [reply for reply in replies if reply.id != reply_id]
