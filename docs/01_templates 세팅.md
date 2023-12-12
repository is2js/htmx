- 참고유튜브: https://www.youtube.com/watch?v=yu0TbJ2BQso&list=PL-2EBeDYMIbSppj2GYHnvpZ9W69qmkInS

1. `requirements.txt` 작성 및 자동 설치부터
    - pycharm이라면, freeze 부터 하고, 추가설치할 것은 버전 명시해서 설치
    - `Jinja2==3.0.3` + uvicorn 삭제 후 `uvicorn==0.21.0`

2. templates/index.html 만들고, 터미널에서 `code .`으로 vscode 열기
3. main.py에 fastapi templates 문서가서 필요한 패키지 복붙 + template 기본 코드 복붙
    ```python
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    
    app = FastAPI()
    
    templates = Jinja2Templates(directory="templates")
    
    
    @app.get("index/")
    async def index(request: Request, response_class=HTMLResponse):
        context = {'request': request}
        return templates.TemplateResponse("index.html", context)
    ```
   

4. index.html을 `html:5`로 열어주고, htmx + tailwindcss.com head에 걸어주기
    ```html
    <!-- htmx -->
    <script src="https://unpkg.com/htmx.org@1.6.1"
            integrity="sha384-tvG/2mnCFmGQzYC1Oh3qxQ7CkQ9kMzYjWZSNtrRZygHPDDqottzEJsqS4oUVodhW" crossorigin="anonymous">
    </script>
    <script>
        htmx.config.useTemplateFragments = true; // table row 조작을 위한 설정
        // 없으면 htmx-swap 에러가 남 : htmx.org@1.6.1:1 Uncaught TypeError: e.querySelectorAll is not a function
    </script>
    <!-- css -->
    <script src="https://cdn.tailwindcss.com"></script>
    ```