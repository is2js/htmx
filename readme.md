### 스택
- fastapi + htmx + alpinejs + no database(json) + AWS S3

### 목표
1. `ORM, sql도입없이 json`을 백엔드로 선정하여 `빠른 프로토타입 개발`에 목표를 두었습니다.
    - 초기데이터 1~2개만 app reload시마다 활용. 다른 프로젝트 개발시 재활용 가능.
    - **그러나 편리한 ORM없이 직접 관계형 모델을 흉내내는 것이 더 시간이 많이 걸리고 복잡한 작업이었습니다.**
2. 특히, `htmx`를 사용하여, 백엔드개발자로서 frontend framework에 대한 학습이나 투자 없이 `화면전환이나 실시간 업데이트를 server-side에서 rendering하는 것을 목표`로 하였습니다.
3. 반드시 필요한 `프론트 상태관리는 alpinejs`를 사용하였습니다.
4. `AWS S3`를 사용하여, 1개의 이미지에 대해 `thumbnail(기본) + 정해진 size들(512, 1024, 1920)`까지 기본 생성하여 저장되도록 합니다.
    - **업로드 -> `s3에 webp`형식으로 thumbnail만 동기적으로 처리하여 view에 표시 + 512, 1024px은 background 업로드**
    - **다운로드 -> `원본파일명.원본확장자`를 512, 1024px로 다운로드 할 수 있음.**
    - **thumbnail클릭시, `modal + srcset`을 이용하여 `cutoff에 따른 size별 최적의 image를 렌더링`하게 됩니다.**

5. frontend framework나 jquery 등의 요청이 아닌 `미들웨어에서 refresh token`을 사용하는 도전도 해보았습니다.

### 데모

1. **로그인/회원가입 화면을 `htmx`를 이용하여, 화면전환 없는 `modal`  + `tab 전환`이 가능하다.**

    ![a8a3b931-1301-475e-8876-8841cee9d03c](https://raw.githubusercontent.com/is2js/screenshots/main/a8a3b931-1301-475e-8876-8841cee9d03c.gif)

2. **post를 생성하면, thumbnail+512+1024+1960 size별 `S3에는 uuid + webp형식` , `사용자 다운로드시 원본파일명 + 원본확장자형식`으로 다운로드**

    ![043c1897-7a6b-4efc-9447-96498d6bd096](https://raw.githubusercontent.com/is2js/screenshots/main/043c1897-7a6b-4efc-9447-96498d6bd096.gif)

3. **`javascript + jquery가 없는 것`이 장점인 htmx스택에서, refresh token을 middelware에서 사용하는 방식을 최초 시도해 보았음.**

    ![f3c54017-d8bf-4c3c-b58d-ecd33f27643b](https://raw.githubusercontent.com/is2js/screenshots/main/f3c54017-d8bf-4c3c-b58d-ecd33f27643b.gif)

4. **bootstrap `modal과 toast의 부모태그를 지속 재활용`하여 base.html에 1개만 존재하면, 모든 상속 템플릿 html에서 쉽게 호출 가능**

    ![64913b77-605f-4e2b-9add-13bb18edbf9a](https://raw.githubusercontent.com/is2js/screenshots/main/64913b77-605f-4e2b-9add-13bb18edbf9a.gif)

5. `alpinejs`를 이용하여 `front에서의 동적인 상태관리`를 통해, `댓글입력창의 활성 + 답글입력창의 활성 및 focus를 조정`한다.
    ![88de53d2-6115-404b-aba0-cc17e9b673b3](https://raw.githubusercontent.com/is2js/screenshots/main/88de53d2-6115-404b-aba0-cc17e9b673b3.gif)