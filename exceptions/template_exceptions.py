from starlette import status


class TemplateException(Exception):
    """
    oob message전달을 위해, 204를 제외한 200~399 까지 swap이 일어나는 코드로 반환한다.
    """
    status_code: int
    message: str
    ex: Exception

    def __init__(self, status_code: int = status.HTTP_200_OK, message: str = None, ex: Exception = None):
        if not (200 <= status_code < 400 or status_code != 204):
            raise Exception('템플릿 오류는 status_code가 200<= < 400 사이이며, 204 또한 제한됩니다.')
        self.status_code = status_code
        self.message = message
        self.ex = ex


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
    ):
        super().__init__(
            message=message,
            ex=ex,
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