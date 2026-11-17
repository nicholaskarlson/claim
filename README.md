# The Claim Ceiling companion

Public companion to Nicholas Elliott Karlson's *The Claim Ceiling: How Design, Measurement, and Verification Decide What Statistics Can Say*, Book 11 of NEKpress Research: Proof-First Guides.

**Everything in Tonmick is fictional. These are teaching records, not findings about real people.**

- [Read the companion](https://nicholaskarlson.github.io/claim/)
- [Data and dictionary](data/README.md)
- [Six completed Claim Audits](https://nicholaskarlson.github.io/claim/cases/claim-audits.html)
- [Blank card and field prompts](https://nicholaskarlson.github.io/claim/field-guide.html)
- [Coverage register](https://nicholaskarlson.github.io/claim/cases/method-register.html)
- [Releases](https://github.com/nicholaskarlson/claim/releases)
- [Errata](https://github.com/nicholaskarlson/claim/issues)

## Run the checks

On Ubuntu, install Python with venv support and actual base R. Then, from the public checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/check_public.py
```

If R is installed elsewhere, set `CLAIM_RSCRIPT` to its Rscript executable. The successful marker is `CLAIM_PUBLIC_OK ordinary_groups=9 routes=3 fixtures=10`. The receipt is `build/verified/public-check.json`. No private source checkout, hidden file, generator or pandas installation is required. The public check does not generate a new World.

For file identity alone, run `python3 scripts/check_public.py --inventory-only`. `release.json` identifies the source World revision, book source tree, public version and exact file inventory. Use a tagged release matching the book edition; record the tag in your notes.

## What is recomputed

Each selected ordinary calculation is independently checked with NumPy, standard-library Python and base R:

1. Baseline stress–wellbeing score correlation and eligible score pairs.
2. Assignment–registry join, counts, recorded fractions and binary completion bounds.
3. Invitation-roster summaries under the actual policy mixture.
4. College-weighted completion range and conservative finite-design interval.
5. Month-three stress retest, selection/tie rules and declared error scenarios.
6. Archived visit summaries and covariance checks with the published Poisson coefficients held fixed.
7. Observed-GPA college summaries and the working synthesis.
8. Month-three intention screen, missing-label bounds and conditional probit summaries.
9. Chapter 14's normal working posterior and Bayes factor across the declared priors, using the published estimate and fixed standard error.

The command also runs ten families of invented fixtures, including invalid-input refusals. The data dictionary distinguishes those fixtures from the frozen Tonmick projections.

## Evidence with a different scope

The CFA/IRT fits and prior one-state benchmark from Book 10 remain documented aggregate evidence. This command does not refit them. It does not refit Book 9's full Poisson/NB2 family. Book 7's [public companion](https://github.com/nicholaskarlson/predict) supplies its full later-cohort evaluation; this repository supplies its evidence summary and a runnable scoring fixture. No matching hidden potential-outcome or joint latent-state benchmark is released here. See the [closing truth audit](https://nicholaskarlson.github.io/claim/cases/truth-checks.html).

## Source and reuse

The seven ordinary files are verified projections of the frozen Tonmick World baseline and v1.1.0 administrative observation extension. [Provenance](data/PROVENANCE.json) records the source revision, selected member hashes and transformations. The authoring World registry is maintained separately. Users of this companion need only these public files.

Data, dictionaries, original notes and audit sheets are CC BY 4.0; original code is MIT. Retained source notices are `WORLD_LICENSES.md` and `REGISTRY_LICENSES.md`. See [LICENSES.md](LICENSES.md). Book manuscript and branding rights are reserved.

To report a problem, include the book edition, public tag, case ID, expected and observed result, and a small reproducible example. Please do not post private inputs or credentials.
