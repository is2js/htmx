- 장고+modal+htmx 참고 유튜브: https://www.youtube.com/watch?v=3dyQigrEj8A&list=PLh3mlyFFKnrmo-BsEAUtfc9eazfswjvAc
- 로그인 참고 깃허브(fastapi + htmx + pydantic): https://github.dev/sammyrulez/htmx-fastapi/blob/main/templates/owner_form.html
- tagify 정리
  블로그: https://inpa.tistory.com/entry/Tagify-%F0%9F%93%9A-%ED%95%B4%EC%8B%9C-%ED%83%9C%EA%B7%B8tag-%EC%9E%85%EB%A0%A5%EC%9D%84-%EC%9D%B4%EC%81%98%EA%B2%8C-%EA%B0%84%ED%8E%B8%ED%9E%88-%EA%B5%AC%ED%98%84-%EC%82%AC%EC%9A%A9%EB%B2%95

#### 패키지화

1. 패키지화 -> import하는 함수들을 따로 패키지내 `imports.py`에 모으고, ipython을 시작하며 print하는 함수를 `main.py`에 만든다.
    - **init.py의 가장 상단에 `하위모듈에서도 사용될 전역변수`를 선언해놓고**
    - .import되는 imports.py 내에서 전역변수에 입력시키고
    - .import되는 main.py 내에서 import_map과 banner_map을 사용되게 한다.
    - 결국 init.py의 전역변수 + 하위모듈들을 외부 shell.py에서 사용할 수 있게 된다.

    ```python
    # shellplus/__init__.py
    from collections import OrderedDict
    
    # 하위모듈이 사용할 전역 데이터 -> 하위모듈에서 채우고 -> import한 외부 shell.py에서 globals() 등에 입력할 때 사용한다.
    banner_map = OrderedDict()
    import_map = dict()
    
    from .imports import import_target, import_folder
    from .main import start_ipython
    
    ```
    ```python
    # shell.py
    from shellplus import start_ipython, import_target, import_folder
    
    import_target('/main.py', 'app')
    import_target('/database.py', 'Base', with_table=True)
    import_target('/database.py', 'SessionLocal', instance_name='session')
    
    import_target('schemas/picstagrams.py', '*')
    
    import_target('sqlalchemy', ['select', 'or_'], is_package=True)
    
    
    start_ipython()
        
    ```

#### imports.py

1. **`imports.py`에는 텍스트로 root에서부터 from에 쓰일 `상대경로`를 입력하면, import `해당 모듈내 특정 python객체` or `Base객체와 내부 테이블들`
   or `특정객체의 instance객체` / import `*(모든객체)` / import `특정패키지(폴더) 내 모든 *.py들` 할 수 있게 제작했다.**
    - "`/ or \`"를 사용한 상대경로 입력 -> re.split("[/|\\]", path ) -> Path(*parts)로 `/`로 `os에 맞는 상대경로`의 Path 제작
        - **splite을 정규표현식으로 할려면, `re모듈.split(pattern, 대상)`을 사용해야한다**
        - **lstrip은 바로 정규식 사용이 가능하다.**
    - `schemas/picstagrams.py`
      or `schemas/picstragrams.py` -> `['schemas', 'picstagrams.py']` -> `Path('schemas', 'picstagrams.py')` -> path객체(
      os에 맞는 구분자)`schemas\picstagrams.py`
        - 참고로 Path객체.resolve()는 절대주소로 만든다. 여기선 쓸 필요없다.
    - 맨마지막이 `x.py`이므로 `path객체.stem`하면, 확장자를 제외한 모듈명만 나와서 import_module()안에 넣으면, 해당 python모듈을 가져올 수 있다.
    - 하지만, split한 parts가 1개 이상인 경우, `path객체.stem`은 맨 마지막만 파일의 모듈명만 나오므로, `path.pars[:-1]`로 모듈명전까지의 경로를 가져와 `list()`로 만든
      뒤, `'.'.join()`으로 import_module()을 위한 상대경로로 변경해준다.
    - import된 module객체에서 `.getattr(모듈, 타겟객체명)`으로 실제 가져오고 싶은, target객체를 가져온다.
    - import_map에 `.으로 연결된 from_path`와 `target`모듈을 init의 impor_map에 넣어준다.
    - 반복되는 경로 입력을 `set_banner_map`을 함수로 만든 뒤, key가 존재하는지 확인하고, value에도 포함안되어있으면 넣어준다.
        - 이 때, key(from_path)마다 value를 list로 넣어주는데, `dict.setdefault( key, 기본값).기본값에 add하는 함수()`를 이용해, 기본값을 가진 dict에
          넣어준다
    - 만약, target이 `*`라면, **import된 module에 `dir()`을 매겨 명령어를 순회한 뒤, `_`로 시작하는 것을 제외하고 모아서 -> `getattr(모듈, _제외한 pythom객체)`
      를 통해 전부 각각의 모듈내 객체들을 가져온 뒤, import_map.update( dict genearator )로 넣어서 1개씩 업데이트 시킨다?**
        - 이 때, banner_map에 넣어줄 이름을 target모듈.`__name__`으로 꺼내보고 없으면, 사용자가 넣어준 target_object(모듈명)으로 넣어준다.
    - 만약, 타겟모듈이 클래스라서 `()`의 인스턴싱한 객체까지 import시키려고 한다면, `isinstance_name='객체명'`을 받아서, 객체명을 import_map에 넣어준다.
        - banner_map에도 추가해줘야한다. `객체명 = 타겟모듈()` 형태로 넣어줘야한다.
    - 만약, Base객체를 import하는 목적이 해당 테이블들을 import하고자 한다면, `with_table=True`옵션으로 같이 가져오게 한다.
        - target모듈(Base)`.registry._class_registry.values()`로 테이블 class(model_)들을 순회할 수 있다.
        - `__tablename__`이 선언된 sqlalchemy model일 때만 처리하며, `model_.__name__`과 `model_`을 각각 import_map에 넣어주고,
          from_path는 `model.__module__`로 가져온다.
    - 폴더 내부의 전체 *.py를 import한다면
      - **`상대path객체.glob('*.py')`를 순회한 뒤, `.stem`으로 파일명만 가져와서 순회하며**
      - import_module -> dir()순회 with _필터링 -> from_path + import_value를 import_map과 banner_map에 넣어준다. 
    ```python
    from __future__ import annotations
    
    import re
    from importlib import import_module
    from pathlib import Path
    
    from . import banner_map, import_map
    
    
    def set_banner_map(from_path, import_value):
        if (not (value_list := banner_map.get(from_path))) or import_value not in value_list:
            banner_map.setdefault(from_path, []).append(import_value)
    
    
    def import_target(
            relative_module_path, target_object_list,
            instance_name: bool | str = False,
            is_package=False,
            with_table=False
    ):
        if not isinstance(target_object_list, (list, tuple)):  # Sequence나 Iterable을 주면 'string'을 순회 인식해버림.
            target_object_list = [target_object_list]
    
        if is_package:
            from_path = relative_module_path
            imported_module = import_module(f'{from_path}')
    
            for target_object in target_object_list:
                if target_object == '*':
                    # globals().update(
                    #     {name: getattr(module_of_target, name) for name in dir(module_of_target)
                    #      if not name.startswith('_')}
                    # )
                    import_map.update(
                        {
                            module_name: getattr(imported_module, module_name) for module_name in dir(imported_module)
                            if not module_name.startswith('_')
                        }
                    )
    
                    # banner_map.setdefault(stem, []).append(target_name)
                    set_banner_map(from_path, target_object)
    
                    break
    
                target = getattr(imported_module, target_object)  # TODO: create_app 팩토리라면, 거내서 생성까지
                # globals().update({target_name: target})
                import_map.update({target_object: target})
                target_object = getattr(target, '__name__', target_object)
    
                # banner_map.setdefault(stem, []).append(target_name)
                set_banner_map(from_path, target_object)
            return
    
        # 1) "/" or "\" 를 사용한 사용자 상대경로 입력 -> re.split(pattern, 대상) -> Path(*list)로 상대경로 Path 제작
        relative_module_path = relative_module_path.lstrip(r'[/|\\]')
        relative_module_path_parts = re.split(r'[/|\\]', relative_module_path)
    
        relative_path_of_module = Path(*relative_module_path_parts)  # .resolve() # 상대주소만 이용할거면 .resolve()를 통한 C:// 절대경로는 (X
    
        #  schemas\picstagrams.py
        # 참고)
        # parent_paths = [part for part in relative_path_of_module.parents
        #                 if relative_path_of_module.name not in part.parts]
        # parent_paths  >> [WindowsPath('schemas'), WindowsPath('.')]
    
        for target_object in target_object_list:
            if len(relative_module_path_parts) > 1:
                # print(f"depth 1개이상 >>")
                # parent_paths = [part for part in module_of_target_path.parents
                #                 if module_of_target_path.name not in part.parts]
                # print(f"parent_paths >> {parent_paths}")
                # parent_paths >> [
                # WindowsPath('C:/Users/cho_desktop/PycharmProjects/htmx/schemas'),
                # WindowsPath('C:/Users/cho_desktop/PycharmProjects/htmx'),
                # WindowsPath('C:/Users/cho_desktop/PycharmProjects'),
                # WindowsPath('C:/Users/cho_desktop'),
                # WindowsPath('C:/Users'),
                # WindowsPath('C:/')
                # ]
    
                # relative_path = module_of_target_path.relative_to(root_path)
                # print(f"relative_path >> {relative_path} in {__file__}")
    
                # relative_path >> schemas\picstagrams.py
                path_elements = '.'.join(
                    list(relative_path_of_module.parts[:-1]) + [relative_path_of_module.stem])
                # print(f"path_elements  >> {path_elements}")
                # path_elements  >> schemas.picstagrams
                from_path = path_elements
            else:
                from_path = relative_path_of_module.stem
    
            # print(f"stem  >> {stem}")
            imported_module = import_module(f'{from_path}')
    
            if target_object == '*':
                # globals().update(
                #     {name: getattr(module_of_target, name) for name in dir(module_of_target)
                #      if not name.startswith('_')}
                # )
                import_map.update(
                    {name: getattr(imported_module, name) for name in dir(imported_module)
                     if not name.startswith('_')}
                )
                banner_map.setdefault(from_path, []).append(target_object)
                break
    
            target = getattr(imported_module, target_object)
            # globals().update({target_name: target})
            import_map.update({target_object: target})
    
            target_object = getattr(target, '__name__', target_object)
            # banner_map.setdefault(stem, []).append(target_name)
            set_banner_map(from_path, target_object)
    
            if instance_name:
                # globals().update({instance_name: target()})
                import_map.update({instance_name: target()})
    
                from_path = 'instance'
                import_value = f'{instance_name} = {target_object}()'
                # if (not (value_list := banner_map.get(from_path))) or import_value not in value_list:
                #     banner_map.setdefault(from_path, []).append(import_value)
                set_banner_map(from_path, import_value)
    
            if target_object == 'Base' and with_table:
                for model_ in target.registry._class_registry.values():
                    if hasattr(model_, '__tablename__'):
                        # globals()[clzz.__name__] = clzz
                        import_map.update({model_.__name__: model_})
    
                        from_path = model_.__module__
                        import_value = model_.__name__
                        # if (not (value_list := banner_map.get(from_path))) or import_value not in value_list:
                        #     banner_map.setdefault(from_path , []).append(import_value)
                        set_banner_map(from_path, import_value)
    
    
    def import_folder(relative_folder_path):
        relative_folder_path = relative_folder_path.lstrip(r'[/|\\]')
        relative_folder_path_parts = re.split(r'[/|\\]', relative_folder_path)
        relative_path_folder = Path(*relative_folder_path_parts)  # .resolve() # 상대주소만 이용할거면 .resolve()를 통한 C:// 절대경로는 (X)
    
        # relative_path = folder_relative_path.relative_to(root_path)
        relative_import_module_path = '.'.join(list(relative_path_folder.parts))
    
        for module_path in relative_path_folder.glob('*.py'):
            module_name = module_path.stem  # xxx.py의 경로에서 .stem으로 모듈명만 추출
    
            # module = import_module(f'{relative_import_module_path}.{module_name}')
            imported_module = import_module(f'{relative_import_module_path}')
    
            for module_name in dir(imported_module):
                if module_name.startswith('_'):
                    continue
                # globals().update({name: getattr(module, name)})
                import_map.update({module_name: getattr(imported_module, module_name)})
    
            from_path = f'{relative_import_module_path}.{module_name}'
            import_value = '*'
            # 이미 해당fromapath의 모듈list에 들어가 있는 모듈명이면 제외
            set_banner_map(from_path, import_value)
    
    ```

#### shellplus/main.py
1. 하위 모듈들이 받아서 넣어놓은 init의 전역변수를 가져와, `globals()`안에 넣어준다.
    - banner_map도 순회하며 출력해준다. 
    - **이 때, `IPython`패키지의 `embed모듈`로 ipython이 실행되게 한다. colors =, banner2= 옵션으로 색과 import string을 넣어준다.**
```python
from IPython import embed

from shellplus import banner_map, import_map


def start_ipython():
    # 1) import
    # for from_, import_ in import_map.items():
    #     globals().update({from_:import_})
    globals().update(**import_map)

    # 2) print
    banner = '■■■■■■■■■■■■ Shellplus for FastAPI ■■■■■■■■■■■■\n'
    # 일반 모듈
    for stem, target_list in banner_map.items():
        if stem == 'instance':
            continue
        banner += f"from {stem} import {', '.join(target_list)}\n"
    banner += '\n'

    # instancing
    instance_string_list = banner_map.get('instance', [])
    banner += '\n'.join(instance_string_list)

    banner += '\n'

    embed(colors='neutral', banner2=banner)

```

#### root/shell.py
1. 정의한 모듈들을 가져와서 터미널에 `python shell.py`로 실행한다.
    - 이 때, start_ipython()메서드안에서 패키지내 전역변수를 내부사용해서 처리한다.
    ```python
    # shell.py
    from shellplus import start_ipython, import_target, import_folder
    
    # 1) 내 파일 속 python 객체 import
    import_target('/main.py', 'app')
    import_target('/database.py', 'Base', with_table=True)
    import_target('/database.py', 'SessionLocal', instance_name='session')
    # from main import app
    # from database import Base, SessionLocal
    # from models import Film, Employee, Department
    # session = SessionLocal()
    
    
    # import_target('schemas/picstagrams.py', 'PostSchema')
    # import_target('schemas/abc/picstagrams.py', 'TagCreateReq')
    # import_target('schemas/picstagrams.py', ['TagCreateReq', 'PostSchema'])
    import_target('schemas\picstagrams.py', '*')
    # from schemas.picstagrams import *
    
    
    # 3) 폴더/*.py의 모든 모듈들을 import하기
    # import_folder('schemas')
    # from schemas.picstagrams import *
    # from schemas.tracks import *
    # from schemas.utils import *
    
    
    # 4) 설치 패키지 from -> 경로 / import -> * or 'select' or ['select', 'or_']
    # import_target('sqlalchemy', '*', is_package=True)
    # import_target('sqlalchemy', 'select', is_package=True)
    import_target('sqlalchemy', ['select', 'or_'], is_package=True)
    # from sqlalchemy import select, or_
    
    
    start_ipython()
    
    ```