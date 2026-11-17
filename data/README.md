# Tonmick ordinary data for The Claim Ceiling

All records are fictional. These files are selected, verified projections of Tonmick World ordinary records, not a newly generated sample. They support the cases named below. See [DICTIONARY.csv](DICTIONARY.csv) and [PROVENANCE.json](PROVENANCE.json). Use `student_id` for individual-record joins; row inventories differ by purpose.

| File | Rows and use |
|:---|:---|
| [ordinary/baseline-items.csv](ordinary/baseline-items.csv) | 1,219 baseline respondents; raw stress/wellbeing items. S5 requires all ten items and reverses item four on each scale. |
| [ordinary/baseline-offer.csv](ordinary/baseline-offer.csv) | The same respondents, with college and randomized offer; offer is assignment, not attendance. |
| [ordinary/observed-registry.csv](ordinary/observed-registry.csv) | 1,600 original invitees under the actual policy mixture, including 11 unknown outcomes. Use withdrawal_label with outcome_known, not a legacy zero. |
| [ordinary/month3-stress.csv](ordinary/month3-stress.csv) | Month-three response and raw stress items for baseline respondents. Missing response/items remain missing. The retest has its own eligibility and scoring rule. |
| [ordinary/visits-exposure.csv](ordinary/visits-exposure.csv) | Archived visits, recorded enrollment months and named covariates for baseline respondents. Recording and postassignment exposure limit interpretation. |
| [ordinary/month3-screen.csv](ordinary/month3-screen.csv) | All invitees retained before the exit_month > 3 landmark. Intention is a binary month-three response; blank means no available screen. |
| [ordinary/synthesis-colleges.csv](ordinary/synthesis-colleges.csv) | Sixteen anonymized college summaries. GPA known counts differ from withdrawal-known counts. Grade sums are integer hundredths; sums of squares use those same integer units squared. |

The registry endpoint is withdrawal before competing transfer by month twelve. Consent withdrawal leaves the label unknown. The month-three screen uses only records still observed and event-free at that scheduled landmark. The college synthesis is an analogue within one study, not sixteen independent replicated studies.

The private World registry also contains simulator truth and author-only extensions. They are absent from this public selection. The [public checks](../README.html) use these data and declared working-model inputs; inherited fits and upstream forecast evidence have separately stated scopes.

Data, dictionary and notes: CC BY 4.0, Nicholas Elliott Karlson. Original World v1.0.0 plus derived administrative observation release v1.1.0. Inherited notices: [World](../WORLD_LICENSES.md) and [registry](../REGISTRY_LICENSES.md).
