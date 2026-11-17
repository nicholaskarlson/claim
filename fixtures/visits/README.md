# Four records with unequal exposure

These four invented rows describe recorded visits and enrolled months. Calculate visits per respondent, total visits divided by total months, and the average of the individual visit rates in each assigned group. The first and third comparisons are higher in the offered group. The aggregate rate is lower. The example isolates how changing the denominator and weighting changes the question.

An observed zero visit count at positive exposure is valid. A zero or negative exposure is outside this offset example and is refused.

From the companion root run `python3 scripts/check_visits.py --fixture-only` with NumPy and actual base R. Compare each route with `expected.json`.
