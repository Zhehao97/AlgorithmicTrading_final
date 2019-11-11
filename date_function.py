from holidays_jp import CountryHolidays as hol
import datetime as dt


def holiday_adjust(trade_date):
    year = trade_date.year
    # if trade_date is holiday in japan
    if [item for item in hol.get("JP", year) if item[0].date() == trade_date]:
        trade_date = trade_date + dt.timedelta(days=1)
    # if adjusted day is us holiday
    if [item for item in hol.get("US", year) if item[0].date() == trade_date]:
        trade_date = trade_date + dt.timedelta(days=1)
    # if adjusted day is weekend
    if trade_date.weekday() >= 5:
        trade_date = trade_date + dt.timedelta(days=1)
    return trade_date
