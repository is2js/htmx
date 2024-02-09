from __future__ import annotations

from io import BytesIO

import boto3
from PIL import Image, UnidentifiedImageError

from config import settings


async def get_image_size_and_ext(image_bytes: bytes) -> tuple:
    try:
        image = Image.open(BytesIO(image_bytes))
    except UnidentifiedImageError:
        raise ValueError("Invalid Image")
    # 2) 원본 size + ext 추출
    image_size = image.size  # (357, 343)
    image_extension = image.format  # PNG
    return image_size, image_extension


async def get_thumbnail_image_obj_and_file_size(
        image_bytes,
        thumbnail_size=(200, 200)
):
    image = Image.open(BytesIO(image_bytes))
    # 3-1) 정사각형 아닐 경우, w or h 짧은 쪽기준으로 crop하여 [정사각형 image객체] 만들기
    #    w > h 인 경우, top0,bottom:h로 다쓰고, 좌우는 w-h/2, w+h/2로 긴 w를 중점으로 h만큼간 절반으로 잡아 crop한다.
    #    h > w 인 경우,  left0,right:w로 다쓰고, 반대로 간다.
    #    w == h 인 경우, 그대로 둔다.
    width, height = image.size
    if width != height:
        if width > height:
            left = (width - height) / 2
            right = (width + height) / 2
            top = 0
            bottom = height
        # elif width < height:
        else:
            left = 0
            right = width
            top = (height - width) / 2
            bottom = (height + width) / 2

        image = image.crop((int(left), int(top), int(right), int(bottom)))
    # 3-2) 원본crop 정사각형 image객체 -> thumbnail image객체로 변환

    image = image.resize(thumbnail_size)
    # 3-3) thumbnail image객체 -> [format='webp'로 image.save()]를 빈 BytesIO에 할당하여
    #                             thumbnail_buffered를 만들어야, file_size를 추출할 수 있다.
    #      buffer + image.save() -> buffer.get_value()  + len()으로 file_size 추출
    thumbnail_buffered = BytesIO()
    image.save(thumbnail_buffered, format='WEBP')
    thumbnail_file_size = len(thumbnail_buffered.getvalue())  # 8220

    return image, thumbnail_file_size


async def resize_and_get_image_obj_and_file_size(image_bytes, convert_size):
    current_image = Image.open(BytesIO(image_bytes))

    # 정해진 해당size로 resize
    current_width, current_height = current_image.size
    ratio = current_width / current_height
    current_image = current_image.resize((convert_size, int(convert_size / ratio)))

    # webp포맷으로 inplace후, file_size추출
    convert_buffered = BytesIO()
    current_image.save(convert_buffered, format="WEBP")
    current_image_file_size = len(convert_buffered.getvalue())

    return current_image, current_image_file_size


async def get_s3_url(image_group_name, s3_file_name):
    return f"https://{settings.aws_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{image_group_name}/{s3_file_name}"


async def s3_image_upload(image_file_name, image_group_name, image_obj):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region
    )

    buffered = BytesIO()
    image_obj.save(buffered, format="WEBP")

    s3.put_object(
        Bucket=settings.aws_bucket_name,
        Key=f"{image_group_name}/{image_file_name}",
        Body=buffered.getvalue(),
        ACL="public-read",
        ContentType="image/webp",
    )

    return f"https://{settings.aws_bucket_name}.s3.{settings.aws_region}.amazonaws.com/{image_group_name}/{image_file_name}"


async def background_s3_image_data_upload(to_s3_upload_data_per_size):
    for size, data in to_s3_upload_data_per_size.items():
        image_obj = data['image_obj']
        image_group_name = data['image_group_name']
        image_file_name = data['image_file_name']

        await s3_image_upload(image_file_name, image_group_name, image_obj)
