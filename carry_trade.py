import datetime as dt
import numpy as np
import pandas as pd
import time
import sys

from holidays_jp import CountryHolidays as hol
from simtools import log_message
from date_function import holiday_adjust


# Record a trade in our trade array
def record_trade(trade_df, idx, signal, usd_ir, jpy_ir, fx_rate, equity, position, unreal_pnl, real_pnl):
    trade_df.loc[ idx ][ 'Signal' ] = signal
    trade_df.loc[ idx ][ 'USD_IR' ] = usd_ir
    trade_df.loc[ idx ][ 'JPY_IR' ] = jpy_ir
    trade_df.loc[ idx ][ 'FX_Rate' ] = fx_rate
    trade_df.loc[ idx ][ 'Equity' ] = equity
    trade_df.loc[ idx ][ 'Asset Pos' ] = position
    trade_df.loc[ idx ][ 'Unreal_PnL' ] = unreal_pnl
    trade_df.loc[ idx ][ 'Real_PnL' ] = real_pnl
    return


def calculate_pnl( leverage, r_foreign , r_domestic, rate_open, rate_close):
    return leverage * (( 1 + r_foreign ) * (rate_close - rate_open) / rate_open + r_foreign - r_domestic ) + r_domestic


# MAIN ALGO LOOP
def algo_loop(total_data, trading_period = 30):
    log_message('Beginning Carry-Trade Strategy run')

    # capital initialization
    leverage = 2.0
    equity = 10000 # invest with fixed equity

    # trading info initialization
    # trading_period = 30 # 1 month = 30 days
    trading_day = 0
    current_pos = 0
    rate_open = 0

    # pnl initialization
    unreal_pnl = 0
    real_pnl = 0
    temp_pnl = 0

    # signal initialization 
    usd_signal = 0
    jpy_signal = 0
    signal = 0

    prev_index = 0

    trades = pd.DataFrame(columns=['Signal', 'USD_IR', 'JPY_IR', 'FX_Rate', 'Equity', 'Asset Pos', 'Unreal_PnL', 'Real_PnL'],
                          index=total_data.index)

    for index, row in total_data.iterrows():

        # FX rates
        spot_fx_rate = row['SpotRate']
        forward_fx_rate = row['1MFR']

        # deal with fx_rate = 0 situation
        if (spot_fx_rate == 0) or (forward_fx_rate == 0):
            continue

        # deal with multiple day error
        if prev_index == index:
            continue

        # Interest rates
        usd_ir = row['1MUSD']/100
        jpy_ir = row['1MJPY']/100

        # Signals
        usd_signal = 1 + usd_ir * trading_period / 360
        jpy_signal = ( 1 + jpy_ir * trading_period / 360 ) * spot_fx_rate / forward_fx_rate
        signal = usd_signal - jpy_signal

        #print(usd_signal, jpy_signal, signal)

        # position = 0
        if current_pos == 0:

            if signal < 0: # borrow USD and invest in JPY

                # record trading day
                trading_day = index

                # update trading info
                current_pos = - equity * leverage 
                rate_open = spot_fx_rate
                r_foregin = jpy_ir
                r_domestic = usd_ir

                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=r_foregin , r_domestic=r_domestic,
                                               rate_open=rate_open, rate_close=spot_fx_rate)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, usd_ir=usd_ir, jpy_ir=jpy_ir, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_pnl=unreal_pnl, real_pnl=real_pnl)

            elif signal > 0: # borrow JPY and invest in

                # record trading day
                trading_day = index

                # update trading info
                current_pos = equity * leverage 
                rate_open = spot_fx_rate
                r_foregin = usd_ir
                r_domestic = jpy_ir

                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=r_foregin , r_domestic=r_domestic,
                                               rate_open=rate_open, rate_close=spot_fx_rate)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, usd_ir=usd_ir, jpy_ir=jpy_ir, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_pnl=unreal_pnl, real_pnl=real_pnl)

            else:

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, usd_ir=usd_ir, jpy_ir=jpy_ir, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_pnl=unreal_pnl, real_pnl=real_pnl)    
                continue

        # position > 0 or position < 0
        else:

            # calculate how long we have hold the position
            holding_period = int(str(index - trading_day)[:-14])

            # close the position, return the money we borrowed
            if holding_period >= trading_period:

                # calculate pnl
                unreal_pnl = 0
                temp_pnl = calculate_pnl(leverage=leverage, r_foreign=r_foregin , r_domestic=r_domestic,
                                               rate_open=rate_open, rate_close=spot_fx_rate)
                real_pnl = (1 + real_pnl) * (1 + temp_pnl) - 1


                # record trading info
                record_trade(trade_df=trades, idx=index, signal=signal, usd_ir=usd_ir, jpy_ir=jpy_ir, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_pnl=unreal_pnl, real_pnl=real_pnl)

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
                record_trade(trade_df=trades, idx=index, signal=signal, usd_ir=usd_ir, jpy_ir=jpy_ir, fx_rate=spot_fx_rate,
                                 equity=equity, position=current_pos, unreal_pnl=unreal_pnl, real_pnl=real_pnl)


        prev_index = index

    log_message( 'Algo run complete.' )


    return trades
