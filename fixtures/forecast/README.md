# A forecast with tied probabilities

The six invented records have one binary outcome and two frozen forecasts per student. The constant forecast is 0.5. The groups are teaching labels. All six rows are eligible, and the fixture has two event/non-event ties for the changing forecast.

Run `python3 scripts/check_forecast.py --fixture-only` from the companion root with NumPy and base R. The three routes compare squared probability loss and ranking. They also check the fixed calibration bins and reject a missing binary outcome. Ties count as half a win in AUC. Empty score bins have counts of zero and no means.
