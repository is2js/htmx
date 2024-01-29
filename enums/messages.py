import json
from enum import Enum, auto


class MessageLevel(Enum):
    DEBUG = auto()
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()


class MessageCss(str, Enum):
    DEBUG = "bg-light"
    INFO = "text-white bg-primary"
    SUCCESS = "text-white bg-success"
    WARNING = "text-dark bg-warning"
    ERROR = "text-white bg-danger"


class Message(str, Enum):
    CREATE = "을(를) 생성하였습니다."
    READ = "을(를) 읽었습니다."
    UPDATE = "을(를) 수정했습니다."
    DELETE = "을(를) 삭제했습니다."
    FAIL = "을(를) 실패하였습니다."
    SUCCESS = "을(를) 성공하였습니다."

    def generate_text_and_css(self, entity, message_level):
        message_level_name = MessageLevel(message_level).name
        message_css = MessageCss[message_level_name].value

        postfix = self.value
        message_text = f"{entity}{postfix}"

        return message_text, message_css

    def write(
            self,
            entity: str,
            text:str = None,
            level: MessageLevel = MessageLevel.INFO
    ):
        """
        In [2]: Message.CREATE.write("포스트 생성", message_level=MessageLevel.ERROR)
        Out[2]: {'text': '포스트 생성을(를) 생성하였습니다.', 'css': 'text-white bg-danger'}
        """
        message_text, message_css = self.generate_text_and_css(entity, level)
        if text:
            message_text = text

        return {
            "text": message_text,
            "css": message_css
        }
