"""The seal on the held-out anchor.

This project has exactly one validation anchor, the Uzbek cotton affair. A detector chosen,
tuned or even eyeballed while its only test case is visible is fit and validated on the same
event, and the project's only real claim collapses. ``CONTRACT.md`` rule 5 therefore forbids
plotting, testing, scoring or summarising the anchor before gate G3 is signed.

A rule in a document is not enough, because the person who breaks it will be someone who
forgot. This module makes it something the code refuses to do.

What the seal is and is not
---------------------------
It is a guard against forgetting, not against a determined bypass. Anyone with write access to
this repository can create the unseal record by hand. That is deliberate and unavoidable: the
owner has to be able to lift the seal at G3, and no mechanism available here can distinguish
the owner lifting it deliberately from the owner lifting it early. What the seal does buy is
that lifting it is a **separate, deliberate, auditable act** that leaves a committed artefact,
rather than something that happens silently because a notebook cell had no filter on it.

What is permitted while sealed
------------------------------
Acquiring, transcribing, validating and checksumming the cotton data. Loading it into memory
through :func:`filter_sealed` so that the rest of a table stays usable. Counting how many rows
were withheld.

What is not
-----------
Any plot, statistic, score, distributional summary, or power curve fitted on it. Any
groupby that isolates the held-out unit. Any frame passing through code that cannot tell
whether it contains held-out rows.

Reading a row
-------------
The anchor's material arrives as transcribed Russian tables, so a row is recognised from what
those tables print, not only from English working labels:

* **Labels** are folded before they are compared: Cyrillic is transliterated, accents and
  apostrophes are dropped, case is ignored. One Latin vocabulary therefore covers the Russian
  spelling and the common transliterations of it (``khlopok``, ``hlopok``, ``xlopok``).
  :data:`UZBEK_SSR_PARTS` holds the republic, the Karakalpak ASSR and the oblasts, because a
  table by oblast is a breakdown of the anchor too; :data:`COTTON` holds the series.
* **The vocabulary rules a label out by default.** A readable label that names nothing in it
  is read as some other place or product: ``Kolkhozy``, a district, an abbreviation the list
  lacks. It is a deny-list. Refusing every label that cannot be mapped to a known region or
  series would need a vocabulary of every place and product a Soviet table prints, and this
  module does not have one.
* **Periods** are read with the transcription validator's own parser, so a plan period
  (``1976-1980``) or a crop year (``1984/85``) is held out whenever it overlaps the window.
* **A transcription is read through every column that says what a cell is**: both labels and
  their transliterations, the table heading, the volume and the definition note. Republics are
  printed as columns as often as rows, and in the Uzbek republic annual the region is named
  only on the title page.
* **Only a stub can rule a transcribed cell's region out.** A cell is placed by its row stub
  and its column head; the heading, the volume and the definition note describe the whole
  table. Any of them can show that a cell is in the anchor's region, but a heading that names
  no region (``Proizvodstvo khlopka-syrtsa``) says nothing about which region a row is, so the
  table-level columns never show that a cell is somewhere else.
* **Fail closed on values, not only on columns.** A row whose region, series or period is
  blank, carries no letters (a numeric code), or is in a script the fold cannot read, is one
  the seal cannot classify. While the seal is on that refuses the whole frame, unless another
  of the row's fields already shows it is not the anchor (a Kazakh row, a wheat series, 1990).
  In a transcription the same goes for a stub: a row stub or column head with no letters that
  is not the cell's own period (a row number on the right-hand page of a two-page table, a
  column number, an item code) may stand for the cell's region or its series, so nothing but
  the period can rule out a row that has one.

The aggregate question
----------------------
A union-level cotton total for 1980 contains the Uzbek figure inside it. Refusing every
aggregate that touches a held-out number would make the project impossible, because the
union-level series is most of what exists. The rule drawn here is narrower than that and
narrower than it first appears:

    An aggregate is permitted. A breakdown that isolates the held-out unit is not.

So summing cotton output across republics is allowed even though the total contains Uzbek
cotton, because the total does not tell you the Uzbek figure. Grouping the same frame *by
republic* is refused, because the resulting table has a row that is the anchor. The line is
whether the output lets a reader read off, or closely bound, the held-out quantity.

One consequence is enforced rather than left to prose. A table printed by republic carries its
own union total, and that total minus the other republics IS the Uzbek figure. So when
:func:`filter_sealed` withholds an anchor cell from a transcription, it also withholds every
printed total and subtotal in the same column or the same row, within the same table and
period: every cell there whose role is not ``data``. That is more than the totals the anchor
was summed into, because the seal does not know which group a subtotal sums: another group's
subtotal in the anchor's column goes too, and is counted in ``n_withheld``. A role that is
missing or unreadable counts as a possible total. The other republics stay. A union total
taken from a different table can still be differenced against them; that pair is assembled
across frames, which no single call can see, and it is forbidden in ``docs/HELD_OUT.md``.

This is the part of the seal most likely to be argued with later, and it should be: it is a
judgement about what counts as seeing something, not a fact. See ``docs/HELD_OUT.md``.
"""

from __future__ import annotations

import math
import numbers
import os
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from gosplan.transcribe.validate import period_years

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd

#: Repository root, found by walking up from this file.
_PROJECT_DIR = Path(__file__).resolve().parents[3]

#: The artefact that lifts the seal. It does not exist until a human writes it at G3, and it
#: must name the gate issue it was signed against, so that lifting the seal leaves a record
#: that can be read back and dated.
UNSEAL_RECORD = _PROJECT_DIR / "docs" / "G3_UNSEAL.md"

#: The line the unseal record must contain, exactly. Requiring a fixed declaration means the
#: file cannot be created by accident, and reading it tells you what was agreed.
UNSEAL_DECLARATION = "GATE G3 IS SIGNED AND THE GOSPLAN ANCHOR IS UNSEALED"

#: The token :func:`unseal` requires. It is not a secret and is not trying to be: the guard is
#: the recorded declaration, not the string.
UNSEAL_TOKEN = "g3-signed"

#: Set to any non-empty value to lift the seal for one process. This exists ONLY so the seal's
#: own tests can exercise the unsealed path without creating the record file. It is checked
#: after the record file, is never mentioned in user-facing errors, and must not appear in any
#: analysis code: a card that uses it is violating CONTRACT rule 5 by another route.
_TEST_OVERRIDE_ENV = "GOSPLAN_SEAL_TEST_OVERRIDE"


# ---------------------------------------------------------------- folding labels

#: Cyrillic letters to Latin, after accents are stripped and case is folded. Russian follows
#: the transliteration this project writes (``Narodnoe khoziaistvo``, ``Uzbekskoi``) without
#: its diacritics; the rest covers the other letters of the Soviet republics' Cyrillic
#: alphabets, Uzbek among them. Letters such as short i, short u and yo need no entry: they
#: decompose to a base letter that has one. Written with escapes because every source file in
#: this repository is ASCII.
_CYRILLIC_TO_LATIN: dict[str, str] = {
    "\u0430": "a",  # a
    "\u0431": "b",  # be
    "\u0432": "v",  # ve
    "\u0433": "g",  # ghe
    "\u0434": "d",  # de
    "\u0435": "e",  # ie
    "\u0436": "zh",  # zhe
    "\u0437": "z",  # ze
    "\u0438": "i",  # i
    "\u043a": "k",  # ka
    "\u043b": "l",  # el
    "\u043c": "m",  # em
    "\u043d": "n",  # en
    "\u043e": "o",  # o
    "\u043f": "p",  # pe
    "\u0440": "r",  # er
    "\u0441": "s",  # es
    "\u0442": "t",  # te
    "\u0443": "u",  # u
    "\u0444": "f",  # ef
    "\u0445": "kh",  # ha
    "\u0446": "ts",  # tse
    "\u0447": "ch",  # che
    "\u0448": "sh",  # sha
    "\u0449": "shch",  # shcha
    "\u044a": "",  # hard sign
    "\u044b": "y",  # yeru
    "\u044c": "",  # soft sign
    "\u044d": "e",  # e
    "\u044e": "iu",  # yu
    "\u044f": "ia",  # ya
    "\u0452": "dj",  # dje
    "\u0454": "ie",  # Ukrainian ie
    "\u0455": "dz",  # dze
    "\u0456": "i",  # Byelorussian-Ukrainian i
    "\u0458": "j",  # je
    "\u0459": "lj",  # lje
    "\u045a": "nj",  # nje
    "\u045b": "c",  # tshe
    "\u045f": "dzh",  # dzhe
    "\u0491": "g",  # ghe with upturn
    "\u0493": "g",  # ghe with stroke (Uzbek g')
    "\u0497": "zh",  # zhe with descender
    "\u0499": "z",  # ze with descender
    "\u049b": "q",  # ka with descender (Uzbek q)
    "\u04a1": "q",  # bashkir qa
    "\u04a3": "ng",  # en with descender
    "\u04ab": "s",  # es with descender
    "\u04af": "u",  # straight u
    "\u04b1": "u",  # straight u with stroke
    "\u04b3": "h",  # ha with descender (Uzbek h)
    "\u04b7": "j",  # che with descender
    "\u04b9": "ch",  # che with vertical stroke
    "\u04bb": "h",  # shha
    "\u04cf": "",  # palochka
    "\u04d9": "a",  # schwa
    "\u04e9": "o",  # barred o
}

#: Apostrophes and primes, which transliterations use for the soft and hard signs and Uzbek
#: Latin uses in o' and g'. Dropped, so ``O'zbekiston`` folds like ``Ozbekiston``.
_APOSTROPHES = "'\"`\u00b4\u2018\u2019\u201c\u201d\u02b9\u02ba\u02bb\u02bc\u02be\u02bf"

#: Hyphens and dashes inside a name are dropped, so ``Kara-Kalpak`` folds like
#: ``Karakalpak`` and ``khlopka-syrtsa`` keeps its ``khlop``.
_JOINERS = "-\u2010\u2011\u2012\u2013\u2014\u2212"

_FOLD_TABLE = str.maketrans(
    {**_CYRILLIC_TO_LATIN, **dict.fromkeys(_APOSTROPHES, ""), **dict.fromkeys(_JOINERS, "")}
)
_WORD_RE = re.compile(r"[a-z0-9]+")


@lru_cache(maxsize=8192)
def fold_label(text: str) -> tuple[str, ...] | None:
    """Fold a printed label into lowercase ASCII words, or None if it cannot be read.

    Accents are stripped, case is folded, Cyrillic is transliterated, apostrophes and hyphens
    inside a word are dropped, and everything else separates words. A label left holding a
    letter outside ASCII after that -- another script, or a Cyrillic letter the table above
    does not know -- returns None: the seal cannot say what it names, so it must not guess.

    Examples
    --------
    >>> fold_label("Uzbekskaya SSR")
    ('uzbekskaya', 'ssr')
    >>> fold_label("\\u0423\\u0437\\u0431\\u0435\\u043a\\u0441\\u043a\\u0430\\u044f \\u0421\\u0421\\u0420")
    ('uzbekskaia', 'ssr')
    >>> fold_label("O'zbekiston")
    ('ozbekiston',)
    >>> fold_label("\\u10e1\\u10d0\\u10e5\\u10d0\\u10e0\\u10d7\\u10d5\\u10d4\\u10da\\u10dd") is None
    True
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    folded = stripped.casefold().translate(_FOLD_TABLE)
    if any(ch.isalpha() and not ch.isascii() for ch in folded):
        return None
    return tuple(_WORD_RE.findall(folded))


@lru_cache(maxsize=256)
def _folded_forms(forms: tuple[str, ...]) -> tuple[str, ...]:
    out = []
    for form in forms:
        words = fold_label(form)
        if words:
            out.append("".join(words))
    return tuple(out)


def _names_any(words: tuple[str, ...], forms: tuple[str, ...]) -> bool:
    """Whether folded label words contain any of the forms.

    A form of three letters or fewer is an abbreviation and must be a whole word, so that
    ``uz`` does not fire inside ``Kuzbass``. Anything longer is matched as a substring of the
    label with its word breaks removed, so ``Syr-Darya``, ``Syr Darya`` and ``Syrdarya`` all
    contain ``syrdar``.
    """
    squeezed = "".join(words)
    for form in _folded_forms(forms):
        if len(form) <= 3:
            if form in words:
                return True
        elif form in squeezed:
            return True
    return False


# ---------------------------------------------------------------- the vocabulary

#: Every unit whose rows are the held-out region, with the folded forms that name it. A table
#: by oblast, or a row for the Karakalpak ASSR, is a breakdown of the Uzbek SSR, so each part
#: is the anchor as much as the republic is. The city of Tashkent shares its oblast's name, so
#: one entry covers both.
#:
#: Forms are written folded (see :func:`fold_label`), so each covers the Russian spelling once
#: transliterated and any Latin spelling that folds to it. ``tests/test_seal.py`` checks, for
#: every unit, the Russian name, the Uzbek one in Cyrillic, and several Latin spellings, ISO 9
#: and the scholarly system with their diacritics among them. Most forms are short stems, so
#: that the abbreviations tight tables print (``Andizh. obl.``, ``Karakalp. ASSR``) match as
#: well as the full names; the test spells every unit both ways.
#:
#: The list errs towards matching too much, because withholding a row by mistake costs a row
#: and showing one by mistake costs the project. What it cannot do is recognise a place it does
#: not name: no district (raion) is in it, and an oblast or an abbreviation missing from it
#: would pass, because a readable label it does not recognise is read as some other place, not
#: refused. Adding a form is always safe. A district table for the republic still carries the
#: republic in its heading or its volume, and a transcription is read through those too.
UZBEK_SSR_PARTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "Uzbek SSR": ("uzbek", "zbek", "usbek", "uzssr", "uz", "uzb"),
        "Karakalpak ASSR": ("karakalp", "qaraqalp", "qoraqalp", "kkassr"),
        "Andijan oblast": ("andij", "andiz", "andidj", "andidzh"),
        "Bukhara oblast": ("bukh", "buhar", "buxar", "bokhar", "buhoro", "buxoro"),
        "Jizzakh oblast": ("jizak", "jizzak", "jizzax", "zhizak", "zhizzak", "dzizak"),
        "Kashkadarya oblast": ("kashkad", "kaskad", "qashqad"),
        "Khorezm oblast": ("horezm", "xorezm", "horazm", "xorazm", "hwarazm", "hwarezm"),
        "Namangan oblast": ("namang",),
        "Navoi oblast": ("navoi", "navoy"),
        "Samarkand oblast": ("samark", "samarq"),
        "Surkhandarya oblast": (
            "surkhand",
            "surhand",
            "surxand",
            "surkhond",
            "surhond",
            "surxond",
        ),
        "Syrdarya oblast": ("syrdar", "sirdar"),
        "Tashkent oblast and city": ("tashk", "taskent", "toshk"),
        "Fergana oblast": ("ferg", "farg"),
    }
)

#: :data:`UZBEK_SSR_PARTS` as one tuple, the default :attr:`HeldOut.region`. ``uzbek`` comes
#: first because error messages name the region by its first form.
UZBEK_SSR: tuple[str, ...] = tuple(f for forms in UZBEK_SSR_PARTS.values() for f in forms)

#: Folded forms of the held-out series. ``hlop`` is the Russian root of ``khlopok``,
#: ``khlopka-syrtsa``, ``khlopkovoe volokno`` and ``khlopchatnik`` in every transliteration that
#: writes the first letter as kh, h or ch; ``xlop`` is the scholarly x. ``pakhta`` is Uzbek.
COTTON: tuple[str, ...] = ("cotton", "hlop", "xlop", "pakhta", "pahta", "paxta")

#: Other names of a held-out series, keyed by :attr:`HeldOut.series`. A series without an
#: entry is recognised by its own name only.
SERIES_FORMS: Mapping[str, tuple[str, ...]] = MappingProxyType({"cotton": COTTON})


# ---------------------------------------------------------------- the transcription schema

#: Columns of a transcription (``gosplan.transcribe.schema``) that can name the region a cell
#: belongs to. Republics are printed as rows or as columns, and a republic annual names its
#: republic only in the volume title.
SCHEMA_REGION_COLUMNS: tuple[str, ...] = (
    "row_label",
    "row_label_translit",
    "column_label",
    "column_label_translit",
    "title_ru",
    "title_translit",
    "volume",
)

#: Columns of a transcription that can name a cell's series: everything that can name its
#: region, plus the definition note copied from the table.
SCHEMA_SERIES_COLUMNS: tuple[str, ...] = (*SCHEMA_REGION_COLUMNS, "definition_note")

#: The transcription's period column: ``YYYY``, ``YYYY-YYYY`` or ``YYYY/YY``.
SCHEMA_PERIOD_COLUMN = "period"

#: The stubs of a transcription, each as printed and transliterated: the row stub and the
#: column head, which between them place one cell in its table.
SCHEMA_STUB_COLUMNS: tuple[tuple[str, str], ...] = (
    ("row_label", "row_label_translit"),
    ("column_label", "column_label_translit"),
)

#: Columns of a transcription that describe the whole table rather than one cell. They can
#: show that a cell is in the anchor's region, never that it is not: a heading that names no
#: region says nothing about which region each row is.
SCHEMA_TABLE_LABEL_COLUMNS: tuple[str, ...] = (
    "title_ru",
    "title_translit",
    "volume",
    "definition_note",
)

#: A frame holding all of these is read as a transcription, through every column above,
#: whatever column names the caller passes. All are required fields of the schema, so a blank
#: in any of them is a row the seal cannot read.
SCHEMA_IDENTITY_COLUMNS: tuple[str, ...] = (
    "row_label",
    "column_label",
    SCHEMA_PERIOD_COLUMN,
    "title_ru",
    "title_translit",
    "volume",
)

#: Columns that tell one printed table from another, when a frame holds several.
_SCHEMA_TABLE_COLUMNS: tuple[str, ...] = (
    "source_id",
    "volume",
    "edition_year",
    "page",
    "table_number",
    "title_ru",
)


class SealedError(RuntimeError):
    """Raised when an operation would expose the held-out anchor.

    The message always says what was withheld, why, and what would lift it, because the person
    hitting this is usually someone who did not know the seal existed.
    """


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        import pandas as pd

        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _year_span(value: Any) -> tuple[int, int] | None:
    """First and last year a year or period value covers, or None if it cannot be read."""
    if _is_blank(value) or isinstance(value, bool):
        return None
    if isinstance(value, numbers.Integral):
        return int(value), int(value)
    if isinstance(value, numbers.Real):
        f = float(value)
        if math.isfinite(f) and f.is_integer():
            return int(f), int(f)
        return None
    if isinstance(value, str):
        years = period_years(value)
        return (min(years), max(years)) if years else None
    return None


# Outcomes of reading one label.
_HELD, _CLEAR, _SILENT, _UNREAD, _BLANK = "held", "clear", "silent", "unread", "blank"


def _read_label(value: Any, forms: tuple[str, ...]) -> str:
    """Whether one label names the held-out unit, names something else, or cannot say.

    ``silent`` is a label with no letters, such as a year printed as a column head: readable,
    but it names nothing. ``unread`` is one the fold cannot read.
    """
    if _is_blank(value):
        return _BLANK
    return _read_text(str(value), forms)


@lru_cache(maxsize=8192)
def _read_text(text: str, forms: tuple[str, ...]) -> str:
    words = fold_label(text)
    if words is None:
        return _UNREAD
    if _names_any(words, forms):
        return _HELD
    if not any(ch.isalpha() for ch in "".join(words)):
        return _SILENT
    return _CLEAR


def _stub_names_nothing(label: Any, period: Any) -> bool:
    """Whether a transcription stub carries no letters and is not the cell's own period.

    A row number on the right-hand page of a two-page table, a column number or an item code
    stands where a region or a series would be printed, and says neither which of the two it
    stands for nor what that is. A year printed as a column head is the cell's period, which
    the seal reads separately, so it is not counted.
    """
    if _is_blank(label) or _read_text(str(label), ()) != _SILENT:
        return False
    span = _year_span(str(label))
    return span is None or span != _year_span(period)


def _combine_labels(readings: Sequence[tuple[str, bool]]) -> bool | None:
    """One axis of a row from several labels: True held, False clear, None cannot tell.

    Any label naming the held-out unit holds the row. Otherwise the row is clear only if some
    label names something else and none is unreadable or a blank required field.
    """
    if any(r == _HELD for r, _ in readings):
        return True
    if any(r == _UNREAD or (r == _BLANK and required) for r, required in readings):
        return None
    return False if any(r == _CLEAR for r, _ in readings) else None


@dataclass(frozen=True)
class HeldOut:
    """The rows nobody may look at before G3.

    Attributes
    ----------
    series : str
        Matched case-insensitively as a substring, so ``"cotton"`` catches "seed cotton",
        "cotton lint" and "raw cotton" without listing them. :data:`SERIES_FORMS` adds the
        series' other names, so ``"cotton"`` also catches the Russian and Uzbek ones. Labels
        are folded first, as for ``region``.
    region : tuple of str
        Any of these forms, found in a folded label, identifies the held-out unit (see
        :func:`fold_label`; a form of three letters or fewer must be a whole word). The default
        is :data:`UZBEK_SSR`: the republic, the Karakalpak ASSR and the oblasts, in the
        spellings the sources and their transliterations use.
    years : range
        Deliberately WIDER than the affair's own 1978 to 1983 window. A detector tuned on 1977
        and 1984 is still a detector tuned around the anchor, so the shoulder years are sealed
        too. A plan period or crop year is held out if it overlaps the window at all.
    reason : str
        Printed in every error, so the seal explains itself at the point of contact.
    """

    series: str = "cotton"
    region: tuple[str, ...] = UZBEK_SSR
    years: range = field(default_factory=lambda: range(1976, 1986))
    reason: str = (
        "the Uzbek cotton affair is this project's only validation anchor, so looking at it "
        "before the detectors are frozen would fit and validate them on the same event"
    )

    @property
    def series_forms(self) -> tuple[str, ...]:
        """The series' own name and the other names :data:`SERIES_FORMS` records for it."""
        return (self.series, *SERIES_FORMS.get(self.series, ()))

    def region_status(self, label: Any) -> bool | None:
        """True if a label names the held-out region, False if it names another, None if the
        label is blank, carries no letters, or cannot be read."""
        return _combine_labels([(_read_label(label, self.region), True)])

    def series_status(self, label: Any) -> bool | None:
        """As :meth:`region_status`, for the series."""
        return _combine_labels([(_read_label(label, self.series_forms), True)])

    def period_status(self, period: Any) -> bool | None:
        """True if a year or period overlaps :attr:`years`, False if it does not, None if it
        is missing or is not a year, ``YYYY``, ``YYYY-YYYY`` or ``YYYY/YY``."""
        span = _year_span(period)
        if span is None:
            return None
        lo, hi = span
        return any(lo <= y <= hi for y in self.years)

    def classify(self, region: Any, series: Any, year: Any) -> bool | None:
        """True if a row is held out, False if it is not, None if the seal cannot tell.

        A row is clear as soon as one of the three shows it is not the anchor, whatever the
        others say: a Kazakh row, a wheat series or 1990 needs nothing more.
        """
        return _combine_row(
            self.region_status(region), self.series_status(series), self.period_status(year)
        )

    def matches(self, region: Any, series: Any, year: Any) -> bool:
        """True if one row is held out. All three conditions must hold.

        False also when the row cannot be classified; :func:`held_out_mask` is what refuses
        such a row rather than letting it through.
        """
        return self.classify(region, series, year) is True


def _combine_row(region: bool | None, series: bool | None, period: bool | None) -> bool | None:
    if region is False or series is False or period is False:
        return False
    if region and series and period:
        return True
    return None


#: The one held-out set in this project.
HELD_OUT = HeldOut()


def _record_lifts_seal() -> bool:
    if not UNSEAL_RECORD.is_file():
        return False
    try:
        text = UNSEAL_RECORD.read_text(encoding="utf-8")
    except OSError:
        return False
    return UNSEAL_DECLARATION in text


def is_sealed() -> bool:
    """True while the anchor is hidden.

    The seal is lifted only by the unseal record: a committed file containing
    :data:`UNSEAL_DECLARATION`, written by a human at G3.
    """
    if _record_lifts_seal():
        return False
    return not os.environ.get(_TEST_OVERRIDE_ENV)


def unseal(token: str) -> None:
    """Assert that the seal is lifted, or raise explaining what is missing.

    This does not itself lift the seal, and cannot: there is deliberately no code path that
    creates :data:`UNSEAL_RECORD`. Lifting the seal is a human act at G3 that leaves a
    committed artefact. This function is how analysis code checks.

    Raises
    ------
    SealedError
        If the token is wrong, or the unseal record is absent or does not carry the
        declaration.
    """
    if token != UNSEAL_TOKEN:
        raise SealedError(
            f"wrong unseal token. The anchor stays sealed. {HELD_OUT.reason}. "
            f"After gate G3 is signed, the record at {UNSEAL_RECORD} lifts the seal."
        )
    if is_sealed():
        raise SealedError(
            f"the anchor is sealed: {UNSEAL_RECORD} does not exist or does not contain the "
            f"declaration {UNSEAL_DECLARATION!r}. {HELD_OUT.reason}. Lifting the seal is a "
            "human act at gate G3, not something code may do."
        )


# ---------------------------------------------------------------- reading a frame


@dataclass(frozen=True)
class _Source:
    """One column read for one of region, series and period."""

    column: str
    #: A blank in a required field leaves the row unclassified.
    required: bool
    #: Whether a label here that names something else can rule the anchor out. False for the
    #: table-level columns of a transcription on the region axis.
    rules_out: bool = True


@dataclass(frozen=True)
class _Reading:
    """Which columns are read for each of region, series and period."""

    region: tuple[_Source, ...]
    series: tuple[_Source, ...]
    period: tuple[_Source, ...]
    transcription: bool


def _reading(
    columns: Any, region_col: str, series_col: str, year_col: str
) -> tuple[_Reading | None, list[str]]:
    """Decide how a frame is read, or return the caller's missing columns if it cannot be.

    A frame can be read if it has the caller's three columns, or if it is a transcription
    (it has :data:`SCHEMA_IDENTITY_COLUMNS`). A transcription is always read through all of
    its labelling columns, in addition to whatever the caller named: naming one column can
    only add to what the seal reads, never narrow it. So on the region axis a table-level
    column (:data:`SCHEMA_TABLE_LABEL_COLUMNS`) of a transcription can hold a row but never
    rule it out, whoever named it.
    """
    present = set(columns)
    caller = {"region": region_col, "series": series_col, "period": year_col}
    missing = [c for c in caller.values() if c not in present]
    transcription = all(c in present for c in SCHEMA_IDENTITY_COLUMNS)
    if missing and not transcription:
        return None, missing

    def source(axis: str, col: str, required: bool) -> _Source:
        table_level = transcription and axis == "region" and col in SCHEMA_TABLE_LABEL_COLUMNS
        return _Source(col, required, rules_out=not table_level)

    axes: dict[str, list[_Source]] = {k: [] for k in caller}
    for axis, col in caller.items():
        if col in present:
            axes[axis].append(source(axis, col, True))
    if transcription:
        for axis, cols in (
            ("region", SCHEMA_REGION_COLUMNS),
            ("series", SCHEMA_SERIES_COLUMNS),
            ("period", (SCHEMA_PERIOD_COLUMN,)),
        ):
            for col in cols:
                if col in present and all(col != s.column for s in axes[axis]):
                    axes[axis].append(source(axis, col, col in SCHEMA_IDENTITY_COLUMNS))
    return (
        _Reading(
            region=tuple(axes["region"]),
            series=tuple(axes["series"]),
            period=tuple(axes["period"]),
            transcription=transcription,
        ),
        missing,
    )


def _stubs_naming_nothing(frame: pd.DataFrame) -> list[frozenset[str]]:
    """For each row of a transcription, the stub columns that name nothing the seal can read.

    A stub is the row stub or the column head, as printed and as transliterated. It names
    nothing when every label it has carries no letters and is not the cell's own period (see
    :func:`_stub_names_nothing`). Such a stub may stand for the cell's region or its series,
    so its columns are read as unreadable on both axes: nothing but the period can then rule
    the row out, though labels that name the anchor still hold it.
    """
    periods = frame[SCHEMA_PERIOD_COLUMN].tolist()
    out: list[set[str]] = [set() for _ in range(len(frame))]
    for pair in SCHEMA_STUB_COLUMNS:
        cols = [c for c in pair if c in frame.columns]
        values = [frame[c].tolist() for c in cols]
        for i, period in enumerate(periods):
            labels = [v[i] for v in values if not _is_blank(v[i])]
            if labels and all(_stub_names_nothing(label, period) for label in labels):
                out[i].update(cols)
    return [frozenset(s) for s in out]


def _classify_rows(frame: pd.DataFrame, reading: _Reading, held_out: HeldOut) -> list[bool | None]:
    columns = {
        s.column: frame[s.column].tolist()
        for s in (*reading.region, *reading.series, *reading.period)
    }
    unread = _stubs_naming_nothing(frame) if reading.transcription else [frozenset()] * len(frame)

    def axis(sources: tuple[_Source, ...], forms: tuple[str, ...], i: int) -> bool | None:
        readings = []
        for s in sources:
            if s.column in unread[i]:
                r = _UNREAD
            else:
                r = _read_label(columns[s.column][i], forms)
                if r == _CLEAR and not s.rules_out:
                    r = _SILENT
            readings.append((r, s.required))
        return _combine_labels(readings)

    series_forms = held_out.series_forms
    out: list[bool | None] = []
    for i in range(len(frame)):
        region = axis(reading.region, held_out.region, i)
        ser = axis(reading.series, series_forms, i)
        statuses = [held_out.period_status(columns[s.column][i]) for s in reading.period]
        if any(s is True for s in statuses):
            period: bool | None = True
        elif any(s is None for s in statuses):
            period = None
        else:
            period = False
        out.append(_combine_row(region, ser, period))
    return out


def held_out_mask(
    frame: pd.DataFrame,
    *,
    region_col: str = "region",
    series_col: str = "series",
    year_col: str = "year",
    held_out: HeldOut = HELD_OUT,
) -> Any:
    """Boolean mask of the held-out rows.

    A frame with the transcription schema's columns is read through all of its labelling
    columns (:data:`SCHEMA_REGION_COLUMNS`, :data:`SCHEMA_SERIES_COLUMNS`, ``period``) as well
    as any of ``region_col``, ``series_col`` and ``year_col`` it has. Any other frame is read
    through those three. In a transcription only a stub can rule a cell's region out, and a
    stub with no letters that is not the cell's period leaves both region and series open.

    Raises
    ------
    SealedError
        While the seal is on, if the frame lacks a column needed to identify held-out rows, or
        if any row cannot be classified: its region, series or period is blank, carries no
        letters, or cannot be read (in a transcription, a stub such as a row number counts),
        and nothing else in the row shows it is not the anchor. A frame that cannot be checked
        is refused rather than passed through: silently letting an unidentifiable frame past
        is exactly the failure this module exists to prevent, and a table with no region
        column may well BE the Uzbek series.
    """
    import numpy as np

    reading, missing = _reading(frame.columns, region_col, series_col, year_col)
    if reading is None:
        if is_sealed():
            raise SealedError(
                f"cannot tell whether this frame contains the held-out anchor: it has no "
                f"{missing} column(s), and it is not a transcription (which would need "
                f"{list(SCHEMA_IDENTITY_COLUMNS)}). Add them, or if the frame provably contains "
                "no Uzbek cotton data for 1976-1985, say so explicitly by passing "
                "declare_clean=True to filter_sealed. Guessing is not available while the seal "
                "is on."
            )
        return np.zeros(len(frame), dtype=bool)

    statuses = _classify_rows(frame, reading, held_out)
    unknown = [i for i, s in enumerate(statuses) if s is None]
    if unknown and is_sealed():
        first = unknown[0]
        cols = [s.column for s in (*reading.region, *reading.series, *reading.period)]
        shown = {c: frame[c].iloc[first] for c in dict.fromkeys(cols)}
        raise SealedError(
            f"cannot tell whether this frame contains the held-out anchor: {len(unknown)} "
            f"row(s) have a region, series or period that is blank, has no letters, or cannot "
            f"be read (in a transcription, a row stub or column head with no letters that is "
            f"not the cell's period, such as a row number, counts), and nothing else in the "
            f"row rules the anchor out. First: row "
            f"{frame.index[first]!a}, {shown!a}. Labels are read in Latin or Cyrillic, periods "
            "as YYYY, YYYY-YYYY or YYYY/YY. Fix the rows, or if the frame provably contains no "
            "Uzbek cotton data for 1976-1985, say so explicitly by passing declare_clean=True "
            "to filter_sealed. Guessing is not available while the seal is on."
        )
    return np.array([s is True for s in statuses], dtype=bool)


def _with_printed_totals(frame: pd.DataFrame, mask: Any) -> Any:
    """Extend a mask of anchor cells to every printed total and subtotal in their columns and
    rows.

    Only a transcription carries the layout this needs. A total is a cell in the same table
    and period as a withheld cell, in its column with a ``row_role`` other than ``data`` or in
    its row with a ``column_role`` other than ``data``. Repeated until nothing changes, so a
    grand total reached through a row total goes too. The roles do not say which cells a
    subtotal sums, so every subtotal there goes, another group's included.
    """
    import numpy as np

    n = len(frame)
    table_cols = [c for c in _SCHEMA_TABLE_COLUMNS if c in frame.columns]
    tables = list(zip(*(frame[c].astype(str).str.strip() for c in table_cols), strict=True))
    if not tables:
        tables = [()] * n
    periods = frame[SCHEMA_PERIOD_COLUMN].astype(str).str.strip().tolist()
    rows = frame["row_label"].astype(str).str.strip().tolist()
    cols = frame["column_label"].astype(str).str.strip().tolist()

    def not_data(role_col: str) -> list[bool]:
        if role_col not in frame.columns:
            return [True] * n
        return [str(v).strip().casefold() != "data" for v in frame[role_col].tolist()]

    row_total = not_data("row_role")
    col_total = not_data("column_role")

    down_column: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    along_row: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for i in range(n):
        if row_total[i]:
            down_column[(tables[i], periods[i], cols[i])].append(i)
        if col_total[i]:
            along_row[(tables[i], periods[i], rows[i])].append(i)

    withheld = {int(i) for i in np.flatnonzero(mask)}
    queue = list(withheld)
    while queue:
        i = queue.pop()
        for j in (
            *down_column.get((tables[i], periods[i], cols[i]), ()),
            *along_row.get((tables[i], periods[i], rows[i]), ()),
        ):
            if j not in withheld:
                withheld.add(j)
                queue.append(j)
    out = np.zeros(n, dtype=bool)
    out[sorted(withheld)] = True
    return out


def filter_sealed(
    frame: pd.DataFrame,
    *,
    region_col: str = "region",
    series_col: str = "series",
    year_col: str = "year",
    held_out: HeldOut = HELD_OUT,
    declare_clean: bool = False,
) -> tuple[pd.DataFrame, int]:
    """Drop the held-out rows and report how many went.

    Returns ``(frame, n_withheld)``. While the seal is lifted this is a no-op returning
    ``(frame, 0)``, so analysis code can call it unconditionally and stop being correct only
    because someone remembered.

    A transcription is filtered as transcribed, before it is reshaped: its own columns say
    what each cell is (see :func:`held_out_mask`), and its row and column roles say which
    cells are printed totals. Every printed total and subtotal in the same column or row as an
    anchor cell, within its table and period, is withheld with it and counted in
    ``n_withheld``, because a table's own union total minus the other republics is the anchor.
    A subtotal of another group in that column goes too, since the roles do not say what each
    subtotal sums.

    ``declare_clean=True`` asserts that the caller knows the frame contains no held-out data,
    for tables that legitimately lack a region or series column. It is an assertion by the
    caller, recorded in the call site, not a bypass: it does not lift the seal for anything
    else, and using it on a frame that does contain the anchor is a CONTRACT rule 5 violation.

    Raises
    ------
    SealedError
        As :func:`held_out_mask`: when the frame cannot be checked, or a row in it cannot be
        classified.
    """
    if not is_sealed():
        return frame, 0
    if declare_clean:
        return frame, 0
    mask = held_out_mask(
        frame,
        region_col=region_col,
        series_col=series_col,
        year_col=year_col,
        held_out=held_out,
    )
    reading, _ = _reading(frame.columns, region_col, series_col, year_col)
    if reading is not None and reading.transcription and mask.any():
        mask = _with_printed_totals(frame, mask)
    n = int(mask.sum())
    return frame.loc[~mask], n


def check_grouping(
    frame: pd.DataFrame,
    by: str | list[str],
    *,
    region_col: str = "region",
    series_col: str = "series",
    year_col: str = "year",
    held_out: HeldOut = HELD_OUT,
) -> None:
    """Refuse a grouping that would isolate the held-out unit.

    An aggregate is permitted; a breakdown is not. Summing cotton across republics is allowed,
    because the total does not tell you the Uzbek figure. Grouping the same frame by republic
    is refused, because one of the resulting rows IS the anchor.

    The test is deliberately simple and slightly conservative: if the grouping keys include a
    column that can name the region and the frame still contains held-out rows, refuse. For a
    transcription those columns are :data:`SCHEMA_REGION_COLUMNS`, since a republic can be a
    row stub, a column head or the volume. Anything subtler would need to reason about what an
    aggregate reveals, and being wrong in that direction is the expensive mistake.

    Raises
    ------
    SealedError
        If the grouping would isolate the anchor while the seal is on, or, when the keys
        include a region column, if the frame cannot be checked (see :func:`held_out_mask`).
    """
    if not is_sealed():
        return
    keys = [by] if isinstance(by, str) else list(by)
    reading, _ = _reading(frame.columns, region_col, series_col, year_col)
    region_keys = {region_col}
    if reading is not None:
        region_keys.update(s.column for s in reading.region)
    if not region_keys.intersection(keys):
        return
    mask = held_out_mask(
        frame,
        region_col=region_col,
        series_col=series_col,
        year_col=year_col,
        held_out=held_out,
    )
    n = int(mask.sum())
    if n:
        raise SealedError(
            f"grouping by {keys} would isolate the held-out anchor: {n} row(s) of "
            f"{held_out.series} for {held_out.region[0]} in {held_out.years.start}-"
            f"{held_out.years.stop - 1} are still in this frame. {held_out.reason}. "
            "Aggregate without the region key, or call filter_sealed first and report how "
            "many rows were withheld."
        )
