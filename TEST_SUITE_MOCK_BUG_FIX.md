# The `sys.modules` Mock Bug — Full Writeup

What broke, why it broke, how it was found, and how it was fixed. This
covers one specific issue in the test suite (not the AI-1 module itself —
see `AI1_IMPLEMENTATION_NOTES.md` for that), but it affected *every*
contributor's tests, so it gets its own document.

**Status**: Fixed and verified on `feat/anas` (commit `e3461ea`). **Not yet
on `main`** — `main` still has the broken version as of this writing. Needs
a PR from `feat/anas` to land.

**Files involved**:
- `tests/unit/conftest.py`
- `tests/integration/test_pipeline_integration.py`

---

## Table of contents

1. [Background: what a `conftest.py` is](#1-background-what-a-conftestpy-is)
2. [The problem it was trying to solve](#2-the-problem-it-was-trying-to-solve)
3. [The original fix, and why it was too broad](#3-the-original-fix-and-why-it-was-too-broad)
4. [The mechanism: how `sys.modules` poisoning actually breaks things](#4-the-mechanism-how-sysmodules-poisoning-actually-breaks-things)
5. [Why it passed some runs and failed others](#5-why-it-passed-some-runs-and-failed-others)
6. [How the bug was actually found](#6-how-the-bug-was-actually-found)
7. [The fix](#7-the-fix)
8. [Why the fix is correct — what it preserves, what it changes](#8-why-the-fix-is-correct--what-it-preserves-what-it-changes)
9. [Verification performed](#9-verification-performed)
10. [Current status and what's still needed](#10-current-status-and-whats-still-needed)
11. [Broader lessons](#11-broader-lessons)

---

## 1. Background: what a `conftest.py` is

`conftest.py` is a special filename pytest recognizes automatically — it
isn't a test file itself, but pytest imports and executes it *before*
collecting or running any tests in its directory, and that applies to every
subdirectory underneath it too. A `conftest.py` at `tests/unit/` runs before
*anything* under `tests/unit/ingestion/`, `tests/unit/propagation/`,
`tests/unit/shared/`, and `tests/unit/conjunction/` — regardless of which of
those you actually intended to test.

This makes `conftest.py` a natural place to put setup that every test needs
(shared fixtures, environment configuration) — and also a place where a
mistake has an unusually wide blast radius, since it runs unconditionally
for the whole subtree.

## 2. The problem it was trying to solve

The comment left in the original code explains the intent:

> Mock astropy and sgp4 to avoid C-extension deadlocks on Python 3.14 on macOS

`astropy` and `sgp4` both ship compiled C/C++ extensions. On a specific
platform combination — Python 3.14 on macOS, per the comment — importing
these apparently hangs the process outright (a deadlock in the C extension's
initialization, not a Python-level exception that could just be caught).

The AI-2 conjunction module (`src/conjunction/`) doesn't use either
library — it works entirely with plain numpy arrays that arrive already
computed by AI-1's propagation module. So on the affected platform, the
reasonable-sounding idea was: since conjunction's own tests don't need these
libraries, replace them with harmless fakes before anything can try to
import them for real and hang.

**Why this needed to happen globally, not just in conjunction's own test
files**: pytest collection. Before running any test, pytest first *imports
every test file it can discover*, to find out what tests exist in each one.
`tests/unit/propagation/test_sgp4_engine.py` imports the real `sgp4` at the
top of the file, because that module's tests genuinely need it. Even someone
who only asked pytest to run `tests/unit/conjunction/` would, if pointed at
the whole `tests/` tree (or if collection touches sibling directories for
any reason), still end up importing that file — and if `sgp4` hangs on
import on that machine, the run would still lock up before a single test had
executed, regardless of which tests were actually wanted.

## 3. The original fix, and why it was too broad

The original code:

```python
import sys
from unittest.mock import MagicMock

# Mock astropy and sgp4 to avoid C-extension deadlocks on Python 3.14 on macOS
sys.modules['astropy'] = MagicMock()
sys.modules['astropy.time'] = MagicMock()
sys.modules['astropy.coordinates'] = MagicMock()
sys.modules['astropy.units'] = MagicMock()
sys.modules['erfa'] = MagicMock()
sys.modules['sgp4'] = MagicMock()
sys.modules['sgp4.api'] = MagicMock()
sys.modules['sgp4.ext'] = MagicMock()
sys.modules['sgp4.earth_gravity'] = MagicMock()
```

This runs unconditionally — on every machine, every time, regardless of
whether the real deadlock would actually occur there. On the platform where
the deadlock was reported, that's exactly what was wanted. On every other
platform — this project's Windows/Python 3.11 development machine, almost
certainly most CI runners, and presumably most of the team who aren't on
that exact macOS/3.14 combination — `astropy` and `sgp4` import completely
normally. The code above doesn't check for that. It substitutes the fakes
regardless, every single time, for everyone.

An identical copy of this same block also existed in
`tests/integration/test_pipeline_integration.py`, for the same stated
reason (that test constructs its inputs directly rather than running real
SGP4 propagation, so it doesn't need the real libraries either).

## 4. The mechanism: how `sys.modules` poisoning actually breaks things

`sys.modules` is Python's own process-wide cache of every module that's
been imported so far, keyed by name (`'astropy'`, `'astropy.time'`, etc.).
Normally, when any code anywhere does `import astropy`, Python's import
system checks this cache first — if the name is already there, Python hands
back the cached object directly, skipping re-reading and re-executing the
library's source. This is what makes repeated imports of the same module
fast: `import numpy` in ten different files only actually loads numpy once.

The line `sys.modules['astropy'] = MagicMock()` exploits this cache
directly: it manually inserts a `MagicMock()` — an object from Python's
`unittest.mock` library that silently accepts *any* attribute access or
method call and hands back another `MagicMock` in response, never raising
an error — into the cache, under the name `'astropy'`, before anything real
ever imports it.

From that point on, for the remainder of the process, *anywhere* that does
`import astropy` or `from astropy.time import Time` finds the fake already
sitting in the cache and receives that instead of the real library. The
import statement itself does not fail or raise a warning — it succeeds,
silently, with fake data.

Concretely, here is what happened when running the AI-1 propagation and
coordinate-transform tests together with the rest of the suite:

1. `tests/unit/conftest.py` (or `test_pipeline_integration.py`, depending on
   collection order — see §5) executes its module-level mocking code.
   `sys.modules['astropy']`, `['astropy.time']`, `['sgp4']`, etc. are now
   all `MagicMock()` instances, for the rest of the process.
2. pytest collection reaches `tests/unit/shared/test_transforms.py`, which
   imports `src/shared/frames/transforms.py`, which has
   `from astropy.time import Time` at module level.
3. Python checks `sys.modules['astropy.time']`, finds the fake already
   there, and hands back an attribute of that `MagicMock`. The import
   "succeeds" — no `ImportError` — but the name `Time` inside
   `transforms.py` is now bound to a fake object, not the real
   `astropy.time.Time` class.
4. Later, `transforms.py` runs `if isinstance(epochs, Time):`.
   `isinstance()`'s second argument must be an actual class (or tuple of
   classes). A `MagicMock` attribute is neither a class nor anything that
   behaves like one at the C level `isinstance` checks against. Python
   raises:

   ```
   TypeError: isinstance() arg 2 must be a type, a tuple of types, or a union
   ```

This is the exact error observed. It is not a bug in the propagation or
transform code — `Time` really is the correct `astropy.time.Time` class
when that module is imported on its own. The failure only appears when
something else, earlier in the same process, has already swapped the real
library out from underneath it.

## 5. Why it passed some runs and failed others

Running `pytest tests/unit/shared/test_transforms.py` **by itself** passed.
Running `pytest tests/` (the whole suite) **failed** with the error above,
36 times over (every test that touched astropy or sgp4 through
`src/shared/frames/transforms.py` or `src/propagation/`).

The reason is collection order combined with where each copy of the mocking
code lived:

- `tests/unit/conftest.py` only applies to files under `tests/unit/`. A
  first fix attempt (make just this file conditional) fixed
  `pytest tests/unit/` in isolation, but running the *full* `pytest tests/`
  — which also includes `tests/integration/` — still failed.
- `tests/integration/` sorts alphabetically *before* `tests/unit/`. pytest,
  by default, collects and imports files in that order. So
  `test_pipeline_integration.py`'s copy of the same unconditional mocking
  code ran and poisoned `sys.modules` *before* `tests/unit/conftest.py` (by
  then already fixed) ever got a chance to matter — the damage was already
  done by an entirely separate file, earlier in the run.

This is why the bug needed to be found and fixed in **two** places, not
one: fixing only `conftest.py` was necessary but not sufficient once the
whole test tree was run together, because the integration test carried an
independent copy of the same problem.

## 6. How the bug was actually found

1. Merged `origin/main` (which included AI-2's conjunction module, its test
   suite, and both files with the mocking code) into `feat/anas`.
2. Ran `pytest tests/` across the whole repository, as a "does everything
   still work together" sanity check.
3. Saw 36 failures, all in AI-1's own propagation/transform test files, all
   with the same `TypeError: isinstance() arg 2 must be a type...` error.
4. Ran one of the failing test files **on its own** — it passed. That
   ruled out a logic bug in the test or the code it was testing, and pointed
   at something environment/ordering-dependent instead.
5. Searched the repository for anything touching `sys.modules` directly —
   found the block in `tests/unit/conftest.py`.
6. Fixed that file to be conditional, re-ran `pytest tests/unit/` — passed.
   Re-ran the *full* `pytest tests/` — still failed, which meant there had
   to be a second source.
7. Searched again, specifically for the same `sys.modules[...] = MagicMock()`
   pattern anywhere else in the tree — found the identical block in
   `tests/integration/test_pipeline_integration.py`.
8. Applied the same conditional-import fix there. Full suite passed.

## 7. The fix

Applied identically in both files:

```python
import importlib
import sys
from unittest.mock import MagicMock

for _mod_name in (
    "astropy", "astropy.time", "astropy.coordinates", "astropy.units",
    "erfa", "sgp4", "sgp4.api", "sgp4.ext", "sgp4.earth_gravity",
):
    try:
        importlib.import_module(_mod_name)
    except Exception:
        sys.modules[_mod_name] = MagicMock()
```

`importlib.import_module(name)` behaves exactly like writing `import name`
— it performs a real import attempt. If the module imports successfully
(the normal case on most platforms), nothing further happens: the real
module is the one left sitting in `sys.modules`, exactly as if this code
didn't exist at all. Only if that import genuinely raises an exception —
the real deadlock/failure case the original code was trying to protect
against — does the `except` block substitute a `MagicMock` instead.

## 8. Why the fix is correct — what it preserves, what it changes

| | Original (unconditional) | Fixed (conditional) |
|---|---|---|
| Platform where astropy/sgp4 import fine | Faked anyway (wrong) | Real library used (correct) |
| Platform where astropy/sgp4 genuinely hang/fail | Faked (intended) | Faked (still intended — preserved) |
| Effect on conjunction module's tests | Unaffected either way (doesn't use these libraries) | Unaffected either way |
| Effect on AI-1's propagation/transform tests | Broken (real classes replaced with fakes) | Fixed (real classes available) |

The fix changes *when* the substitution happens (only on genuine failure,
never speculatively) without removing the capability the original author
needed. Nothing about the deadlock workaround's actual purpose is lost.

## 9. Verification performed

- `pytest tests/` (full repository): **131/131 passing** — 98 from AI-1
  (ingestion/propagation/shared) + 33 from AI-2 (conjunction).
- Repeated 3 times consecutively — deterministic, no flakiness.
- Re-run with an explicitly reordered file list
  (`tests/unit/shared tests/unit/propagation tests/integration tests/unit/conjunction tests/unit/ingestion`)
  — still 131/131, confirming the fix isn't itself order-dependent.
- AI-2's own standalone test runner (`scripts/run_unit_tests.py`, which
  doesn't use pytest at all): 32/32 passing.
- A real (non-mocked) end-to-end smoke test: live Celestrak data through
  ingestion → SGP4 propagation → AI-2's `ConjunctionPipeline.run()`
  directly, at both 300-object/24h and 800-object/72h (target) scale —
  completed in ~5.7s at target scale, produced 69 physically plausible
  conjunction events.
- `ruff` static check on both changed files: only the deliberately broad
  `except Exception` flagged (expected — annotated with
  `# noqa: BLE001` since "any import failure means fall back to mock" is
  the intended behavior, not an oversight).

## 10. Current status and what's still needed

Fixed and pushed to `feat/anas`:

- `e3461ea` — the conditional-import fix, both files.
- `e8ca3a2` — a follow-up sync merge from `origin/main` (an unrelated
  trivial rename, `sources/` → `resources/`) confirming the fix survives
  merging and the full suite still passes afterward.

**Not yet on `main`.** As of this writing, `origin/main`'s copy of
`tests/unit/conftest.py` is still the original unconditional version — this
bug is still live for anyone working directly off `main`. Landing the fix
there requires a pull request from `feat/anas`
(`https://github.com/Rushorgir/RADAR/pull/new/feat/anas` — GitHub's
pre-built compare link, not yet opened as of this writing since no `gh` CLI
was available in this environment to do it programmatically).

## 11. Broader lessons

- **A fix scoped wider than its problem can break things silently, far from
  where it was written.** The actual problem was "conjunction tests hang on
  one specific machine." The fix addressed "make these libraries fake
  everywhere, unconditionally, for everyone" — solving the narrow problem
  while introducing a much broader one, invisible unless someone runs the
  *whole* suite together on a machine where the original problem doesn't
  exist.
- **`sys.modules` mutation is process-global and sticky.** Anything that
  writes to it directly (rather than through normal `import` machinery)
  affects every subsequent import of that name in the same process, in
  every file, regardless of which module did the writing or why.
- **Test collection order matters more than it looks like it should.**
  pytest importing every test file up front (to discover tests) means
  module-level side effects in *any* test file — not just the ones you
  meant to run — can affect every other test file collected in the same
  session. Two files with the identical bug had to be found independently
  because fixing one wasn't visible as "incomplete" until the full suite
  was tested against the other.
- **"Passes in isolation" is not sufficient evidence "passes as part of the
  whole suite."** The failing tests here were individually correct and
  individually passing the entire time — the bug only manifested in
  combination with other files' side effects, which only running the full
  suite together would reveal.
