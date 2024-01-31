from jose import ExpiredSignatureError
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from crud.picstargrams import get_user
from enums.messages import Message, MessageLevel
from exceptions.template_exceptions import TemplateException, NotAuthorized
from schemas.picstargrams import UserToken, UserSchema
from utils.auth import decode_token
from utils.https import render, url_pattern_check

app_name: str = "picstargram"
LOGIN_EXCEPT_PATH_REGEX = f"^(/docs|/redoc|/static|/favicon.ico|/uploads|/auth|/api/v[0-9]+/auth|/{app_name}/auth)"


class AccessControl(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        headers = request.headers
        url = request.url.path
        ip = request.headers["x-forwarded-for"] if "x-forwarded-for" in request.headers.keys() else request.client.host
        request.state.ip = ip.split(",")[0] if "," in ip else ip

        request.state.user = None

    #     login_required = not await url_pattern_check(url, LOGIN_EXCEPT_PATH_REGEX) \
    #                      or (url != "/") or (url != f"/{app_name}")
    #
        try:
    #         if login_required:
    #             # set 로그인(UserToken)을 위한 request cookies token들 검사
    #             next_access_token, next_refresh_token = await self.set_user_token_to(request)
    #
            response = await call_next(request)
    #
    #         # token 만료시, 재발급되는 token들을 response cookies에 set
    #         if login_required:
    #             await self.set_new_token_to(response, next_access_token, next_refresh_token)
    #
            return response
    #
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
    #
    #     # error_dict = dict(
    #     #     status=error.status_code,
    #     #     code=error.code,
    #     #     message=error.message,
    #     #     detail=error.detail,
    #     # )
    #
    #     # if isinstance(error, (APIException, SQLAlchemyException, DBException)):
    #     # if isinstance(error, (APIException, SQLAlchemyException, DBException, DiscordException)):
    #     #     response = JSONResponse(status_code=error.status_code, content=error_dict)
    #
    # async def set_new_token_to(self, response, next_access_token, next_refresh_token):
    #     if next_access_token:
    #         response.set_cookie('access_token', next_access_token, httponly=True)
    #     if next_refresh_token:
    #         response.set_cookie('refresh_token', next_refresh_token, httponly=True)
    #
    # async def set_user_token_to(self, request):
    #     cookies = request.cookies
    #
    #     next_access_token = None
    #     next_refresh_token = None
    #
    #     if "access_token" in cookies.keys():
    #         access_token = cookies.get("access_token")
    #         refresh_token = cookies.get("refresh_token")
    #         try:
    #             access_token_info: dict = decode_token(access_token)
    #             request.state.user = UserToken(**access_token_info)
    #             print('로그인 된 상태 UserToken >> ', UserToken)
    #         except ExpiredSignatureError:
    #             try:
    #                 refresh_token_info: dict = decode_token(refresh_token)
    #
    #                 user_id = int(refresh_token_info['sub'])
    #                 user: UserSchema = get_user(user_id)
    #
    #                 next_token: dict = user.refresh_token(refresh_token, refresh_token_info['iat'])
    #
    #                 next_access_token = next_token['access_token']
    #                 next_refresh_token = next_token['refresh_token'] if next_token['refresh_token'] != refresh_token \
    #                     else None
    #
    #                 request.state.user = UserToken(**decode_token(next_access_token))
    #                 print(f"재발급과 동시에 login 완료 >> {request.state.user}")
    #
    #             except ExpiredSignatureError:
    #                 # TODO: login 검사안하는 곳(home에 로그인검사안하도록 적용 후)으로 redirect
    #                 raise NotAuthorized('토큰이 만료되었습니다. 다시 시작해주세요.')
    #             except Exception as e:
    #                 raise e
    #
    #     return next_access_token, next_refresh_token
