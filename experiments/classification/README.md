# Labelled cases for the classification of `cadl fit` (2026-11-14)

`cases.py` defines 17 cases with the expected verdict and F3 class written before running the tool
(commit f36d269). Command: `$PY -I cases.py FIT_SRC results.csv` (from this directory). Result (`results.csv`): 16 of 17 as expected. The miss: two operating modes written as
unrelated propositions (`emergency_mode`, `normal_mode`) without stated exclusivity are reported as a
guarantee conflict; with `NOT normal_mode` added to the rule's assumptions they are an exclusion.


2026-11-14 (cadl fit 443213f): the class `vacuous` was split into `vacuous` (the destination excludes the rule's assumption) and `disabling` (the rule's guarantee excludes a destination contract's assumption). The case "vacuous, reverse" was relabelled `disabling`; still 16 of 17 correct.
