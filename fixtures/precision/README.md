# Difference and equivalence

The four invented estimates use percentage points and a normal reference with a fixed standard error. Each row includes a symmetric teaching margin of ±2 percentage points. Negative estimates favor the offer for a withdrawal outcome. The fixture compares a two-sided difference test at 5% with two one-sided equivalence tests at 5% each. It also computes the chance of demonstrating equivalence if the underlying difference is zero, conditional on each row's standard error and normal law.

Run `python3 scripts/check_precision.py --fixture-only` from the companion root with NumPy and base R. The checker compares the 95% and 90% intervals, both one-sided probabilities, the larger of the two probabilities, and the stated decisions. The margin belongs to the invented decision. The Tonmick model exercise uses the same value to illustrate how a decision changes with an explicit threshold.
