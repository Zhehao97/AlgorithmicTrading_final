import holidays as hol
import datetime as dt
from dateutil.relativedelta import relativedelta

def holiday_adjust(trade_date, delta):
    forward_date = trade_date + delta
    year = forward_date.year
    # if trade_date is holiday
    if (forward_date in hol.Australia()
            or forward_date in hol.US()
            or forward_date in hol.UK()
            or forward_date in hol.Japan()):
        forward_date = forward_date + dt.timedelta(days=1)
        holiday_adjust(forward_date, dt.timedelta())
    # date is weekend
    elif forward_date.weekday() >= 5:
        forward_date = forward_date + dt.timedelta(days=1)
        holiday_adjust(forward_date, dt.timedelta())
    return forward_date
