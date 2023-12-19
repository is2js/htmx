import mimetypes
import os
import pathlib
import uuid
from io import BytesIO


def _make_dir(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path, exist_ok=True)


def make_dir_and_file_path(directory_name, UPLOAD_DIR=None):
    if not UPLOAD_DIR:
        # project_config.UPLOAD_FOLDER
        # TODO: upload폴더를 지정하지않으면, root의 uploads폴더를 생성하여 저장한다.
        UPLOAD_DIR = pathlib.Path() / 'uploads'

    file_path = UPLOAD_DIR / f'{directory_name}'

    _make_dir(file_path)

    return file_path


def get_updated_file_name_and_ext_by_uuid4(file):
    # filename을 os.path.split  ext()를 이용하여, 경로 vs 확장자만 분리한 뒤, ex> (name, .jpg)
    #      list()로 변환한다.
    _, ext = os.path.splitext(file.filename)
    # print(f"name, ext>>> {_, ext}")
    # 3-3) name부분만 uuid.uuid4()로 덮어쓴 뒤, 변환된 filename을 반환한다
    # https://dpdpwl.tistory.com/77
    # -> uuid로 생성된 랜덤에는 하이픈이 개입되어있는데 split으로 제거한 뒤 합친다. -> replace로 처리하자
    file_name = str(uuid.uuid4()).replace('-', '')
    # print(f"uuid + ext>>> {filename}")
    return file_name, ext


from PIL import Image, ImageOps


def get_extension_from_mime(mime_type):
    """
    MIME 타입으로부터 파일 확장자를 가져오는 함수
    """
    extension = mimetypes.guess_extension(mime_type, strict=True)
    return extension


def create_thumbnail(data, file_path, file_name, mime_type, max_size=(200, 200)):
    # file(X) data로  -> image객체를 만든다.
    # image = Image.open(os.path.join(image_dir, image_name))
    image = Image.open(BytesIO(data))

    # 각 image객체를 사이즈별ㄹ .copy()부터 한 뒤, .thumbnail()메서드로 resize 후 .save()까지 한다.
    copied_image = image.copy()

    # 이미지 크기가 최대 크기보다 큰 경우에만 리사이즈 수행
    if not (copied_image.width > max_size[0] or copied_image.height > max_size[1]):
        return

    # 비율을 유지하면서 큰 쪽에 맞춰서 조절 -> .resize가 알아서 생성
    copied_image = ImageOps.contain(copied_image, max_size, Image.LANCZOS)  # inplace아님(.thumbnail은 inplace)

    # 확장자 없이 저장하기 위해선, format=에 확장자를 지정해줘야하는데, mime_type에서 추출해서 쓴다.
    ext = get_extension_from_mime(mime_type).strip('.')
    ext = 'jpeg' if (ext == 'jpg') else ext

    copied_image.save(file_path / f'{file_name}-thumbnail', optimize=True, quality=95, format=ext)

    return True  # 외부에서 thumbnail 있으면 생성되었다고 알려서 그것으로 url 아니라면, 원본 url
