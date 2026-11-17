# One unknown label in an exact assignment example

These are invented student records. They reuse the two colleges and realized offer allocation from the Chapter 3 blocked-assignment example. In this version the recorded outcome for B4 is blank. Two offers were assigned uniformly within each four-person college, independently across colleges.

For each binary completion of B4, test the sharp null that the offer changes nobody’s outcome. Hold the completed outcome vector fixed and calculate the college-share weighted difference between offered and unoffered means for all legal assignments. Count absolute differences at least as large as the observed one, including ties. The largest of the two p values is conservative for the sharp null under the stated design and binary support, assuming the known labels are correct.

From the companion root run `python3 scripts/check_design.py --fixture-only` with NumPy and actual base R installed. Each route must match `expected.json`.
