# Part I exact fixtures

These invented records are separate from Tonmick. No World generator is run.

| File | Fields and meaning |
|---|---|
| assigned.csv | One assigned student, college ID and binary offer. Includes both arms. |
| registry.csv | Includes assigned respondents and two extra frame records, observed event/exit, known-label flag and observation source. Blank label denotes unknown. |
| sampling.csv | Four equal-size colleges with known withdrawals; sample_colleges is the number selected without replacement with equal pair probabilities. |
| assignment.csv | Eight students in two colleges, fixed outcomes and observed offer. offers_per_college fixes the quota. The sharp null makes each outcome invariant to offer assignment. |
| model.csv | Fixed number of independent common-probability trials, observed event count and two candidate event probabilities. |

The checker enumerates all samples and assignments in three independent engines, checks exact rational answers, preserves undefined known-label rates, and refuses duplicate IDs, an unknown recoded as zero, missing joins and conflicting offers. The pooled assignment calculation is a deliberately different reference, labeled in the chapter.
