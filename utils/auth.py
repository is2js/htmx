from datetime import datetime, timedelta

from jose import jwt, JWTError, ExpiredSignatureError
from jose.exceptions import JWTClaimsError
from passlib.context import CryptContext

from config import settings
from exceptions.template_exceptions import NotAuthorized

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


############
# register #
############

def hash_password(password):
    return pwd_context.hash(password)


############
# login #
############

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_token(data: dict, delta: int):
    """
    :data: key "sub" / value str(user.id)가 필수로 들어가야한다.
    :delta: 분 단위로 timedelta(minutes=)에 넣을 int를 입력.
            access_token과 refresh_token 값이 다름.
    """
    payload = data.copy()

    payload.update({
        "exp": datetime.utcnow() + timedelta(minutes=delta),
        "iat": datetime.utcnow(),  # for refresh
        "iss": settings.app_name,
    })

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str):
    """
    """
    token = token.replace("Bearer ", "")
    # try:
    payload = jwt.decode(token, key=settings.jwt_secret_key, algorithms=settings.jwt_algorithm)
    return payload
    # except ExpiredSignatureError:
    #     raise NotAuthorized("토큰이 만료되었습니다. 다시 로그인 해주세요.")
    # except JWTError:
    #     raise NotAuthorized("토큰 정보가 정확하지 않습니다. 올바른 경로로 로그인 해주세요.")
