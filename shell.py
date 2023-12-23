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

#### custom import 시작=========================
# sqlalchemy session객체 추가
globals()['db'] = SessionLocal()
#### custom import 끝=========================



embed(colors='neutral', banner2=banner)