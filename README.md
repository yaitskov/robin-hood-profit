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
$ ./robin-hood-profit.py --rh_csv_dir . --tax 0.24 --standard-deduction 15000
  Instrument       Profit  Fees      Div  Total Cost  Shares     AvgCost
0        SPY  2492.616831   0.0     0.00    60348.00   100.0  603.480000
0        PBR   114.238664 -14.1  1181.37    54240.27  3850.0   14.088382
0        XOM  3204.229398   0.0     0.00       -0.00     0.0         NaN
0          F   223.547910   0.0     0.00    43830.20  4480.0    9.783527
0       SBUX     5.000000   0.0     0.00       -0.00     0.0         NaN
0         BP    61.000000   0.0     0.00       -0.00     0.0         NaN
0       NVDA  1443.000000   0.0     0.00       -0.00     0.0         NaN
-------------------------------------------------------------------------
Unknown codes:         ['GDBP']
Tax year:                    2025
Used instruments:      ['SPY' 'PBR' 'XOM' 'F' 'SBUX' 'BP' 'NVDA']
Debit + Credit:          30700.00
Total shares cost:        8430.00
Interest:                  633.35
Fees and foreign tax:      -24.10
Total dividends:          1181.37
Buy/Sell profit:          7543.63
Total profit:             9334.25
Tax income braket:           0.24
Tax income:                  0.00
After tax:                9334.25
Days:                          42
After tax per day:         222.24

```
