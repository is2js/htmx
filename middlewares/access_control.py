from jose import ExpiredSignatureError
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from crud.picstargrams import get_user
from enums.messages import Message, MessageLevel
from exceptions.template_exceptions import TemplateException, NotAuthorized
from schemas.picstargrams import UserToken, UserSchema, Token
from utils.auth import decode_token
from utils.https import render, url_pattern_check, redirect

app_name: str = "picstargram"
LOGIN_EXCEPT_PATH_REGEX = f"^(/docs|/redoc|/static|/favicon.ico|/uploads|/auth|/api/v[0-9]+/auth|/{app_name}/auth)"


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

        except Exception as e:
            # 템플릿 오류 -> oob render(status code 200<= <400 + 204제외만 oob swap)
            if isinstance(e, TemplateException):
                return render(request, "",
                              messages=[Message.FAIL.write('', text=f'{str(e)}', level=MessageLevel.ERROR)],
                              )
            # 그외 오류
            else:
                # return JSONResponse({"message": str(e)}, status_code=500)
                raise e


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
