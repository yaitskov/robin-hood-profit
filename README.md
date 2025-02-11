# RobinHood Profit Report

RobinHood app can produce CSV activity report.

RobinHood app UI is not informative.

It is impossible to figure out quarter profit to do tax prepayments.

## Installation

```bash
$ git clone https://github.com/yaitskov/robin-hood-profit
$ cd robin-hood-profit
$ nix-build
$ ./result/bin/robin-hood-profit --help
$ export PATH=$PATH:$PWD/result/bin
```

## Usage
```
$ ./robin-hood-profit --rh_csv jan2025.csv 
  Instrument      Profit  Fees      Div    Shares     AvgCost
0        SPY  582.220886   0.0     0.00  71778.91  603.184118
0        PBR    0.000000 -14.1  1181.37  22140.00   13.837500
0        XOM    0.000000   0.0     0.00  42794.93  106.987325
-------------------------------------------------------------------------
Unknown codes:         [nan]
Used instruments:      ['SPY' 'PBR' 'XOM']
Debit + Credit:          30700.00
Total shares cost:      136713.84
Interest:                  633.35
Fees and foreign tax:      -19.10
Total dividends:          1181.37
Buy/Sell profit:           582.22
Total profit:             2377.84
Tax income braket:           0.24
Tax income:                570.68
```
