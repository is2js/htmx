import datetime
from math import inf


# def feed_time(feed_datetime: datetime, is_feed: bool = True, k: int = 8):
def feed_time(feed_datetime: datetime, is_feed: bool = True):
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    wd = weekdays[feed_datetime.weekday()]
    # ymd_format = "%Y.%m.%d %H:%M({})".format(wd)
    ymd_format = "%Y.%m.%d %H:%M".format(wd)

    # is_feed형태일 때, k = 1 이라면 -> k일 이상부터는, 년월일, 그전에는 피드시간(yyyy.mm.dd h:m)
    # cf) 일단위를 넘어가면 전부 yyyy.mm.dd
    if not is_feed:
        formatted = feed_datetime.strftime(ymd_format.encode('unicode-escape').decode()).encode().decode(
            'unicode-escape')
    else:
        current_time = datetime.datetime.now()
        ## total 초로 바꾼다.
        total_seconds = int((current_time - feed_datetime).total_seconds())
        ## 어느 단위에 걸리는지 확인한다.
        periods = [
            ('year', inf, '년 전'),  # new) 비교후 걸리면, 이전 것으로 하는데, 맨 마지막을 가장 큰 것을 해놓고, 무조건 걸리게.
            ('year', 60 * 60 * 24 * 365, '년 전'),
            ('week', 60 * 60 * 24 * 7, '주 전'),
            ('day', 60 * 60 * 24, '일 전'),
            ('hour', 60 * 60, '시간 전'),
            ('minute', 60, '분 전'),
            ('second', 1, '초 전'),
        ]
        prev_unit = 0
        prev_ment = '방금 전'

        for period, unit, ment in reversed(periods):
            ## new) 업뎃한 prev_unit가 가장 큰 unit인 경우, 또다른 종착역으로서 더이상 업뎃 로직X 종착역 -> 업뎃판단이 아니라 바로 년단위로 처리
            if total_seconds <= unit:
                # (1) 큰 것부터 보면서 잘라먹고 나머지 다시 처리하는 식이 아니라
                # 작은단위부터 보고 그것을 못 넘어선 경우, 그 직전단위 prev_unit로 처리해야한다.
                # , 해당단위보다 클 경우, (ex> 61초 -> 1초보다, 60(1분)보단 큰데 60*60(1시간보단)작다  => 60,60직전의 1분으로처리되어야한다)
                #    나머지하위단위들을 total_seconds에 업뎃해서 재할당한다. -> 버린다.

                # (3) 1초보다 작아서, prev 0으로 나누는 경우는 그냥 방금전
                if not prev_unit:
                    value = ''
                else:
                    value, _ = divmod(total_seconds, prev_unit)
                # (2) 몫 + 멘트를 챙긴다
                formatted = str(value) + prev_ment
                # (3) [k][일] 이상 지나간, 그냥 년월일로 하자

                # late_unit = 60 * 60 * 24
                # if prev_unit == late_unit and value >= k:
                #### new2) k일 이상지나면 X -> 10년이상되면,yyyy.mm.dd로 / 아니라면 is_feed인 이상, x년 전, 방금 전
                year = periods[1][1]
                if total_seconds > 10 * year:
                    formatted = feed_datetime.strftime(ymd_format.encode('unicode-escape').decode()).encode().decode(
                        'unicode-escape')
                break
            else:
                ## 현재단위보다 크면, 다음단위로 넘어가되 prev업뎃
                prev_unit = unit
                prev_ment = ment

    return formatted


if __name__ == "__main__":
    from utils import D

    print(feed_time(datetime.datetime.now() - datetime.timedelta(seconds=62), is_feed=False))
    # D유틸을 이용해 utc(한국-9시간)기준으로 now -> -9시간은 기본으로
    print(feed_time(D.datetime(diff_hours=9, diff_seconds=-62), is_feed=False))

    print(feed_time(datetime.datetime.now() - datetime.timedelta(seconds=119), k=8))
    # D유틸을 이용해 utc(한국-9시간)기준으로 now -> -9시간은 기본으로
    print(feed_time(D.datetime(diff_hours=9, diff_seconds=-119), k=8))

    # is_feed=False
    # 2023.12.26 22:20
    # 2023.12.26 22:22

    # is_feed=True + k=8일이상부터는 yyyy.mm.dd
    # 1분 전
    # 방금 전
