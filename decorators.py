from functools import wraps

from jose import ExpiredSignatureError
from starlette.requests import Request
from starlette.responses import RedirectResponse

from crud.picstargrams import get_user
from enums.messages import Message, MessageLevel
from schemas.picstargrams import UserToken, UserSchema
from utils.auth import decode_token
from utils.https import redirect, render


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
                # path=f"{request.url_for('pic_index')}?next={request.url}",
                path=request.url_for('pic_index').include_query_params(next=request.url),
            )

            return response
            # raise e # 이대로 두면, middleware에서 render하는데, modal용 noContent 트리거로만 간다?

        # 4) acess_token이 없어서 request.state.user = None상태 -> 직접 로그인하도록 redirect
        if not request.state.user:
            response = redirect(
                request,
                path=request.url_for('pic_index').include_query_params(next=request.url),
            )

            return response
            # 2) login 페이지가 따로 없으니 messages를 보내기 위해서
            # return render(request, "picstargram/home/index.html",
            #               messages=[Message.CREATE.write("포스트", level=MessageLevel.INFO)],
            #               hx_trigger='loginModal')

        response = await func(request, *args, **kwargs)

        # 5) access_token이 있지만, 만료되어 재발급 -> next_token들이 None, None 아니라면, response.set_cookie에 삽입
        await set_new_token_to(response, next_access_token, next_refresh_token)

        return response

    return wrapper


async def set_user_token_to(request):
    cookies = request.cookies

    next_access_token = None
    next_refresh_token = None

    if "access_token" in cookies.keys():
        access_token = cookies.get("access_token")
        refresh_token = cookies.get("refresh_token")
        try:
            access_token_info: dict = decode_token(access_token)
            request.state.user = UserToken(**access_token_info)
            # print('로그인 된 상태 UserToken >> ', UserToken)
        except ExpiredSignatureError:
            try:
                refresh_token_info: dict = decode_token(refresh_token)

                user_id = int(refresh_token_info['sub'])
                user: UserSchema = get_user(user_id)

                next_token: dict = user.refresh_token(refresh_token, refresh_token_info['iat'])

                next_access_token = next_token['access_token']
                next_refresh_token = next_token['refresh_token'] if next_token['refresh_token'] != refresh_token \
                    else None

                request.state.user = UserToken(**decode_token(next_access_token))
                # print(f"재발급과 동시에 login 완료 >> {request.state.user}")

            # except ExpiredSignatureError:
            #     # TODO: login 검사안하는 곳(home에 로그인검사안하도록 적용 후)으로 redirect
            #     raise NotAuthorized('토큰이 만료되었습니다. 다시 시작해주세요.')
            except Exception as e:
                raise e

        except Exception as e:
            raise e

    return next_access_token, next_refresh_token


async def set_new_token_to(response, next_access_token, next_refresh_token):
    if next_access_token:
        response.set_cookie('access_token', next_access_token, httponly=True)
    if next_refresh_token:
        response.set_cookie('refresh_token', next_refresh_token, httponly=True)
