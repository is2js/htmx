from __future__ import annotations

import json
from typing import List

from starlette import status
from starlette.responses import HTMLResponse, Response
from starlette.templating import Jinja2Templates

from enums.messages import Message
from templatefilters import feed_time

templates = Jinja2Templates(directory="templates")
templates.env.filters['feed_time'] = feed_time  # 필터들도 main.py와 다르게 직접 추가해줘야한다.


def render(request, template_name="", context: dict = {}, status_code: int = 200, cookies: dict = {},
           hx_trigger: dict | str | List[str] = None,
           messages: dict | List[dict] = None,
           oobs: List[tuple] = None
           ):
    # 추가context가 안들어오는 경우는 외부에서 안넣어줘도 된다.
    ctx = {
        'request': request,
        # 'user': request.state.user,
        **context
    }

    # template render + oob도 아니면, 일반Response + 204로
    html_str = ""
    if template_name:
        t = templates.get_template(template_name)
        html_str += t.render(ctx)

    # messages 등 oob 처리
    # -> messages는 자주쓰이니 직접 편하게 입력하도록 oob template 경로를 적어서 반영해준다.
    oob_html_str = ""
    if messages:
        messages = [messages] if isinstance(messages, dict) else messages
        oob_html_str = render_oob('picstargram/_toasts.html', messages=messages)

    if oobs:
        for t_name, t_context in oobs:
            oob_html_str += ('\n' if oob_html_str else '') + render_oob(t_name, **t_context)

    # oob까지 없어야 실제 204 No Content -> swap 발생 안됨.
    if not (html_str or oob_html_str):
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
    # oob가 있다면, HTMLResponse + not 204로 나가야됨.
    else:
        total_html_str = '\n'.join([html_str, oob_html_str])
        response = HTMLResponse(total_html_str, status_code=status_code)

    hx_trigger: dict = convert_hx_trigger_to_dict(hx_trigger)
    if not html_str:
        hx_trigger['noContent'] = True
    response.headers['HX-Trigger'] = json.dumps(hx_trigger)

    # # messages를 삽입하려면, 기존 trigger들을 dict로 변환해야, message라는 또다른 HX-Trigger를 dict에 추가하여 -> 다시 json.dumps()로 string화
    # # 1) 1개의 string  VS 2) 2개이상의 "{" json 시작  => 둘다 dict로 만들어야한다.
    # # 3) 없는 경우 -> 빈 dict로 만들어야한다. -> .get( , {})로 해결
    # # ==> 없는 경우 VS 있는 경우( 2개이상-명시쉬움 -> 나머지는 1개)형태로 조건문 순서를 설정한다.
    # if messages:
    #     # 없는 경우 -> {}
    #     if hx_trigger := response.headers.get("HX-Trigger", {}):
    #         # 2개이상인 경우 -> json이라서 load하여 dict로 변환
    #         if hx_trigger.startswith("{"):
    #             hx_trigger = json.loads(hx_trigger)
    #         # 있는데 & 2개이상이 아닌 경우 -> 1개인 경우 -> value에 True를 집어넣는 dict로 변환
    #         else:
    #             hx_trigger = {hx_trigger: True}
    #
    #     # messages 1개만 오는 경우는 dict라서, list로 변환하여 삽입
    #     hx_trigger["messages"] = [messages] if isinstance(messages, dict) else messages
    #
    #     # hx_trigger와 통합된 HX-Trigger를 새롭게 집어넣는다.
    #     response.headers["HX-Trigger"] = json.dumps(hx_trigger)

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


def convert_hx_trigger_to_dict(hx_trigger):
    if hx_trigger:
        # 2) dict로 json변화없이 들어왔다면 그대로 둔다.
        if isinstance(hx_trigger, dict):
            pass
        # 3) dict가 아니면 str or List[str]이다. list류일 때는, 개별 trigger를 :True를 집어넣은 [dict 1개에 여러 key:value]를 dicㅅ comp로 만든다.
        #    hx_trigger dict comp >> {'postsChanged': True, 'closeModal': True}
        elif isinstance(hx_trigger, (list, tuple)):
            hx_trigger = {trigger: True for trigger in hx_trigger}
        # 4) list, tuple이 아니면, str으로 이미 json화 되어있는데, 1개면 "postsChanged" 지만,
        # -> 2개이상이면, {"postsChanged": true, "closeModal": "true"}의 json화 된상태라 json.loads하여 dict로 변환한다.
        else:
            if hx_trigger.startswith("{"):
                hx_trigger = json.loads(hx_trigger)
            else:
                hx_trigger = {hx_trigger: True}
    # 1) trigger가 없는 경우, 빈 dict를 만들어서, noContent일 때 삽입되도록 한다.
    else:
        hx_trigger = {}
    return hx_trigger


def render_oob(template_name, *args, **kwargs: dict):
    t = templates.get_template(template_name)
    oob_html_str = t.render(*args, **kwargs)
    return oob_html_str
