#!/usr/bin/env python

import argparse
import datetime as dt
import math
import numpy
import os
import pandas


pandas.options.mode.copy_on_write = True

parser = argparse.ArgumentParser(
    prog='robin hood profit',
    description="""RH UI is not obvious about profits per instrument.

    It is hard to see how much tax prepayment should trader do quaterly
    to keep IRS happy.""")

parser.add_argument('--tax',
                    default=0.12,
                    dest = 'tax',
                    help = "Income Tax ration (default: 0.12)",
                    type = float)

parser.add_argument('--standard-deduction',
                    default=15000,
                    dest = 'standard_deduction',
                    help = "Income Tax ration (default: 15000)",
                    type = float)

parser.add_argument('--tax-year',
                    default=dt.date.today().year,
                    dest = 'tax_year',
                    help = "Tax Year (default: %d)" % dt.date.today().year,
                    type = int)

parser.add_argument('--rh_csv_dir',
                    default = '.',
                    dest = 'rh_csv_dir',
                    help = "Directory with RobinHood reports in CSV format.")

def clean_currency(x):
    """ If the value is a string, then remove currency symbol and delimiters
    otherwise, the value is numeric and can be converted
    """
    if isinstance(x, str):
        return x.replace('$', '').replace(',', '')
    return x

def to_date(x):
    if x == '' or (type(x) == float and numpy.isnan(x)):
        return None
    return dt.datetime.strptime(x, '%m/%d/%Y').date()

def clean_quantity(x):
    if isinstance(x, str):
        return x.replace('S', '')
    return x

def massage(rh_report):
    rh_report['Amount'] = rh_report['Amount'].apply(clean_currency).astype('float')
    rh_report['Price'] = rh_report['Price'].apply(clean_currency).astype('float')
    rh_report['Quantity'] = rh_report['Quantity'].apply(clean_quantity).astype('float')
    rh_report['Date'] = rh_report['Process Date'].apply(to_date)
    rh_report = rh_report.loc[rh_report['Date'].notnull()]
    # .apply(lambda x: dt.datetime.strptime(x, '%m/%d/%Y').date()).astype('date')
    rh_report['Code'] = rh_report['Trans Code']

    for cn in ['Activity Date', 'Process Date', 'Trans Code', 'Settle Date', 'Unnamed: 9', 'Description']:
        del rh_report[cn]
    return rh_report

def load_robin_hood_csv(fp):
    return massage(pandas.read_csv(fp).iloc[::-1])

def inf_to_0(x):
    if not x or math.isinf(x):
        return 0
    else:
        return x

def all_fees(df):
    return df.loc[df['Code'].isin(['DFEE', 'GOLD'])]['Amount'].sum()

def interest(df):
    return df.loc[df['Code'].isin(['INT'])]['Amount'].sum()

def debit_credit(df):
    return df.loc[df['Code'] == 'ACH']['Amount'].sum()

def unexpected_codes(df):
    return pandas.unique(df.loc[~df['Code'].isin(['DFEE', 'INT', 'GOLD', 'CDIV', 'Buy', 'Sell', 'ACH'])]['Code'])

def discover_instruments(df):
    return pandas.unique(df.loc[df['Code'].isin(['Buy', 'Sell'])]['Instrument'])

def instrument_fees(df, instrument):
    return df.loc[df['Instrument'] == instrument].loc[df['Code'] == 'DFEE']['Amount'].sum()

def instrument_dividends(df, instrument):
    return df.loc[df['Instrument'] == instrument].loc[df['Code'] == 'CDIV']['Amount'].sum()

def find_end_of_year_shares(df, instruments, year):
    """Compute Map<Instrument, {Amount : float; Shares: int}>

    :param df: rows from activity report
    :param instruments: list of instruments in df to process
    :param year: stop year
    """
    first_day = dt.date(year, 1, 1)
    df = df.loc[df['Date'] < first_day]
    df = df.loc[df['Code'].isin(['Buy', 'Sell'])]
    result = dict([(i, {'Amount': 0.0, 'Shares': 0}) for i in instruments])
    unbalanced_dic = {}
    for i, r in df.iterrows():
        instr = result.get(r['Instrument'])

        if instr is not None:
            am = r['Amount']
            if r['Code'] == 'Buy' and am > 0:
                raise Exception("Amount is positive for Buy: %s" % am)
            if r['Code'] == 'Sell' and am < 0:
                raise Exception("Amount is negative for Sell: %s" % am)
            # print("%s was %s" % (r['Instrument'], instr))
            instr['Amount'] += am
            dsh = int(numpy.sign(am) * r['Quantity'] * -1)
            instr['Shares'] += dsh
            if instr['Shares'] == 0:
                instr['Amount'] = 0.0

            # print("%s %s => %s" % (am, dsh, instr))

            if instr['Shares'] < 0:
                unbalanced[r['Instrument']] = True

    unbalanced = unbalanced_dic.keys()
    if len(unbalanced) > 0:
        raise Exception("History is not complete for instruments: %s" % unbalanced)

    return result

def instrument_profit(df, instrument, end_of_year):
    df = df.loc[df['Instrument'] == instrument].loc[df['Code'].isin(['Buy', 'Sell'])]
    eoy = end_of_year.get(instrument) or {'Amount': 0, 'Shares': 0}
    # print('eoy %s' % eoy)
    cumsum = eoy['Amount']
    cumq = eoy['Shares']
    for i, r in df.iterrows():
        cumsum += r['Amount']
        cumq += int(r['Quantity'] * -1 * numpy.sign(r['Amount']))
        if cumq == 0:
            cumsum = 0
        if cumq < 0:
            raise Exception("History is not complete for instrument: %s" % instrument)
        df._set_value(i, 'CumAmount', cumsum)
        df._set_value(i, 'CumQuantity', cumq)

    del df['Instrument']
    df['AvgCost'] = -1 * df['CumAmount'] / df['CumQuantity']
    df['PriceDiff'] = df['Price'] - df['AvgCost'].shift(1)
    for i, r in df.iterrows():
        if r['Code'] == 'Sell' and not math.isnan(r['PriceDiff']) and not math.isnan(r['Quantity']):
            df._set_value(i, 'Profit', r['Quantity'] * r['PriceDiff'])
        else:
            df._set_value(i, 'Profit', 0)
    df['CumProfit'] = df['Profit'].apply(inf_to_0).cumsum()
    # print('-- %s ------------------------------------------' % instrument)
    # print(df)
    return df

def profit_by_instrument(rh_report, instruments, end_of_year):
    td = None
    for instrument in instruments:
        lr = instrument_profit(rh_report.copy(), instrument, end_of_year).iloc[-1]

        df = pandas.DataFrame(
            [
                [instrument,
                 lr['CumProfit'],
                 instrument_fees(rh_report, instrument),
                 instrument_dividends(rh_report, instrument),
                 lr['CumAmount'] * -1,
                 lr['CumQuantity'],
                 lr['AvgCost']
                 ]
            ],
            columns=['Instrument','Profit', 'Fees', 'Div', 'Total Cost', 'Shares', 'AvgCost'])

        td = df if td is None else pandas.concat([td, df])
    return td

def print_report(rh_report, args):
    rh_report_in_year = rh_report.loc[rh_report['Date'] >= dt.date(args.tax_year, 1, 1)]
    rh_report_in_year = rh_report_in_year.loc[rh_report_in_year['Date'] < dt.date(args.tax_year + 1, 1, 1)]
    # print("rows %s / %s" % (len(rh_report_in_year), len(rh_report)))
    used_instruments = discover_instruments(rh_report_in_year)
    eoy = find_end_of_year_shares(rh_report, used_instruments, args.tax_year)

    unknown_codes = unexpected_codes(rh_report_in_year)
    td = profit_by_instrument(rh_report_in_year, used_instruments, eoy)
    print(td)
    print("-------------------------------------------------------------------------")
    if len(unknown_codes) > 0:
        print("Unknown codes:        ", unknown_codes)
    print("Tax year:             %11d" % args.tax_year)
    print("Used instruments:     ", used_instruments)
    print("Debit + Credit:       %11.2f" % debit_credit(rh_report_in_year))
    print("Total shares cost:    %11.2f" % td['Shares'].sum())
    inter = interest(rh_report_in_year)
    print("Interest:             %11.2f" % inter)
    fees = all_fees(rh_report_in_year)
    print("Fees and foreign tax: %11.2f" % fees)
    divi = td['Div'].sum()
    print("Total dividends:      %11.2f" % divi)
    profi = td['Profit'].sum()
    print("Buy/Sell profit:      %11.2f" % profi)
    total = profi + divi + fees + inter
    print("Total profit:         %11.2f" % total)
    if total > 0:
        print("Tax income braket:    %11.2f" % args.tax)
        tax_income = args.tax * max(0, total - args.standard_deduction)
        print("Tax income:           %11.2f" % tax_income)
        print("After tax:            %11.2f" % (total - tax_income))
        days = (dt.date.today() - dt.date(dt.date.today().year, 1, 1)).days + 1.0
        print("Days:                 %11d" % days)
        print("After tax per day:    %11.2f" % ((total - tax_income) / days))

def load_csv_dir(fp):
    if not os.path.isdir(fp):
        raise Exception("[%s] is not a directory" % fp)

    csv_files = [f.path for f in os.scandir(fp) if f.is_file() and f.name.lower().endswith('.csv')]

    if len(csv_files) == 0:
        raise Exception("Directory [%s] does not have CSV file" % fp)

    csv_files.sort()

    dframes = [ load_robin_hood_csv(fn) for fn in csv_files]
    last_date_prev_df = dt.date(2000, 1, 1)
    for i, df in enumerate(dframes):
        if  df.iloc[0]['Date'] < last_date_prev_df:
            raise Exception("Date from file [%s] is older than form [%s]" % (csv_files[i], csv_files[i - 1]))
        last_date_prev_df = df.iloc[-1]['Date']
    return pandas.concat(dframes)

if __name__ == "__main__":
    args = parser.parse_args()
    print_report(load_csv_dir(args.rh_csv_dir), args) # "jan2025.csv"
