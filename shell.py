from shellplus import start_ipython, import_target, import_folder

# 1) 내 파일 속 python 객체 import
import_target('/main.py', 'app')
import_target('/database.py', 'Base', with_table=True)
import_target('/database.py', 'SessionLocal', instance_name='session')
# from main import app
# from database import Base, SessionLocal
# from models import Film, Employee, Department
# session = SessionLocal()


# import_target('schemas/picstargrams.py', 'PostSchema')
# import_target('schemas/abc/picstargrams.py', 'TagCreateReq')
# import_target('schemas/picstargrams.py', ['TagCreateReq', 'PostSchema'])
import_target('schemas\picstargrams.py', '*')
# from schemas.picstargrams import *

import_target('enums/messages.py', '*')


# 3) 폴더/*.py의 모든 모듈들을 import하기
# import_folder('schemas')
# from schemas.picstargrams import *
# from schemas.tracks import *
# from schemas.utils import *


# 4) 설치 패키지 from -> 경로 / import -> * or 'select' or ['select', 'or_']
# import_target('sqlalchemy', '*', is_package=True)
# import_target('sqlalchemy', 'select', is_package=True)
import_target('sqlalchemy', ['select', 'or_'], is_package=True)
# from sqlalchemy import select, or_


start_ipython()
