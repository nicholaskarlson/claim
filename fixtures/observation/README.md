# Two-stratum observation fixture

These invented counts describe a roster of 20 students divided equally into strata A and B. Eligible counts cover the full roster. Known counts include students whose binary outcome is usable. Withdrawals count known outcomes equal to one. Subtraction gives the number of unknown outcomes. There are no person records.

The response weighting example assumes that the observed group mean represents its entire stratum. Each observed record in a stratum receives eligible divided by known as its weight. Compute the normalized weighted mean, the observed mean, and the support bounds that hold even if the observation assumption fails. A stratum with positive eligible count and zero known outcomes has no available mean and the weighting calculation must be refused.

From the companion root run `python3 scripts/check_observation.py --fixture-only` with NumPy and actual base R installed. The routes compare every result in `expected.json` and check the unsupported-stratum refusal.
