# The held-out anchor

**Nobody looks at Uzbek cotton for 1976 to 1985 until gate G3 is signed.**

This is the most important rule in the project and the one its only real claim depends on.

## Why

This project has exactly one validation anchor. A detector chosen, tuned, or merely eyeballed
while its single test case is visible is fit and validated on the same event. Whatever it then
reports about that event is not evidence, because the event is what shaped it.

With one anchor there is no way to recover from a peek. There is no second event to test on and
no way to unsee the first. So the protection has to be preventive, and it has to survive
somebody simply forgetting the rule exists, which is how it will actually be broken.

## What is sealed

| | |
|---|---|
| Series | anything whose name contains `cotton`, or the Russian or Uzbek word for it (`khlopok`, `khlopka-syrtsa`, `pakhta`) in Cyrillic or in any common transliteration |
| Region | Uzbek SSR, under any of the spellings the sources use, and every part of it: the Karakalpak ASSR, each oblast, and the city of Tashkent |
| Years | **1976 to 1985 inclusive**, and any plan period (`1976-1980`) or crop year (`1984/85`) that overlaps them |

The window is deliberately wider than the affair's own 1978 to 1983. A detector tuned on 1977
and 1984 is still a detector tuned around the anchor, so the shoulder years are sealed too. A
period that reaches into the window is sealed whole: `1975/76` and `1971-1980` both contain a
sealed year.

### How a row is recognised

The anchor's material arrives as transcribed Russian tables, so the seal reads what those
tables print, not only English working labels.

- **Labels are folded before they are compared.** Accents and apostrophes are dropped, case is
  ignored and Cyrillic is transliterated, so one Latin vocabulary covers the Russian spelling,
  the Uzbek one and their transliterations (`Uzbekskaia`, `Uzbekskaja`, `O'zbekiston`). The
  vocabulary is `UZBEK_SSR_PARTS` and `COTTON` in `src/gosplan/seal.py`, and
  `tests/test_seal.py` checks every unit in it in Russian, in Uzbek Cyrillic and in several
  Latin spellings. An oblast row is the anchor as much as the republic row is: a table by
  oblast is a breakdown of it.
- **Periods are read with the transcription validator's parser**, `period_years`, so the seal
  and the validator cannot disagree about which years a cell covers.
- **A transcription is read through every column that says what a cell is**: both labels and
  their transliterations, the heading in Russian and in transliteration, the volume and the
  definition note. Republics are printed as columns as often as rows, and the republic's own
  annual names the republic only on its title page.
- **The seal fails closed on values, not only on missing columns.** A row whose region, series
  or period is blank, has no letters in it (a numeric code), or is in a script the fold cannot
  read refuses the whole frame, unless something else in the row already rules the anchor out.
  A Kazakh row with an unreadable period is fine; an Uzbek cotton row with one is not.

What the vocabulary cannot do is recognise a place it does not name. No district (raion) is in
it. A district table for the republic still names the republic in its heading or its volume,
and a transcription is read through those. A loader that copies row stubs into a frame of its
own and drops the heading and the volume loses that, which is why a transcription is filtered
as transcribed, before it is reshaped.

## What you may and may not do

**Permitted while sealed.** Acquiring the data. Transcribing it. Validating and checksumming
it. Loading it through `filter_sealed` so the rest of a table stays usable. Counting how many
rows were withheld, and reporting that count.

**Not permitted.** Any plot, statistic, score, distributional summary, or power curve fitted on
it. Any breakdown that isolates it. Any frame passing through code that cannot tell whether it
contains held-out rows.

## The aggregate question, which is the interesting part

A union-level cotton total for 1980 contains the Uzbek figure inside it. If the rule were "no
number that a held-out value contributed to", the project would be impossible: the union-level
series is most of what exists, and the anchor is inside nearly all of it.

The rule drawn here is narrower:

> An aggregate is permitted. A breakdown that isolates the held-out unit is not.

Summing cotton across republics is allowed, because the total does not tell you the Uzbek
figure. Grouping the same frame **by republic** is refused, because one of the resulting rows
*is* the anchor. The line is whether the output lets a reader read off, or closely bound, the
held-out quantity.

`check_grouping` implements this conservatively: if the grouping keys include a column that can
name the region and held-out rows are still present, it refuses. For a transcription that is
either label, either heading, or the volume. Something subtler would have to reason about what a
given aggregate reveals, and being wrong in that direction is the expensive mistake.

### A table's own printed total

A table printed by republic carries its own union total, and that total minus the other
republics *is* the Uzbek figure. Withholding the Uzbek row and leaving the rest would hand over
every by-republic table with the differencing pair already in it. So when `filter_sealed`
withholds an anchor cell from a transcription, it also withholds every printed total and
subtotal that cell was summed into: the cells in the same table and period, down its column
with a `row_role` other than `data`, or along its row with a `column_role` other than `data`,
repeated until nothing changes so that a grand total goes too. A role that is blank or missing
counts as a possible total, so a table with no roles loses the whole period. The withheld
totals are counted in `n_withheld`.

The other republics stay. That is the narrower of the two ways to break the pair, and it keeps
every non-Uzbek figure usable; it does not stop a union total *from another table* being set
against them, which is the first soft spot below.

**This is a judgement, not a fact, and it is the part of the seal most worth arguing with.**
Two known soft spots, recorded rather than hidden:

1. **Differencing across tables.** A union total with Uzbekistan and the same total without it
   discloses the Uzbek figure exactly. Within one transcription the seal removes the table's
   own total, as above. It cannot see a pair assembled from two frames: a union series from one
   table and the other republics from another. `check_grouping` inspects one call at a time.
   Do not construct such a pair. Withholding every republic's cotton for the sealed decade
   would close this too, at the cost of all of them; that has not been decided.
2. **A small number of large units.** If the union total were dominated by two republics, the
   total plus one of them bounds the other tightly. For Soviet cotton this is a real risk, not
   a hypothetical, since production was concentrated in Central Asia.

Neither is machine-checkable here. They are why the rule is stated in prose as well as code.

## How the seal lifts

Only by a human act at G3 that leaves a committed artefact: a file at
`projects/gosplan/docs/G3_UNSEAL.md` containing, exactly,

```
GATE G3 IS SIGNED AND THE GOSPLAN ANCHOR IS UNSEALED
```

There is deliberately **no code path that creates that file**, and a test asserts as much. Code
may check the seal; only a person may lift it.

## What the seal is not

It is a guard against forgetting, not against a determined bypass. Anyone with write access can
create the record by hand. That is unavoidable: the owner must be able to lift the seal at G3,
and nothing available here can distinguish the owner doing that deliberately from the owner
doing it early.

What it buys is that lifting the seal becomes a separate, deliberate, auditable act that leaves
something in the history, instead of happening silently because a notebook cell had no filter
on it. That is the realistic threat model, and overstating it would be its own small dishonesty.

## Using it

```python
from gosplan.seal import filter_sealed, check_grouping

frame, n_withheld = filter_sealed(frame)
if n_withheld:
    print(f"{n_withheld} rows withheld: the held-out anchor (see docs/HELD_OUT.md)")

check_grouping(frame, ["region", "year"])  # raises while the anchor is present
```

Call `filter_sealed` unconditionally. After G3 it becomes a no-op returning `(frame, 0)`, so
analysis code does not become correct only because somebody remembered to change it.

A transcription is filtered as transcribed, straight from `read_filled`, before anything
reshapes it:

```python
from gosplan.transcribe import read_filled

frame = pd.DataFrame(read_filled(path))
frame, n_withheld = filter_sealed(frame)  # reads the schema's own columns
check_grouping(frame, ["row_label", "period"])
```

A frame with the schema's `row_label`, `column_label`, `period`, `title_ru`, `title_translit`
and `volume` columns is recognised as a transcription and read through all of them, whatever
column names are passed. Naming a column can only add to what the seal reads.

A table that legitimately has no region or series column cannot be checked, and is **refused**
rather than passed through, because a table with no region column may well be the Uzbek series
itself. The same goes for a row the seal cannot read, as above. If you know such a frame is
clean, say so explicitly with `declare_clean=True`. That is an assertion recorded at the call
site, not a bypass; using it on a frame that does contain the anchor is a violation of
`CONTRACT.md` rule 5.

## After G3

`held_out_mask` still identifies the anchor rows once the seal is lifted, and must: a later task needs
exactly that mask to build the `anchor_holdout` split, where detectors are fitted without ever
seeing the anchor and then asked to rank it. The seal hides the anchor; it does not forget where
it is.
