# P9-D addendum A1 (Marco, 23 Oct 2026; committed before any P9-D run)

Applies to `eval/phase9/P9-D/criterion.md` (b7aa79f).

## A1.1 File artefact

Lines 125–135 of `criterion.md` (stray `</document_content>` / `</documents>` markup after section 10) are a file artefact from writing the file. They are **not** criterion content. The criterion ends at section 10.

## A1.2 Foot rows for the evaluation sequences (input generation, not data)

**Why.** The LEV arm uses a foot contact only when a perception row carries one (`F` rows; `hasFoot`, `PedestrianBA.cc`). The evaluation sequences have only `P` and `C` rows (`~/datasets/p9c_perception`, `p9c2_perception`). Without `F` rows, LEV would equal ON.

**What.** Generate `F` rows (the midpoint contact, as used by the levels module) for subway_s1_36h, subway_s1_24h and office_s1_06h:

- With **exactly** the scripts, model weights and parameters that produced the tuning sequences' `F` rows in the perception directory the levels runs used. Identify that directory (`p9c3c_perception` or the one `run_p9c_one.sh` defaults to) and the scripts (for example `p9c3_add_feet.py` and the RTMW pipeline in `P9-C2/perception/`), and record their md5s in `prerun.md` before generating.
- Without changing the existing `P` and `C` rows. Verify them by md5 per frame file, or per directory, before and after.
- Into a perception directory with the same layout. That directory is what every P9-D arm uses, so OFF, ON and LEV read identical inputs; OFF and ON never read the `F` rows.

**What may be read.** Only the **count** of `F` rows per sequence, and the share of person rows that carry one, as a coverage figure for `prerun.md`. No contact pixel, geometry, level or any other content of the evaluation-sequence rows is inspected.

## A1.3 D1-P with LEV

D1-P with LEV (criterion §7.1) runs after A1.2, on the new perception directory: subway_s1_24h, `FloorContact: levels`, 5 identical invocations, md5 only.

Also confirm, from the run's per-factor **counter file md5 and line count only**, that level code executed: the counter file must contain the level/contact factor columns, with non-empty rows. No counter values are read.

## A1.4 Execution host

Runs execute on workstation-1. Before D1-P and before the campaign:

- sync with `P9-C5/tools/sync_ws.sh`;
- record, in `prerun.md`, the md5s on workstation-1 of: the binary list of `P9-C2/final_binaries.md`, the configs (`none.yaml`, `levels.yaml`, the OFF config), `p9d_analyze.py`, the campaign script, and the perception directory manifest;
- they must equal the laptop's. A mismatch stops the task.

If an additional host is used later, the same verification applies to it.
