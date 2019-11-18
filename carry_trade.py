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
    return leverage * ((1 + r_f) * ((rate_close - rate_open) / rate_open) + r_f - r_d) + r_d


def cal_period_name(trading_day):
    if trading_day == 7:
        return '1W'
    elif trading_day == 30:
        return '1M'
    elif trading_day == 60:
        return '2M'


def cal_rates_name(fx_name, period_name):
    fx_libor_idx = str(fx_name) + '_LIBOR_' + str(period_name)
    dstc_libor_idx = 'JPY_LIBOR_' + str(period_name)
    spot_fx_rate_idx = str(fx_name) + '_Spot'
    forward_fx_rate_idx = str(fx_name) + '_' + str(period_name)
    ask_fx_rate_idx = 'JPY_' + str(fx_name) + '_Ask'
    bid_fx_rate_idx = 'JPY_' + str(fx_name) + '_Bid'

    return [fx_libor_idx, dstc_libor_idx, spot_fx_rate_idx, forward_fx_rate_idx,
            ask_fx_rate_idx, bid_fx_rate_idx]


def find_max_signal(row_row, period_list, fx_list):
    max_signal = -10000
    max_period = 0
    max_fx = '-'

    for i in range(len(period_list)):
        for j in range(len(fx_list)):
            if period_list[i] == 7 and fx_list[j] == 'AUD':
                continue
            else:
                period_name = cal_period_name(period_list[i])
                fx_name = fx_list[j]
                rates_name = cal_rates_name(fx_name, period_name)

                # rates
                [r_foreign, r_domestic] = row_row[rates_name[:2]] / 100  # 0.05 -> 0.05%, not 5%
                [spot_fx_rate, forward_fx_rate, ask_fx_rate_idx, bid_fx_rate_idx] = row_row[rates_name[2:]]

                # signals
                foreign_signal = (1 + r_foreign * period_list[i] / 360) * forward_fx_rate / spot_fx_rate
                domestic_signal = (1 + r_domestic * period_list[i] / 360)
                signal = (foreign_signal - domestic_signal)

                if signal > max_signal:
                    max_signal = signal
                    max_period = period_list[i]
                    max_fx = fx_name

    return [max_signal, max_period, max_fx]



# MAIN ALGO LOOP
def algo_loop(total_data, fx_list, period_list, leverage = 2.0, JPY=0):

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

    # trade info
    trade_fx = '-'
    trade_period = 0
    trade_period_name = '-'

    trades = pd.DataFrame(columns=['Signal', 'FX_name','Period', 'Foreign_IR', 'Domestic_IR', 'FX_Rate', 'Equity',
                                   'Asset Pos', 'Unreal_Return', 'Real_Return'], index=total_data.index)

    for index, row in total_data.iterrows():

        # position = 0
        if current_pos == 0:

            # find max signal
            [max_signal, max_period, max_fx] = find_max_signal(row_row=row, period_list=period_list, fx_list=fx_list)
            max_period_name = cal_period_name(trading_day=max_period)  # max_signal -> float ; max_period -> int ; max_fx -> str
            #print(max_signal)

            if max_signal > 0:

                # record trading fx name and period
                trade_fx = max_fx                        # e.g. AUD
                trade_period = max_period                # e.g. 60
                trade_period_name = max_period_name      # e.g. 2M

                # record trading day
                start_day = index
                end_day = holiday_adjust(start_day, dt.timedelta(days=trade_period))

                # Interest rates idx
                [fx_libor_idx, dstc_libor_idx, spot_fx_rate_idx,
                 forward_fx_rate_idx, ask_fx_rate_idx, bid_fx_rate_idx] = cal_rates_name(fx_name=trade_fx, period_name=trade_period_name)

                # Interest rates
                trade_r_f = row[fx_libor_idx] / 100
                trade_r_d = row[dstc_libor_idx] / 100

                if trade_fx == 'JPY':
                    trade_fx_rate = 1
                    trade_ask_fx_rate = 1
                    trade_bid_fx_rate = 1
                else:
                    trade_fx_rate = row[spot_fx_rate_idx]
                    trade_ask_fx_rate = row[ask_fx_rate_idx]
                    trade_bid_fx_rate = row[bid_fx_rate_idx]

                # update trading info
                rate_open = trade_ask_fx_rate
                current_pos = equity * leverage

                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=trade_r_f, r_domestic=trade_r_d,
                                           rate_open=rate_open, rate_close=trade_bid_fx_rate, trade_period=trade_period)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=trade_fx, period_name=trade_period_name,
                             foreign_ir=trade_r_f, domestic_ir=trade_r_d, fx_rate=trade_fx_rate, equity=equity,
                             position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)

            else:

                if JPY == 1:
                    # record trading fx name and period
                    trade_fx = 'JPY'                        # e.g. AUD
                    trade_period = 7                        # e.g. 60
                    trade_period_name = '1W'                # e.g. 2M

                    # record trading day
                    start_day = index
                    end_day = holiday_adjust(start_day, dt.timedelta(days=trade_period))

                    # Interest rates idx
                    [fx_libor_idx, dstc_libor_idx, spot_fx_rate_idx,
                     forward_fx_rate_idx, ask_fx_rate_idx, bid_fx_rate_idx] = cal_rates_name(fx_name=trade_fx,
                                                                                             period_name=trade_period_name)
                    # Interest rates
                    trade_r_f = row[fx_libor_idx] / 100
                    trade_r_d = row[dstc_libor_idx] / 100

                    if trade_fx == 'JPY':
                        trade_fx_rate = 1
                        trade_ask_fx_rate = 1
                        trade_bid_fx_rate = 1
                    else:
                        trade_fx_rate = row[spot_fx_rate_idx]
                        trade_ask_fx_rate = row[ask_fx_rate_idx]
                        trade_bid_fx_rate = row[bid_fx_rate_idx]


                    if trade_r_d > 0:

                        # update trading info
                        rate_open = trade_ask_fx_rate
                        current_pos = equity

                        # calculate unrealized pnl
                        unreal_pnl = calculate_pnl(leverage=1, r_foreign=trade_r_f, r_domestic=trade_r_d,
                                                   rate_open=rate_open, rate_close=trade_bid_fx_rate, trade_period=trade_period)

                        # record trading info
                        record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=trade_fx, period_name=trade_period_name,
                                     foreign_ir=trade_r_f, domestic_ir=trade_r_d, fx_rate=trade_fx_rate, equity=equity,
                                     position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)
                    else:
                        # record trading info
                        record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name='-', period_name='-',
                                     foreign_ir=0, domestic_ir=0, fx_rate=1, equity=equity,
                                     position=0, unreal_r=unreal_pnl, real_r=real_pnl)
                else:
                    # record trading info
                    record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name='-', period_name='-',
                                 foreign_ir=0, domestic_ir=0, fx_rate=1, equity=equity,
                                 position=0, unreal_r=unreal_pnl, real_r=real_pnl)

        else:   # position < 0

            # Interest rates idx
            [fx_libor_idx, dstc_libor_idx, spot_fx_rate_idx,
             forward_fx_rate_idx, ask_fx_rate_idx, bid_fx_rate_idx] = cal_rates_name(fx_name=trade_fx,
                                                                                     period_name=trade_period_name)

            # Interest rates
            trade_r_f = row[fx_libor_idx] / 100
            trade_r_d = row[dstc_libor_idx] / 100

            if trade_fx == 'JPY':
                trade_fx_rate = 1
                trade_ask_fx_rate = 1
                trade_bid_fx_rate = 1
            else:
                trade_fx_rate = row[spot_fx_rate_idx]
                trade_ask_fx_rate = row[ask_fx_rate_idx]
                trade_bid_fx_rate = row[bid_fx_rate_idx]

            # close the position, return the money we borrowed
            if index >= end_day:

                # calculate pnl
                unreal_pnl = 0
                temp_pnl = calculate_pnl(leverage=leverage, r_foreign=trade_r_f, r_domestic=trade_r_d,
                                         rate_open=rate_open, rate_close=trade_bid_fx_rate, trade_period=trade_period)
                real_pnl = (1 + real_pnl) * (1 + temp_pnl) - 1
                equity *= (1 + temp_pnl)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=trade_fx, period_name=trade_period_name,
                             foreign_ir=trade_r_f, domestic_ir=trade_r_d, fx_rate=trade_fx_rate, equity=equity,
                             position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)

                # refresh the variables
                current_pos = 0
                rate_open = 0

                # refresh trade info
                trade_fx = '-'
                trade_period = 0
                trade_period_name = '-'

            else:
                # calculate unrealized pnl
                unreal_pnl = calculate_pnl(leverage=leverage, r_foreign=trade_r_f, r_domestic=trade_r_d,
                                           rate_open=rate_open, rate_close=trade_bid_fx_rate, trade_period=trade_period)

                # record trading info
                record_trade(trade_df=trades, idx=index, signal=max_signal, fx_name=trade_fx, period_name=trade_period_name,
                             foreign_ir=trade_r_f, domestic_ir=trade_r_d, fx_rate=trade_fx_rate, equity=equity,
                             position=current_pos, unreal_r=unreal_pnl, real_r=real_pnl)


    log_message('Algo run complete.')

    return trades
