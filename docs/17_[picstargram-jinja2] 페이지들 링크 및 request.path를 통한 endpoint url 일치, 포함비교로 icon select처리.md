- 참고 유튜브(flask+htmx): https://www.youtube.com/watch?v=O2Xd6DmcB9g&list=WL&index=8&t=1842s

### 페이지들 연결
1. index.html에서, me / user.html로 넘어가는 a링크들에 route name으로 연결해준다.
    - me.html은, `_page_nav_bottom`에서 클릭시 넘어가는 a태그가 있다.
    ```html
    <li>
        {#<a href="me.html">#}
        <a href="{{ url_for('pic_me') }}">
            <img src="{{ url_for('static', path='images/user1.png') }}" class="profile" alt="내 공간">
        </a>
    </li>
    ```
    - user.html은, 아직 route경로가 미완성이지만, index.html의 각 post들에서, 사진이나 유저명을 클릭하면 넘어가는 a태그가 있다.
    ```html
    <article class="post">
        <div class="header">
            {#<a href="user.html"><img src="images/user2.png" class="profile" alt="사용자2" /></a>#}
            <a href="{{ url_for('pic_users') }}">
                <img src="{{ url_for('static', path='images/user2.png') }}" class="profile" alt="사용자2"/>
            </a>
            <a href="{{ url_for('pic_users') }}">
                <div class="name">사용자2</div>
            </a>
            <div class="time">1시간</div>
        </div>
    ```
   


### request.path를 이용한 select처리
1. 메인메뉴가 nav-bottom에 있으므로, `_page_nav_bottom.html`에서 `request.path`의 포함여부를 jinja2 를 이용해서 처리한다.
    - **현재 home만 선택/비선택이 가능하고, 나머지메뉴는 미구현이거나 modal을 띄우는 상태다.**
    - `request.path`는 포트 다음의 `@app.get('')`에 적어준 경로만 나온다. 
    - **`/picstragram/`으로 끝나면 /picstragram/으로, `/picstragram`으로 적으면 `/picstragram`만 나온다.**
        - 뒤에 `/`를 달아주는게 안전하다고 하니, 모두 달아주고, request.path의 비교도 url과 동일하게 해서 비교하자.

    ```html
    <header class="nav-bottom">
        <ul class="menu">
            <li>
                <a href="{{ url_for('pic_index') }}">
                    {% if '/picstragram/' == request.path %}
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                             class="bi bi-house-door-fill" viewBox="0 0 16 16">
                            <path d="M6.5 14.5v-3.505c0-.245.25-.495.5-.495h2c.25 0 .5.25.5.5v3.5a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293L8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5Z"/>
                        </svg>
    
                    {% else %}
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
                             class="bi bi-house-door" viewBox="0 0 16 16">
                            <path d="M8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4.5a.5.5 0 0 0 .5-.5v-4h2v4a.5.5 0 0 0 .5.5H14a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293L8.354 1.146ZM2.5 14V7.707l5.5-5.5 5.5 5.5V14H10v-4a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5v4H2.5Z"/>
                        </svg>
                    {% endif %}
                </a>
            </li>
    ```