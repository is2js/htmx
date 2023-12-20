# CRUD 함수 정의
import datetime

from schemas.picstagrams import UserSchema

users, comments, posts = [], [], []


def find_max_id(model_list):
    return max([model.id for model in model_list], default=0)


def get_users(with_posts: bool = False, with_comments: bool = False):
    if with_posts and with_comments:
        for user in users:
            user.posts = [post for post in posts if post.user_id == user.id]
            user.comments = [comment for comment in comments if comment.user_id == user.id]

    elif with_posts:
        for user in users:
            user.posts = [post for post in posts if post.user_id == user.id]

    elif with_comments:
        for user in users:
            user.comments = [comment for comment in comments if comment.user_id == user.id]

    return users


def get_user(user_id: int, with_posts: bool = False, with_comments: bool = False):
    user = next((user for user in users if user.id == user_id), None)
    if not user:
        return None

    if with_posts and with_comments:
        user.posts = [post for post in posts if post.user_id == user.id]
        user.comments = [comment for comment in comments if comment.user_id == user.id]

    elif with_posts:
        user.posts = [post for post in posts if post.user_id == user.id]

    elif with_comments:
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

#
#     # many는 list compt로 다 가져와서 넣기
#     user.posts = [post for post in posts if post.user_id == user.id]
#     user.comments = [comment for comment in comments if comment.user_id == user.id]
#
#     return user
#
# def get_user(user_id: int):
#     user = next((user for user in users if user.id == user_id), None)
#     if user:
#         user.posts = [post for post in posts if post.user_id == user.id]
#         user.comments = [comment for comment in comments if comment.user_id == user.id]
#     return user
#
# def create_post(title: str, content: str, user_id: int, img_path: Optional[str] = None):
#     user = get_user(user_id)
#     if user:
#         new_post = PostModel(id=find_max_id(posts) + 1, title=title, content=content, user_id=user_id, img_path=img_path)
#         user.posts.append(new_post)
#         posts.append(new_post)
#         return new_post
#     return None
#
# def get_post(post_id: int):
#     post = next((post for post in posts if post.id == post_id), None)
#     if post:
#         post.user = get_user(post.user_id)
#         post.comments = [comment for comment in comments if comment.post_id == post.id]
#     return post
#
# def create_comment(text: str, user_id: int, post_id: int):
#     user = get_user(user_id)
#     post = get_post(post_id)
#     if user and post:
#         new_comment = CommentModel(id=find_max_id(comments) + 1, text=text, user_id=user_id, post_id=post_id)
#         post.comments.append(new_comment)
#         comments.append(new_comment)
#         return new_comment
#     return None
#
# def get_comments(post: PostModel):
#     comments_for_post = [comment for comment in comments if comment.post_id == post.id]
#     for comment in comments_for_post:
#         comment.user = get_user(comment.user_id)
#     return comments_for_post
#
# def update_comment(comment_id: int, updated_text: str):
#     comment = next((comment for comment in comments if comment.id == comment_id), None)
#     if comment:
#         comment.text = updated_text
#
# def delete_comment(comment_id: int):
#     global comments
#     comments = [comment for comment in comments if comment.id != comment_id]
#
# # CRUD 예제
# # Create User
# user3 = create_user("user3")
#
# # Create Post
# post3 = create_post("Third Post", "Yet another post.", user3.id, img_path="/path/to/image.jpg")
#
# # Create Comment
# comment3 = create_comment("Nice work!", user3.id, post3.id)
#
# # Read Post with User and Comments
# post_with_user_and_comments = get_post(post3.id)
# if post_with_user_and_comments:
#     print("Post Title:", post_with_user_and_comments.title)
#     print("Post User:", post_with_user_and_comments.user.username)
#     print("Post Comments:")
#     for comment in get_comments(post_with_user_and_comments):
#         print(" -", comment.text, "by", comment.user.username)
# else:
#     print("Post not found.")
