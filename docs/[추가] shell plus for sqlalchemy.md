- 참고 사이트: https://www.pedaldrivenprogramming.com/2021/01/shell-plus-for-sqlalchemy/

1. root에 `shell.py`를 아래와같이 생성 후, 터미널에서 `python shell.py`로 실행한다.
    ```python
    from IPython import embed
    
    # TODO: 자신의 Base객체 및, session객체 생성 경로
    from database import Base, SessionLocal
    
    banner = 'Additional imports:\n'
    
    # TODO: 자신의 app객체 경로
    from main import app
    banner = f'{banner}from app.main import app\n'
    
    for clzz in Base.registry._class_registry.values():
        if hasattr(clzz, '__tablename__'):
            globals()[clzz.__name__] = clzz
            import_string = f'from {clzz.__module__} import {clzz.__name__}\n'
            banner = banner + import_string
    
    # custom import 추가=========================
    
    # 1. session객체 추가
    globals()['db'] = SessionLocal()
    
    # custom import 추가=========================
    
    embed(colors='neutral', banner2=banner)
    ```