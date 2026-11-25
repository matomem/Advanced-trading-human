import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mt5-bridge"))
import unittest
import pandas as pd
from backtest import run_backtest, optimize

class BacktestTests(unittest.TestCase):
    def setUp(self):
        self.df=pd.DataFrame({"time":range(120),"open":[100+i*.1 for i in range(120)],
            "high":[101+i*.1 for i in range(120)],"low":[99+i*.1 for i in range(120)],
            "close":[100+i*.1 for i in range(120)]})
    def test_metrics_are_finite(self):
        r=run_backtest(self.df)
        self.assertEqual(r["bars"],120)
        self.assertGreaterEqual(r["trades"],0)
        self.assertLessEqual(r["max_drawdown"],0)
    def test_optimizer_skips_invalid_pairs(self):
        rows=optimize(self.df,fast_values=(5,10),slow_values=(10,20))
        self.assertTrue(rows)
        self.assertTrue(all(r["fast"]<r["slow"] for r in rows))
if __name__=="__main__": unittest.main()
