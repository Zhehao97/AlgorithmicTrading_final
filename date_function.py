from holidays_jp import CountryHolidays as hol
import datetime as dt


def holiday_adjust(trade_date, delta):
    forward_date = trade_date + delta
    year = forward_date.year
    # if trade_date is holiday in japan
    if [item for item in hol.get("JP", year) if item[0].date() == forward_date]:
        forward_date = forward_date + dt.timedelta(days=1)
        holiday_adjust(forward_date, dt.timedelta())
    # if adjusted day is us holiday
    elif [item for item in hol.get("US", year) if item[0].date() == forward_date]:
        forward_date = forward_date + dt.timedelta(days=1)
        holiday_adjust(forward_date, dt.timedelta())
    # if adjusted day is weekend
    elif forward_date.weekday() >= 5:
        forward_date = forward_date + dt.timedelta(days=1)
        holiday_adjust(forward_date, dt.timedelta())
    else:
        return forward_date
