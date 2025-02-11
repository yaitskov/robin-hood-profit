#!/usr/bin/env python

import math
import numpy
import pandas
import argparse

pandas.options.mode.copy_on_write = True

parser = argparse.ArgumentParser(
    prog='robin hood profit',
    description="""RH UI is not obvious about profits per instrument.
It is hard to see how much tax prepayment should trader do quaterly
to keep IRS happy.
""")

parser.add_argument('--tax',
                    default=0.24,
                    dest = 'tax',
                    help = "Income Tax ration (defauld 0.24)",
                    type = float)

parser.add_argument('--rh_csv',
                    required = True,
                    dest = 'rh_csv',
                    help = "RobinHood report in CSV format",
                    type = argparse.FileType('r'))

def clean_currency(x):
    """ If the value is a string, then remove currency symbol and delimiters
    otherwise, the value is numeric and can be converted
    """
    if isinstance(x, str):
        return(x.replace('$', '').replace(',', ''))
    return(x)

def massage(rh_report):
    rh_report['Amount'] = rh_report['Amount'].apply(clean_currency).astype('float')
    rh_report['Price'] = rh_report['Price'].apply(clean_currency).astype('float')

    rh_report['Date'] = rh_report['Process Date']
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

def instrument_profit(df, instrument):
    df = df.loc[df['Instrument'] == instrument].loc[df['Code'].isin(['Buy', 'Sell'])]
    cumsum = 0
    for i, r in df.iterrows():
        cumsum += r['Amount']
        if cumsum > 0:
            cumsum = 0
        df._set_value(i, 'CumAmount', cumsum)

    df['SignedQuantity'] = df['Quantity'] * numpy.sign(df['Amount'])
    df['CumQuantity'] = df.loc[:,'SignedQuantity'].cumsum()
    del df['SignedQuantity']
    del df['Instrument']
    df['AvgCost'] = df['CumAmount'] / df['CumQuantity']
    df['PriceDiff'] = df['Price'] - df['AvgCost'].shift(1)
    for i, r in df.iterrows():
        if r['Code'] == 'Sell' and not math.isnan(r['PriceDiff']) and not math.isnan(r['Quantity']):
            df._set_value(i, 'Profit', r['Quantity'] * r['PriceDiff'])
        else:
            df._set_value(i, 'Profit', 0)
    df['CumProfit'] = df['Profit'].apply(inf_to_0).cumsum()
    return df

def profit_by_instrument(rh_report, instruments):
    td = None
    for instrument in instruments:
        lr = instrument_profit(rh_report.copy(), instrument).iloc[-1]

        df = pandas.DataFrame(
            [
                [instrument,
                 lr['CumProfit'],
                 instrument_fees(rh_report, instrument),
                 instrument_dividends(rh_report, instrument),
                 lr['CumAmount'] * -1,
                 lr['AvgCost']
                 ]
            ],
            columns=['Instrument','Profit', 'Fees', 'Div', 'Shares', 'AvgCost'])

        td = df if td is None else pandas.concat([td, df])
    return td

def print_report(rh_report, tax_braket):
    used_instruments = discover_instruments(rh_report)
    unknown_codes = unexpected_codes(rh_report)
    td = profit_by_instrument(rh_report, used_instruments)
    print(td)
    print("-------------------------------------------------------------------------")
    if len(unknown_codes) > 0:
        print("Unknown codes:        ", unknown_codes)
    print("Used instruments:     ", used_instruments)
    print("Debit + Credit:       %11.2f" % debit_credit(rh_report))
    print("Total shares cost:    %11.2f" % td['Shares'].sum())
    inter = interest(rh_report)
    print("Interest:             %11.2f" % inter)
    fees = all_fees(rh_report)
    print("Fees and foreign tax: %11.2f" % fees)
    divi = td['Div'].sum()
    print("Total dividends:      %11.2f" % divi)
    profi = td['Profit'].sum()
    print("Buy/Sell profit:      %11.2f" % profi)
    total = profi + divi + fees + inter
    print("Total profit:         %11.2f" % total)
    if total > 0:
        print("Tax income braket:    %11.2f" % tax_braket)
        print("Tax income:           %11.2f" % (tax_braket * total))

if __name__ == "__main__":
    args = parser.parse_args()
    print_report(load_robin_hood_csv(args.rh_csv), args.tax) # "jan2025.csv"
