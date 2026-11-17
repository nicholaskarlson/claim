# Four invented colleges

In each invented college the four observed grades without an offer are 1.8, 1.8, 2.2 and 2.2. The four offer grades are those four values shifted by −0.4, 0.0, +0.4 and +0.8 points across colleges A through D, respectively. The CSV stores grade sums in hundredths of a point and sums of squared hundredths. Counts distinguish all assigned from known grades.

The mean contrast is +0.20. Each estimated working variance is 2/75. The four centered contrasts have squared deviations summing to 0.80. Hence the weighted dispersion statistic is 30, and the method-of-moments between-college variance is 0.24. Run `python3 scripts/check_synthesis.py --fixture-only` from the companion root with NumPy and base R. The checker also repeats the common-contrast case and checks the zero-heterogeneity boundary. The example uses invented summaries and describes no Tonmick college.
