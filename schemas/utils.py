import json

from fastapi import Body, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ValidationError
from starlette import status


def form_to(schema: BaseModel):
    """
    template용으로서, class FormTO와 달리 data, error정보(li태그concat string)를 튜플로 함께 반환
        # data >> {'content': '11'}

    @app.put("/posts/{post_id}", response_model=Union[PostSchema, str])
    async def pic_update_post(
            request: Request,
            post_id: int,
            data_and_errors_info=Depends(form_to(UpdatePostReq))

        data, errors_info = data_and_errors_info
        print(f"data >> {data}")

        if len(errors_info) > 0:
            # error_endpoint = request.url_for('errors', status_code=400)
            # error_endpoint = error_endpoint.include_query_params(message=errors_info)
            # return redirect(error_endpoint, is_htmx=is_htmx)
            response.status_code = 400
            return errors_info
    """
    # 바깥 function의 인자는 내부function에서 사용할 예정
    def bytes_body_to_dict_by_schema(body: bytes = Body(...)):
        # 로직 -> 최종 반환될 결과물 반환
        # 1) bytes를 utf-8로 decode(inplace) 후 연결자 &로 split한 것들을 순회하며, '='로 다시split후 dict에 쌓기
        json_dict = dict()
        for param in body.decode('utf-8').split('&'):
            key, value = param.split('=')
            json_dict[key] = value

        # 2) data dict로 변환(model_dump) 및 변환과정에 error가 발생한다면 list에 모았다가 string으로 concat
        data = dict()
        errors = []  # 에러항목마다 dict로 채워서, dict list가 됨.
        error_str = None
        try:
            # TODO; file input들은 배제하여 만들어보자.(test)
            data = schema(**json_dict).model_dump(exclude=['file', 'files'])
        except ValidationError as e:
            # 2-1) 에러가 나면, e.json()으로 string으로 만들 수 있다.
            error_str = e.json()

        # 2-2) 에러가 발생했다면, 다시 json을 dict로 load한다.
        # -> 만약 에러가 json이 아니라면, [필드의 부재 에러]가 발생했을 때라고 한다.
        # -> 내가 dict로 만들어서 기본 에러를 errors list에 넣는다.
        if error_str is not None:
            try:
                errors = json.loads(error_str)
            except Exception as e:
                errors = [
                    {"loc": "non_field"},
                    {"msg": "Unknown error"}
                ]

        # 3. 템플릿에서 errors를 순회하여 뿌려주기 위해, 미리 li태그를 달아놓고 string으로 concat한다.
        # {% for error in errors %}
        #     <li>{% if error.loc[0] != "__root__" %}<b>{{ error.loc[0] }}</b>:{% endif %} {{ error.msg }}</li>
        # {% endfor %}
        error_infos = ""
        for error in errors:
            error_info = "<li>"

            # 만약, "loc"[0]이 "__root__"의 에러라면, "msg"만 담고, 그외에는 "loc"[0]번째 + "msg"를 섞어준다.
            # # [{'type': 'missing', 'loc': ['loop_index'], 'msg': 'Field required', 'input': {'user_id': '3', 'calendar_id': '20'}, 'url': 'https://errors.pydantic.dev/2.3/v/missing'}]
            loc = error.get('loc')[0]
            msg = error.get('msg')
            if loc == "__root__":
                error_info += f"{msg}"
            else:
                error_info += f"{loc}: {msg}"

            error_info += "</li>"

        # data(dict)가 있을지, error_infos(string) 모르니 튜플로 둘다 넘겨준다.
        return data, error_infos

    return bytes_body_to_dict_by_schema  # call될 inner function 반환


class FormTo:
    """
    form_to함수와 달리, dict로 변환 -> 실패시 raise한다.

    @app.put("/posts/{post_id}", response_model=Union[PostSchema, str])
    async def pic_update_post(
            request: Request,
            post_id: int,
            response: Response,
            data: dict = Depends(FormTo(UpdatePostReq))
    ):
        try:
            post = update_post(post_id, data)
            return post

        except Exception as e:
            response.status_code = 400
            return f"Post 수정에 실패했습니다.: {e}"
    """
    def __init__(self, schema: BaseModel) -> None:
        self.schema = schema

    def __call__(self, body: bytes = Body(...)):

        # 로직 -> 최종 반환될 결과물 반환
        # 1) bytes를 utf-8로 decode(inplace) 후 연결자 &로 split한 것들을 순회하며, '='로 다시split후 dict에 쌓기
        json_dict = dict()
        for param in body.decode('utf-8').split('&'):
            key, value = param.split('=')
            json_dict[key] = value

        try:
            # return self.schema(**json_dict)
            return self.schema(**json_dict).model_dump(exclude=['file', 'files'])

        except ValidationError as e:
            raise HTTPException(
                detail=jsonable_encoder(e.errors()),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
