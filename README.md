# VerifierAudit

**Grade the grader.** AI coding agents are scored by automated graders, usually
a test suite: if the tests pass, the agent "solved" the task. When those tests
are sloppy, wrong code passes, correct code fails, and the leaderboard number
means less than it looks. VerifierAudit measures how far a grader can be
trusted, and tells you which tests it is missing.

For each task it answers four questions:

| Question | How it is checked |
|---|---|
| Does the grader **accept wrong solutions**? | Makes small wrong versions of a correct solution (`<` becomes `<=`, `+` becomes `-`, `5` becomes `6`) and sees which ones still pass. |
| Does the grader **reject correct solutions**? | Runs other correct solutions, written differently, and sees which ones fail. |
| Can the grader be **cheated**? | Submits a lookup table of the examples in the tests, functions that return a constant, and an empty file. |
| Is the **answer leaked**? | Searches the files an agent is given (and their git history) for the solution or the grader's tests. |

It is plain Python. It needs no API key and calls no model.

## Quick start

```bash
git clone <this repo> && cd verifieraudit
pip install -e .
verifieraudit audit examples/tasks
```

Output from the five example graders in this repo:

```
Task                     Wrong accepted  Correct rejected  Cheats  Leaks  Verdict
-----------------------  --------------  ----------------  ------  -----  -------
binary_search_blindspot  5/23 (21.7%)    n/a               0       0      FAIL
chunk_overstrict         0/6 (0%)        2/3 (66.7%)       0       0      FAIL
leap_year_strong         0/25 (0%)       0/2 (0%)          0       0      PASS
roman_gameable           1/28 (3.6%)     n/a               1       2      FAIL
shipping_fee_boundaries  9/29 (31.0%)    n/a               0       0      FAIL

1 of 5 graders passed the audit.
```

The full write-up for this run is in
[`examples/report/report.md`](examples/report/report.md). For every wrong
solution that got through, it names the input the tests never tried:

| Edit | Input the tests miss | Correct answer | Wrong answer accepted |
|---|---|---|---|
| line 8: `<=` changed to `<` | `shipping_fee(5)` | `7.5` | `15.0` |
| line 12: `1` changed to `0` | `binary_search([5], 4)` | `-1` | `does not finish (over 1s)` |

## The example graders

The examples are small on purpose. Each one shows a different way a grader goes
wrong, and each was written to look reasonable at a glance.

| Example | What is wrong with the grader |
|---|---|
| `leap_year_strong` | Nothing. Every year from 1 to 4000 is checked against Python's `calendar` module. |
| `shipping_fee_boundaries` | Tests the middle of each price tier and never the edges, so off-by-one mistakes pass. |
| `binary_search_blindspot` | Has a 300-case randomised test, but only ever searches for values that are in the list. A version that loops forever on a missing value passes. |
| `chunk_overstrict` | Behaviour is tested well, but the tests also call a private helper and match an exact error message, so two of three correct rewrites fail. |
| `roman_gameable` | Four hand-picked examples and no subtractive numerals. A lookup table passes, and a backup of the answer sits in the files the agent is given. |

## How it decides what is "wrong"

Changing `<` to `<=` does not always change what a function does. A variant
only counts as wrong if it gives a different result from the reference solution
on at least one input. The comparison uses the task's `EDGE_CASES` plus 300
random inputs from the task's `generate` function, and each one runs in a
separate process with a time limit, so a variant that loops forever is caught
and reported rather than hanging the audit.

Variants that match the reference on every input are reported as "equivalent"
and left out of the rates. Outcomes are compared by value, or by exception
type when the reference raises (the message text is ignored).

A grader fails the audit if any of these is true:

- it accepts more than 5% of wrong variants (`--max-false-accept`),
- it rejects any correct alternative (`--max-false-reject`),
- any cheat passes,
- the solution can be found in the visible files or their git history.

## Auditing your own grader

```bash
verifieraudit init my_task        # creates a starter folder
verifieraudit audit my_task
```

A task folder contains:

```
my_task/
  task.toml              name, the function to test, timeouts
  solution.py            a solution you know is correct
  inputs.py              EDGE_CASES and generate(rng) for making inputs
  tests/                 the grader being audited (pytest by default)
  alternates/            optional: other correct solutions
  visible/               optional: the files an agent is given
```

`inputs.py` is the part that needs thought. Put boundary values in
`EDGE_CASES`; random sampling rarely lands exactly on `weight == 5`. If two
different outputs can both be correct (a list in any order, say), define
`same(expected, got)` there.

To use a grader that is not pytest, set `command` in `task.toml`, for example
`command = ["{python}", "check.py"]`. The command runs in a scratch folder
containing a copy of the grader folder and the candidate saved under the
solution's file name; exit status 0 means "accepted".

### In CI

```bash
verifieraudit audit path/to/tasks --strict
```

`--strict` exits with status 1 if any grader fails, so a weak grader blocks the
merge the same way a failing test would. Reports are written to
`verifieraudit-report/report.md` and `report.json` (change with `--out`).

## Running the tests

```bash
pytest
```

The suite takes a minute or two, because it runs the real audit on every
example.

## Limits

- **Python functions only.** A task is one function with inputs that can be
  generated. Whole-repository tasks in the style of SWE-bench are not supported
  yet.
- **"Wrong" is judged by sampling.** A variant that differs only on an input
  that was never generated is counted as equivalent, so the false-accept rate
  can be understated, not overstated. Good `EDGE_CASES` narrow the gap.
- **The variants are simple.** Single-edit changes model slips, not a
  different wrong algorithm. A grader that scores 0% here has passed a
  necessary check, not a complete one.
- **The cheats are a fixed list.** They cover memorising the tests and
  ignoring the input. They do not cover reading the grader at run time or
  tampering with the test runner.
- **False rejects need alternates.** The tool does not write other correct
  solutions for you; with no `alternates/`, that column shows `n/a`.
- **Developed and tested on Linux.** The code has Windows and macOS paths
  (hangs are caught by a slower whole-run timeout on Windows) but they have
  not been run there yet.
- **Not a security sandbox.** Candidates run in a separate process with time
  and memory limits. That guards against hangs and crashes, not hostile code.

## Why this exists

In 2026 an audit of a widely quoted coding benchmark reported that its
graders accepted wrong implementations 8.5% of the time and rejected correct
ones 24% of the time, and that agents had passed tasks by reading the answer
out of the container's git history
([VentureBeat's coverage](https://venturebeat.com/ai/deepswe-blows-up-the-ai-coding-leaderboard-crowns-gpt-5-5-and-finds-claude-opus-exploiting-a-benchmark-loophole/)).
Those are the three failure types this tool looks for, at a size where each one
can be read and understood in a minute.

## Layout

```
src/verifieraudit/
  task.py            load a task folder
  mutate.py          make single-edit wrong variants
  oracle.py          compare a candidate with the reference on many inputs
  runner.py          run the grader on a candidate
  probes.py          build the cheating solutions
  leaks.py           scan visible files and git history
  audit.py           run everything and decide the verdict
  report.py          console, Markdown and JSON output
  cli.py             the verifieraudit command
examples/tasks/      five graders to audit
tests/               tests for the tool itself
```

## License

MIT
