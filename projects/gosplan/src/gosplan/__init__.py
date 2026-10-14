"""gosplan -- the target project. Soviet economic statistics, almost no ground truth.

Methods validated on elections / aaer / china are transferred here through
forensics_core.eval.harness. Much of the source material is scanned Russian-language tables;
this package is built around transcription, schema validation and provenance, not downloads.

Three subpackages and one helper module:

* :mod:`gosplan.acquire` -- the machine-readable sources the registry verified, fetched
  through the shared provenance layer. The CIA reading room blocks scripted access, so the
  archive.org mirror is used instead.
* :mod:`gosplan.transcribe` -- the central deliverable: a schema for a transcribed printed
  table, generated forms, validators, and a double-transcription comparison that measures the
  per-digit-position disagreement rate a digit test needs before it means anything.
* :mod:`gosplan.analysis` -- stubs only. No number is computed from data anywhere in this tree.
* :mod:`gosplan.anchor_rank` -- reads the anchor's rank off a full-panel score table handed to
  it, against the pre-registered comparator set. Bookkeeping, not analysis: it fits and
  estimates nothing, and before G3 it is only run on synthetic fixtures.
"""

__version__ = "0.1.0"
