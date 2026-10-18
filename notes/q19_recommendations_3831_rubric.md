# Q19 recommendations: classification rubric

Source: the module docstring of `src/data_sheets_schema/q19_rationale_lint.py`
at origin/main c962a6cc8 (#3829, #3836). The wording below is the docstring's own.
Every example sentence, every count per class and every pinned sentence has been
removed; nothing else has been changed or added except the "How to answer" note.

## The ordered test

Each is classed by an ordered test, and the first question it answers yes to
decides its class. A recommendation's imperative is never itself the answer: a
sentence is read for what it says beside the imperative, and against its own
rating.

1. Does it name a slot's absence as a noun or a state? A named absence.
2. Does it say where a slot's content is instead: in another slot, a
   relation, prose, notes or a file? A placement. The step does not ask
   whether the slot is empty, nor whether the sentence also objects to a
   value. These two are misses. They are asked first, so a sentence that
   states an absence is a miss whatever else it asks for.
3. Does it name a populated value and object to it? Both parts must hold:
   a. it names a value the record holds (a populated slot, or an entry or
      item in one, by the slot's name, the entry's name or a value quoted
      from it) and asks for that value to be different, or for more of it:
      more entries, or more on an entry it holds. Re-expressing content in
      another slot or structure leaves the value it comes from as it is,
      and a release artifact a value points at (the RO-Crate) is not a
      value the record holds;
   b. its own rating faults that value in that respect: a weakness, issue,
      deduction, warning or quality note says the value is wrong or lacks
      what the sentence asks for. A fault found with another slot's
      absence does not count.
   If so, a criticism.
4. Otherwise it is a request: the imperative names a slot to fill.
   Requests are not counted as misses: a request presupposes an unfilled
   slot without stating one, and some are conditional.

## How to answer

Use exactly one of these labels per item: `named_absence`, `placement`,
`criticism`, `request`. Step 3b asks about the sentence's own rating: each
item's `sources` gives the rating file (copied under `q19_sources/`, same
relative path) and the JSON path of the sentence within it.
