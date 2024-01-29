from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from enums.messages import Message, MessageLevel
from exceptions.template_exceptions import TemplateException
from utils.https import render


class AccessControl(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        ip = request.headers["x-forwarded-for"] if "x-forwarded-for" in request.headers.keys() else request.client.host
        request.state.ip = ip.split(",")[0] if "," in ip else ip

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 템플릿 오류 -> oob render(status code 200<= <400 + 204제외만 oob swap)
            if isinstance(e, TemplateException):
                return render(request, "",
                              messages=[Message.FAIL.write('', text=f'{str(e)}', level=MessageLevel.ERROR)],
                              )
            else:
                # return JSONResponse({"message": "Internal Server Error"}, status_code=500)
                # return JSONResponse({"message": str(e)}, status_code=500)
                raise e

            # raise e
            # if isinstance(e, TemplateException):

        # error_dict = dict(
        #     status=error.status_code,
        #     code=error.code,
        #     message=error.message,
        #     detail=error.detail,
        # )

        # if isinstance(error, (APIException, SQLAlchemyException, DBException)):
        # if isinstance(error, (APIException, SQLAlchemyException, DBException, DiscordException)):
        #     response = JSONResponse(status_code=error.status_code, content=error_dict)
