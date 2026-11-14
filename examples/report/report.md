# VerifierAudit report

verifieraudit 0.1.0; 300 random inputs per comparison, seed 0. A grader fails if it accepts more than 5% of wrong variants, rejects more than 0% of correct alternatives, can be cheated, or the answer is leaked.

| Task | Wrong accepted | Correct rejected | Cheats | Leaks | Verdict |
|---|---|---|---|---|---|
| binary_search_blindspot | 5/23 (21.7%) | n/a | 0 | 0 | FAIL |
| chunk_overstrict | 0/6 (0%) | 2/3 (66.7%) | 0 | 0 | FAIL |
| leap_year_strong | 0/25 (0%) | 0/2 (0%) | 0 | 0 | PASS |
| roman_gameable | 1/28 (3.6%) | n/a | 1 | 2 | FAIL |
| shipping_fee_boundaries | 9/29 (31.0%) | n/a | 0 | 0 | FAIL |

## binary_search_blindspot: FAIL

A grader with a randomised test that looks thorough but only ever searches for values that are present.

**Problems found**

- accepts wrong solutions: 5 of 23 wrong variants passed (21.7%)

Tried 25 single-edit variants of the reference solution: 23 were wrong, 2 behaved the same on every sampled input and were left out. The grader accepted 5 of the wrong ones.

### Wrong solutions the grader accepted

Each row is a test the grader is missing.

| Edit | Input the tests miss | Correct answer | Wrong answer accepted |
|---|---|---|---|
| line 13: `return -1` changed to `return None` | `binary_search([], 1)` | `-1` | `None` |
| line 4: `1` changed to `0` | `binary_search([], 1)` | `-1` | `raises IndexError` |
| line 13: `1` changed to `2` | `binary_search([], 1)` | `-1` | `-2` |
| line 13: `1` changed to `0` | `binary_search([], 1)` | `-1` | `0` |
| line 12: `1` changed to `0` | `binary_search([5], 4)` | `-1` | `does not finish (over 1s)` |

## chunk_overstrict: FAIL

A grader that checks behaviour well but also checks a private helper and an exact error message.

**Problems found**

- rejects correct solutions: 2 of 3 correct alternatives failed (66.7%)

Tried 9 single-edit variants of the reference solution: 6 were wrong, 3 behaved the same on every sampled input and were left out. The grader accepted 0 of the wrong ones.

### Correct solutions the grader rejected

`inline_check.py` matches the reference on every sampled input but failed:

```
____________________________ test_validation_helper ____________________________

    def test_validation_helper():
>       solution._validate_size(1)
        ^^^^^^^^^^^^^^^^^^^^^^^
E       AttributeError: module 'solution' has no attribute '_validate_size'

tests/test_solution.py:49: AttributeError
=========================== short test summary info ============================
FAILED tests/test_solution.py::test_validation_helper - AttributeError: modul...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
1 failed, 10 passed in 0.02s
```

`loop_different_message.py` matches the reference on every sampled input but failed:

```
    def test_bad_size(size):
>       with pytest.raises(ValueError, match="size must be a positive integer"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       AssertionError: Regex pattern did not match.
E         Expected regex: 'size must be a positive integer'
E         Actual message: 'size must be at least 1'

tests/test_solution.py:42: AssertionError
=========================== short test summary info ============================
FAILED tests/test_solution.py::test_bad_size[0] - AssertionError: Regex patte...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
1 failed, 7 passed in 0.03s
```

## leap_year_strong: PASS

A strong grader: every year from 1 to 4000 is checked against Python's calendar module.

Tried 25 single-edit variants of the reference solution: 25 were wrong, 0 behaved the same on every sampled input and were left out. The grader accepted 0 of the wrong ones.

## roman_gameable: FAIL

A grader with four hand-picked examples, shipped next to a backup of the answer.

**Problems found**

- can be cheated: memoriser passed the grader
- answer leaked: roman.py.bak contains 100% of the reference solution's lines

**Notes**

- 1 of 28 wrong variants passed (3.6%), within the allowed 5.0%
- tests/test_solution.py is a copy of the grader's tests, so the expected outputs can be read off

Tried 30 single-edit variants of the reference solution: 28 were wrong, 2 behaved the same on every sampled input and were left out. The grader accepted 1 of the wrong ones.

### Wrong solutions the grader accepted

Each row is a test the grader is missing.

| Edit | Input the tests miss | Correct answer | Wrong answer accepted |
|---|---|---|---|
| line 11: `-` changed to `+` | `roman_to_int('IV')` | `4` | `6` |

### Cheats that passed

- `memoriser`: lookup table of the 4 example(s) written in the tests. For example `roman_to_int('I')` should give `1`.

### Leaks

- [high] `roman.py.bak` contains 100% of the reference solution's lines
- [medium] `tests/test_solution.py` is a copy of the grader's tests, so the expected outputs can be read off

## shipping_fee_boundaries: FAIL

A grader that only tests the middle of each price tier, never the edges.

**Problems found**

- accepts wrong solutions: 9 of 29 wrong variants passed (31.0%)

Tried 31 single-edit variants of the reference solution: 29 were wrong, 2 behaved the same on every sampled input and were left out. The grader accepted 9 of the wrong ones.

### Wrong solutions the grader accepted

Each row is a test the grader is missing.

| Edit | Input the tests miss | Correct answer | Wrong answer accepted |
|---|---|---|---|
| line 4: `<=` changed to `<` | `shipping_fee(0)` | `raises ValueError` | `4.0` |
| line 6: `<=` changed to `<` | `shipping_fee(1)` | `4.0` | `7.5` |
| line 8: `<=` changed to `<` | `shipping_fee(5)` | `7.5` | `15.0` |
| line 4: `0` changed to `-1` | `shipping_fee(0)` | `raises ValueError` | `4.0` |
| line 6: `1` changed to `2` | `shipping_fee(1.6)` | `7.5` | `4.0` |
| line 8: `5` changed to `6` | `shipping_fee(6)` | `15.0` | `7.5` |
| line 8: `5` changed to `4` | `shipping_fee(5)` | `7.5` | `15.0` |
| line 10: `20` changed to `21` | `shipping_fee(21)` | `16.2` | `15.0` |
| line 10: `20` changed to `19` | `shipping_fee(19.1)` | `15.0` | `13.920000000000002` |
