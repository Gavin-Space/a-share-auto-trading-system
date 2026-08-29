"""analyze_trades.py

Reads trades.csv produced by run_demo.py and outputs:
- summary metrics printed to stdout and saved to trades_analysis.csv
- optional plots (equity curve and cumulative realized P&L) saved as PNG if matplotlib is available

Usage:
  python analyze_trades.py [trades.csv] [initial_cash]

Example:
  python analyze_trades.py trades.csv 100000
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime

# optional plotting
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


def load_trades(path: str):
    df = pd.read_csv(path)
    # ensure datetime
    if 'datetime' in df.columns:
        try:
            df['datetime'] = pd.to_datetime(df['datetime'])
        except Exception:
            # try parsing as string
            df['datetime'] = df['datetime'].apply(lambda x: datetime.fromisoformat(x))
    else:
        df['datetime'] = pd.NaT
    return df


def summarize_trades(df: pd.DataFrame, initial_cash: float = 100000.0):
    out = {}
    out['total_trades'] = len(df)
    out['total_fees'] = df['fee'].sum() if 'fee' in df.columns else 0.0
    out['total_realized'] = df['realized'].sum() if 'realized' in df.columns else 0.0
    out['buys'] = len(df[df['side'] == 'buy'])
    out['sells'] = len(df[df['side'] == 'sell'])
    out['win_trades'] = len(df[df['realized'] > 0]) if 'realized' in df.columns else 0
    out['win_rate'] = (out['win_trades'] / out['total_trades']) if out['total_trades'] > 0 else 0.0

    # time span and frequency
    if df['datetime'].notna().any():
        min_t = df['datetime'].min()
        max_t = df['datetime'].max()
        seconds = (max_t - min_t).total_seconds() if pd.notna(max_t) and pd.notna(min_t) else 0
        out['start_time'] = min_t
        out['end_time'] = max_t
        out['duration_seconds'] = seconds
        out['trades_per_minute'] = (out['total_trades'] / (seconds / 60.0)) if seconds > 0 else np.nan
    else:
        out['start_time'] = None
        out['end_time'] = None
        out['duration_seconds'] = None
        out['trades_per_minute'] = None

    # equity-like curve (we use cash column as proxy for NAV if available)
    if 'cash' in df.columns:
        equity_ts = df[['datetime', 'cash']].copy()
        equity_ts = equity_ts.dropna(subset=['datetime'])
        equity_ts = equity_ts.sort_values('datetime')
        equity_ts = equity_ts.set_index('datetime')
        out['equity_ts'] = equity_ts
    else:
        # fallback: cumulative realized P&L applied to initial cash
        if 'realized' in df.columns:
            df_sorted = df.sort_values('datetime') if 'datetime' in df.columns else df
            cum_realized = df_sorted['realized'].cumsum()
            times = df_sorted['datetime'] if 'datetime' in df.columns else pd.RangeIndex(len(df_sorted))
            equity_ts = pd.DataFrame({'datetime': times, 'nav': initial_cash + cum_realized}).set_index('datetime')
            out['equity_ts'] = equity_ts
        else:
            out['equity_ts'] = pd.DataFrame()

    return out


def save_summary(out: dict, df: pd.DataFrame, out_csv: str = 'trades_analysis.csv'):
    # high-level metrics
    metrics = {
        'total_trades': out['total_trades'],
        'total_fees': float(out['total_fees']),
        'total_realized': float(out['total_realized']),
        'buys': out['buys'],
        'sells': out['sells'],
        'win_trades': out['win_trades'],
        'win_rate': float(out['win_rate'])
    }
    # save metrics + trades to a CSV for record
    metrics_df = pd.DataFrame([metrics])
    # dump trades with index
    trades_out = df.copy()
    try:
        metrics_df.to_csv(out_csv.replace('.csv', '_metrics.csv'), index=False)
        trades_out.to_csv(out_csv, index=False)
    except Exception as e:
        print(f"Warning: failed to write CSVs: {e}")


def plot_equity(equity_ts: pd.DataFrame, prefix: str = 'trades'):
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib not available, skipping plots. Install matplotlib to enable plots.")
        return
    if equity_ts.empty:
        print("No equity time series available to plot.")
        return
    try:
        plt.figure(figsize=(10, 5))
        # equity_ts may have column 'cash' or 'nav'
        ycol = equity_ts.columns[0]
        equity_ts[ycol].plot(title='Equity / Cash over time')
        plt.ylabel('Value')
        plt.xlabel('Time')
        plt.grid(True)
        png = f"{prefix}_equity.png"
        plt.savefig(png)
        print(f"Saved equity plot to {png}")

        # cumulative realized
        if 'nav' not in equity_ts.columns:
            # attempt cumulative realized plot from trades if present
            plt.figure(figsize=(10, 5))
            if 'cash' in equity_ts.columns:
                equity_ts['cash'].plot(title='Cash over time')
                plt.ylabel('Cash')
                plt.xlabel('Time')
                plt.grid(True)
                png2 = f"{prefix}_cash.png"
                plt.savefig(png2)
                print(f"Saved cash plot to {png2}")
    except Exception as e:
        print(f"Plotting failed: {e}")


def main():
    path = 'trades.csv'
    initial_cash = 100000.0
    if len(sys.argv) >= 2:
        path = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            initial_cash = float(sys.argv[2])
        except Exception:
            pass

    try:
        df = load_trades(path)
    except FileNotFoundError:
        print(f"File not found: {path}")
        sys.exit(1)

    out = summarize_trades(df, initial_cash=initial_cash)

    # print summary
    print("--- Trade Analysis Summary ---")
    print(f"Total trades: {out['total_trades']}")
    print(f"Total fees: {out['total_fees']:.4f}")
    print(f"Total realized P&L: {out['total_realized']:.4f}")
    print(f"Buys: {out['buys']}, Sells: {out['sells']}")
    print(f"Win trades: {out['win_trades']}, Win rate: {out['win_rate']:.2%}")
    if out['duration_seconds'] is not None:
        print(f"Duration (s): {out['duration_seconds']:.1f}, Trades/min: {out['trades_per_minute']:.2f}")

    # save CSVs
    save_summary(out, df)
    print("Saved trades_analysis.csv and trades_analysis_metrics.csv")

    # plotting
    plot_equity(out.get('equity_ts', pd.DataFrame()))


if __name__ == '__main__':
    main()
