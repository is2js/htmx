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
    - **thumbnail클릭시, `modal + srcset`을 이용하여 `cutoff에 따른 size별 image를 렌더링`하게 됩니다.**

5. frontend framework나 jquery 등의 요청이 아닌 `미들웨어에서 refresh token`을 사용하는 도전도 해보았습니다.

### 데모

![58cd8530-1606-4cb2-be9b-13633a7000e0](https://raw.githubusercontent.com/is2js/screenshots/main/58cd8530-1606-4cb2-be9b-13633a7000e0.gif)
