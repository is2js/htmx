from starlette import status


class TemplateException(Exception):
    """
    oob message전달을 위해, 204를 제외한 200~399 까지 swap이 일어나는 코드로 반환한다.
    """
    status_code: int
    message: str
    ex: Exception
    hx_trigger: dict
    context: dict
    template_name: str

    def __init__(self,
                 status_code: int = status.HTTP_200_OK,
                 message: str = None,
                 ex: Exception = None,
                 hx_trigger=None,
                 context: dict = None,
                 template_name: str = None,
                 html: str = None
                 ):
        if not (200 <= status_code < 400 or status_code != 204):
            raise Exception('템플릿 오류는 status_code가 200<= < 400 사이이며, 204 또한 제한됩니다.')

        self.status_code = status_code
        self.message = message
        self.ex = ex
        self.hx_trigger = hx_trigger if hx_trigger else dict()
        self.context = context if context else dict()
        self.template_name = template_name if template_name else ""
        self.html = html if html else ""


class InternalServerException(TemplateException):
    def __init__(
            self,
            message="서버 오류 입니다. 관리자에게 문의해주세요.",
            ex: Exception = None,
    ):
        super().__init__(
            message=message,
            ex=ex,
        )


class NotFoundException(TemplateException):
    def __init__(
            self,
            message,
            ex: Exception = None,
    ):
        super().__init__(
            message=message,
            ex=ex,
        )


class BadRequestException(TemplateException):
    def __init__(
            self,
            message,
            ex: Exception = None,
            context=None,
            hx_trigger=None,
            template_name=None,
            html=None
    ):
        super().__init__(
            message=message,
            ex=ex,
            context=context,
            hx_trigger=hx_trigger,
            template_name=template_name,
            html=html,
        )


class NotAuthorized(TemplateException):
    def __init__(
            self,
            message,
            ex: Exception = None,
    ):
        super().__init__(
            message=message,
            ex=ex,
        )
