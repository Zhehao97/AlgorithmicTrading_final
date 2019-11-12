import datetime as dt
import numpy as np
import pandas as pd
import time
import sys

from simtools import log_message
from date_function import holiday_adjust

# Record a trade in our trade array
def record_trade( trade_df, idx, signal, foregin_ir, domestic_ir, fx_rate, equity, position, unreal_r, real_r):
    trade_df.loc[idx]['Signal'] = signal
    trade_df.loc[idx]['Foreign_IR'] = foregin_ir
    trade_df.loc[idx]['Domestic_IR'] = domestic_ir
    trade_df.loc[idx]['FX_Rate'] = fx_rate
    trade_df.loc[idx]['Equity'] = equity
    trade_df.loc[idx]['Asset Pos'] = position
    trade_df.loc[idx]['Unreal_Return'] = unreal_r
    trade_df.loc[idx]['Real_Return'] = real_r
    return


def calculate_pnl( leverage, r_foreign , r_domestic, rate_open, rate_close):
    return leverage * ((1 + r_foreign) * (rate_close - rate_open) / rate_open + r_foreign - r_domestic ) + r_domestic


# MAIN ALGO LOOP
def algo_loop(total_data, foreign_index, domestic_index, fx_index, forward_index, trading_period, leverage = 2.0):
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

    prev_index = 0

    trades = pd.DataFrame(columns=['Signal', 'Foreign_IR', 'Domestic_IR', 'FX_Rate', 'Equity', 'Asset Pos', 'Unreal_Return', 'Real_Return'],
                          index=total_data.index)

    for index, row in total_data.iterrows():

        # FX rates
        spot_fx_rate = row[fx_index]
        forward_fx_rate = row[forward_index]

        # deal with fx_rate = 0 situation
        if (spot_fx_rate == 0) or (forward_fx_rate == 0):
            continue

        # deal with multiple day error
        if prev_index == index:
            continue

        # Interest rates
        r_foregin = row[foreign_index]/100
        r_domestic = row[domestic_index]/100

        # Signals
        trading_day = int(str(trading_period)[:-14])
        foreign_signal = 1 + r_foregin * trading_day / 360
        domestic_signal = (1 + r_domestic * trading_day / 360) * spot_fx_rate / forward_fx_rate
        signal = foreign_signal - domestic_signal

        #print(usd_signal, jpy_signal, signal)

        # position = 0
        if current_pos == 0:

            if foreign_signal > domestic_signal: # invest our money in US market

                # record trading day
                start_day = index
                end_day = holiday_adjust(start_day, trading_period)

                # update trading info
                current_pos = equity * leverage 
                rate_open = spot_fx_rate

                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=r_foregin , r_domestic=r_domestic,
                                               rate_open=rate_open, rate_close=spot_fx_rate)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, foregin_ir=r_foregin, domestic_ir=r_domestic, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)

            else:

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, foregin_ir=r_foregin, domestic_ir=r_domestic, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)
                continue

        # position > 0 or position < 0
        else:

            # close the position, return the money we borrowed
            if index >= end_day:

                # calculate pnl
                unreal_pnl = 0
                temp_pnl = calculate_pnl(leverage=leverage, r_foreign=r_foregin , r_domestic=r_domestic,
                                               rate_open=rate_open, rate_close=spot_fx_rate)
                real_pnl = (1 + real_pnl) * (1 + temp_pnl) - 1
                equity *= (1 + temp_pnl)


                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, foregin_ir=r_foregin, domestic_ir=r_domestic, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)

                # refresh the variables
                current_pos = 0
                trading_day = 0
                r_foregin = 0
                r_domestic = 0

            else:

                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=r_foregin , r_domestic=r_domestic,
                                               rate_open=rate_open, rate_close=spot_fx_rate)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, foregin_ir=r_foregin, domestic_ir=r_domestic, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)


        prev_index = index

    log_message('Algo run complete.')


    return trades
