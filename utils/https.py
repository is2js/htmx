from __future__ import annotations

import json
from typing import List

from starlette.responses import HTMLResponse, Response
from starlette.templating import Jinja2Templates

from enums.messages import Message

templates = Jinja2Templates(directory="templates")


def render(request, template_name="", context: dict = {}, status_code: int = 200, cookies: dict = {},
           hx_trigger: str | List[str] = None,
           messages: dict | List[dict] = None,
           ):

    # 추가context가 안들어오는 경우는 외부에서 안넣어줘도 된다.
    ctx = {
        'request': request,
        # 'user': request.state.user,
        **context
    }

    # template render가 아니면 일반Response로
    if template_name:
        t = templates.get_template(template_name)
        html_str = t.render(ctx)
        response = HTMLResponse(html_str, status_code=status_code)
    else:
        response = Response(status_code=status_code)

    # hx_trigger가 1개의 string -> 그냥 삽입 / 2개이상인 경우, dict comp를 통해 True를 value로 준 dict list로 만든 뒤 -> json.dumps()로 string화
    if hx_trigger:
        if isinstance(hx_trigger, str):
            response.headers["HX-Trigger"] = hx_trigger
        else:
            response.headers["HX-Trigger"] = json.dumps({trigger: True for trigger in hx_trigger})

    # messages를 삽입하려면, 기존 trigger들을 dict로 변환해야, message라는 또다른 HX-Trigger를 dict에 추가하여 -> 다시 json.dumps()로 string화
    # 1) 1개의 string  VS 2) 2개이상의 "{" json 시작  => 둘다 dict로 만들어야한다.
    # 3) 없는 경우 -> 빈 dict로 만들어야한다. -> .get( , {})로 해결
    # ==> 없는 경우 VS 있는 경우( 2개이상-명시쉬움 -> 나머지는 1개)형태로 조건문 순서를 설정한다.
    if messages:
        # 없는 경우 -> {}
        if hx_trigger := response.headers.get("HX-Trigger", {}):
            # 2개이상인 경우 -> json이라서 load하여 dict로 변환
            if hx_trigger.startswith("{"):
                hx_trigger = json.loads(hx_trigger)
            # 있는데 & 2개이상이 아닌 경우 -> 1개인 경우 -> value에 True를 집어넣는 dict로 변환
            else:
                hx_trigger = {hx_trigger: True}

        # messages 1개만 오는 경우는 dict라서, list로 변환하여 삽입
        hx_trigger["messages"] = [messages] if isinstance(messages, dict) else messages

        # hx_trigger와 통합된 HX-Trigger를 새롭게 집어넣는다.
        response.headers["HX-Trigger"] = json.dumps(hx_trigger)

    # 기본 darkmode 및 cookie관련
    # response.set_cookie(key='darkmode', value=str(1))
    # if len(cookies.keys()) > 0:
    # set httponly cookies
    # for k, v in cookies.items():
    #     response.set_cookie(key=k, value=v, httponly=True)

    # delete coookies
    # for key in request.cookies.keys():
    #     response.delete_cookie(key)

    return response
