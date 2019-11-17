import datetime as dt
import numpy as np
import pandas as pd
import time
import sys

from simtools import log_message
from date_function_v2 import holiday_adjust

# Record a trade in our trade array
def record_trade( trade_df, idx, signal, fx_name, period_name ,foreign_ir, domestic_ir, fx_rate, equity, position, unreal_r, real_r):
    trade_df.loc[idx]['Signal'] = signal
    trade_df.loc[idx]['FX_name'] = fx_name
    trade_df.loc[idx]['Period'] = period_name
    trade_df.loc[idx]['Foreign_IR'] = foreign_ir
    trade_df.loc[idx]['Domestic_IR'] = domestic_ir
    trade_df.loc[idx]['FX_Rate'] = fx_rate
    trade_df.loc[idx]['Equity'] = equity
    trade_df.loc[idx]['Asset Pos'] = position
    trade_df.loc[idx]['Unreal_Return'] = unreal_r
    trade_df.loc[idx]['Real_Return'] = real_r
    return


def calculate_pnl(leverage, r_foreign, r_domestic, rate_open, rate_close, trade_period):
    r_f = r_foreign * trade_period / 360
    r_d = r_domestic * trade_period / 360
    return leverage * ((1 + r_f) * (rate_close - rate_open) / rate_open + r_f - r_d) + r_d


def cal_period_name(trading_day):
    if trading_day == 7:
        period_name = '1W'
    elif trading_day == 30:
        period_name = '1M'
    elif trading_day == 60:
        period_name = '2M'

    return period_name

def cal_rates_name(fx_name, period_name):
    fx_libor_idx = str(fx_name) + '_LIBOR_' + str(period_name)
    dstc_libor_idx = 'JPY_LIBOR_' + str(period_name)
    spot_fx_rate_idx = str(fx_name) + '_Spot'
    forward_fx_rate_idx = str(fx_name) + '_' + str(period_name)

    return [fx_libor_idx, dstc_libor_idx, spot_fx_rate_idx, forward_fx_rate_idx]


def find_max_signal(row_row, period_list, fx_list):
    max_signal = 0
    max_period = 0
    max_fx = '-'

    for i in range(len(period_list)):
        for j in range(len(fx_list)):
            period_name = cal_period_name(period_list[i])
            fx_name = fx_list[j]
            rates_name = cal_rates_name(fx_name, period_name)

            # rates
            [r_foreign, r_domestic] = row_row[rates_name[:2]] / 100  # 0.05 -> 0.05%, not 5%
            [spot_fx_rate, forward_fx_rate] = row_row[rates_name[2:]]

            # signals
            foreign_signal = 1 + r_foreign * period_list[i] / 360  # signals on different period have different scale
            domestic_signal = (1 + r_domestic * period_list[i] / 360) * spot_fx_rate / forward_fx_rate
            signal = (foreign_signal - domestic_signal) / domestic_signal  # by doing the division, we can compare signals on different period

            if signal > max_signal:
                max_signal = signal
                max_period = period_list[i]
                max_fx = fx_name

    return [max_signal, max_period, max_fx]



# MAIN ALGO LOOP
def algo_loop(total_data, fx_list, period_list, leverage = 2.0):

    log_message('Beginning Carry-Trade Strategy run')

    # capital initialization
    # leverage = 2.0
    equity = 10000

    # trading info initialization
    current_pos = 0
    rate_open = 0

    # pnl initialization
    unreal_pnl = 0
    real_pnl = 0
    temp_pnl = 0

    # deal with multiple day error
    prev_index = 0

    trades = pd.DataFrame(columns=['Signal', 'FX_name','Period', 'Foreign_IR', 'Domestic_IR', 'FX_Rate', 'Equity',
                                   'Asset Pos', 'Unreal_Return', 'Real_Return'], index=total_data.index)

    for index, row in total_data.iterrows():

        # find max signal
        [max_signal, max_period, max_fx] = find_max_signal(row_row=row, period_list=period_list, fx_list=fx_list)
        # max_signal -> float
        # max_period -> int
        # max_fx -> str
        max_period_name = cal_period_name(trading_day=max_period) # -> str

        # Interest rates idx
        [fx_libor_idx, dstc_libor_idx, spot_fx_rate_idx, forward_fx_rate_idx] = cal_rates_name(fx_name=max_fx, period_name=max_period_name)
        # rates
        r_foreign = row[fx_libor_idx] / 100
        r_domestic = row[dstc_libor_idx] / 100
        spot_fx_rate = row[spot_fx_rate_idx]
        forward_fx_rate = row[forward_fx_rate_idx]


        # position = 0
        if current_pos == 0:

            if max_signal > 0: # invest our money in US market

                # trading period
                trading_period = dt.timedelta(days=max_period)

                # record trading fx name and period
                fx_name = max_fx
                period = max_period
                period_name = max_period_name

                # record trading day
                start_day = index
                end_day = holiday_adjust(start_day, trading_period)

                # update trading info
                current_pos = equity * leverage 
                rate_open = spot_fx_rate

                # record interest rates
                r_f = r_foreign
                r_d = r_domestic

                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=r_f, r_domestic=r_d,
                                           rate_open=rate_open, rate_close=spot_fx_rate, trade_period=period)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=fx_name, period_name=period_name,
                             foreign_ir=r_f, domestic_ir=r_d, fx_rate=spot_fx_rate, equity=equity,
                             position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)

            else:

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=fx_name, period_name=period_name,
                             foreign_ir=r_f, domestic_ir=r_d, fx_rate=spot_fx_rate, equity=equity,
                             position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)
                continue

        # position > 0 or position < 0
        else:

            # close the position, return the money we borrowed
            if index >= end_day:

                # calculate pnl
                unreal_pnl = 0
                temp_pnl = calculate_pnl(leverage=leverage, r_foreign=r_f, r_domestic=r_d,
                                         rate_open=rate_open, rate_close=spot_fx_rate, trade_period=period)
                real_pnl = (1 + real_pnl) * (1 + temp_pnl) - 1
                equity *= (1 + temp_pnl)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=fx_name, period_name=period_name,
                             foreign_ir=r_f, domestic_ir=r_d, fx_rate=spot_fx_rate, equity=equity,
                             position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)

                # refresh the variables
                current_pos = 0
                r_f = 0
                r_d = 0
                rate_open = 0
                fx_name = '-'
                period_name = '-'

            else:

                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=r_f, r_domestic=r_d,
                                           rate_open=rate_open, rate_close=spot_fx_rate, trade_period=period)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=fx_name, period_name=period_name,
                             foreign_ir=r_f, domestic_ir=r_d, fx_rate=spot_fx_rate, equity=equity,
                             position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)


        prev_index = index

    log_message('Algo run complete.')

    return trades
