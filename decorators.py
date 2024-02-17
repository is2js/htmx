from functools import wraps

from fastapi import BackgroundTasks
from starlette.requests import Request

from exceptions.template_exceptions import NotAuthorized
from utils.https import redirect


def login_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not request.state.user:
            if is_htmx(request):
                raise NotAuthorized('로그인이 필요합니다.')
            else:
                response = redirect(
                    request,
                    path=request.url_for('pic_index').include_query_params(next=request.url),
                )
                return response

        if bg_task:=kwargs.get('bg_task'):
            # TODO: 일단 import BackgroundTasks만 되어있으면 되니, 그냥일단 둔다.
            return await func(request, *args,  **kwargs)
        else:
            return await func(request, *args, **kwargs)

    return wrapper


def is_htmx(request: Request):
    return request.headers.get("hx-request") == 'true'