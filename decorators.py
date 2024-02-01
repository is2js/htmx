from functools import wraps

from starlette.requests import Request

from utils.https import redirect


def login_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):

        if not request.state.user:
            response = redirect(
                request,
                path=request.url_for('pic_index').include_query_params(next=request.url),
            )
            return response

        return await func(request, *args, **kwargs)

    return wrapper

