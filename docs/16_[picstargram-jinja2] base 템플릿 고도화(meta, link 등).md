- 참고 유튜브(flask+htmx): https://www.youtube.com/watch?v=O2Xd6DmcB9g&list=WL&index=8&t=1842s

### base template에 jinja문법을 이용한 고도화
#### meta태그
1. **head태그에 있는 `기본값이 있고 + 변동가능성`이 있을 때 쓰는 `block`으로 meta태그변수들을 추가한다.**
    - **이 때, canonical_link(파라미터없는url)는 변수가 안던져지면 request를 이용해서 절대주소로 작성되게 한다.**
    - **`{%- set %} {% endset %-}`을 이용하여, block속 변수값들을 맨위에서 받아놓고, html에 jinja변수 {{}}로 사용하게 한다.**
    - title안에 if subtitle이 있으면, ` - subtitle`이 붙어서 title태그를 작성하게 한다.
        - **이 때, page_subtitle의 block에 기본값을 안넣어두는게 낫다. 기본값 넣어놓으면, 상세페이지에서도 `내프로필-기본subtitle`형태로 title태그가 잡히기 때문**
    - **fastapi에서는 request.base_url(:8000/까지) + request.path(picstragram/~~)을 합친 것이 `request.url._url`이다. .url만 하면 객체값이며 str이 아니어서 변수로 못쓴다.**
    ```html
    {%- set page_site_name %}{% block site_name %}픽스타그램{% endblock %}{% endset -%}
    {%- set page_title %}{% block title %}메인{% endblock %}{% endset -%}
    {%- set page_subtitle %}{% block subtitle %}{% endblock %}{% endset -%}
    {%- set page_description %}{% block description %}최신 포스트들을 게시합니다.{% endblock %}{% endset -%}
    {%- set page_og_image %}{% block og_image %}{{ url_for('static', path='icon/logo-og.png') }}{% endblock %}{% endset -%}
    {%- set page_canonical_link %}{% block canonical_link %}{% endblock %}{% endset -%}
    {%- block html %}
        <!DOCTYPE html>
        <html lang="en">
        <head>
            {%- block meta %}
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <meta charset="utf-8">
                <meta name="description" content="{{ page_description }}">
                <meta property="og:site_name" content="{{ page_site_name }}">
                <meta property="og:title" content="{{ page_title }}{% if page_subtitle %} - {{ page_subtitle }}{% endif %}">
                <meta property="og:description" content="{{ page_description }}">
                <meta property="og:url" content="
                        {%- if page_canonical_link %}{{ page_canonical_link }}{% else %}{{ request.url._url }}{% endif -%}">
                <meta property="og:type" content="website">
                <meta property="og:image" content="{{ page_og_image }}">
                <meta name="twitter:card" content="summary_large_image">
                <meta name="twitter:title"
                      content="{{ page_title }}{% if page_subtitle %} - {{ page_subtitle }}{% endif %}">
                <meta name="twitter:description" content="{{ page_description }}">
                <meta name="twitter:image" content="{{ page_og_image }}">
            {% endblock meta %}
    ```


#### link태그 아이콘
1. 아이콘들은 link태그로 들어간다. static으로 연동시켜준다.
    - **mask-icon은 color="#fffff"를 맨 뒤에 추가로 준다.**
    ```html
    {%- block link %}
        <link rel="shortcut icon" href="/favicon.ico">
        <link rel="icon" sizes="192x192" href="{{ url_for('static', path='icon/logo-192x192.png') }}">
        <link rel="apple-touch-icon" href="{{ url_for('static', path='icon/logo-180x180.png') }}">
        <link rel="mask-icon" href="{{ url_for('static', path='icon/safari-pinned-tab.svg') }}" color="#ffffff">
        <link rel="manifest" href="{{ url_for('static', path='manifest.json') }}">
    {% endblock -%}
    ```
   

2. canonical link는 변하지 안흔ㄴ 것으로서, backend에서 주는게 있으면 쓴다.
    - og에서는 없으면 현재페이지의 url을 넣어줬지만, 이건 있으면 주기

#### title
- `og`에서는 title( - subtitle) 형태였지만, `페이지 title`은 subtitle이 없으면 page_site_name을 title에 붙여준다.
    - **그러므로, 애초에 page_subtitle의 기본값은 안넣어놓는 게 낫다. 안줫는데도, 기본값이 `내프로필 - 기본subtitle`로 붙어다니기 때문**
    ```html
    <title>{{ page_title }}{% if page_subtitle %} - {{ page_subtitle }}{% else %} - {{ page_site_name }}{% endif %}</title>
    ```
  

#### boostrap 등 기본 css + style.css 모두 css block에 + 자식이 쓸 예비자리는 extrastyle block으로 비워두기
- 만약, extrastyle을 덮어쓰면 다 뭉게지니, `super()`랑 같이 쓸 듯하다.
    ```html
    {% block css %}
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet"
          integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3"
          crossorigin="anonymous"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.min.css"/>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600&display=swap" rel="stylesheet">
    <!-- Custom style -->
    <link rel="stylesheet" href="{{ url_for('static', path='css/style.css') }}"/>
    <!-- Custom style -->
    {% endblock css %}

    {% block extrastyle %}
    {% endblock extrastyle %}
    ```
  


#### index.html 등 상속 자식 html은
- content외 기본적으로 `meta, css, title` 등을 block으로서 그대로 쓰든, 덮어쓰든 하면 된다.
- meta와 css는 거의 super()로 그대로 상속해서 쓰고, 필요시 수정할 것 같다.
    ```html
    {% extends 'picstragram/_page_base.html' %}
    
    {% block meta %} {{ super() }} {% endblock meta %}
    {% block css %} {{ super() }} {% endblock css %}
    {% block title %}메인{% endblock title %}
    {% block subtitle %}최신포스트{% endblock subtitle %}
    
    {% block content %}
    ```
  

- index.html, me.html, user.html 도 block으로 부모를 super() 그대로 이용 or 덮어쓰기 해보자.
    ```html
    {% extends 'picstragram/_page_base.html' %}
    
    {% block meta %} {{ super() }} {% endblock meta %}
    {% block css %} {{ super() }} {% endblock css %}
    {% block title %}내 프로필{% endblock title %}
    
    {% block nav_top %}
    ```
    ```html
    {% extends 'picstragram/_page_base.html' %}
    
    {% block meta %} {{ super() }} {% endblock meta %}
    {% block css %} {{ super() }} {% endblock css %}
    {% block title %}유저 정보{% endblock title %}
    
    {% block nav_top %}
    ```