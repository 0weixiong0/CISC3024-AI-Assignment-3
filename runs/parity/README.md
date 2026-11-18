# Parity gate logs — which one is the evidence

`python tests/test_parity.py` prints the M0 data assertions, then 11 gated and 7 diagnostic checks.
Several runs are kept on disk because the record cites them at different moments; only the two marked
**valid** describe the geometry as it now is, and the public repository carries only those two plus
`parity_report.json`.

| Log | Run at | Wall clock | M0 geometry line | Result | Status | In public repo |
| --- | --- | --- | --- | --- | --- | --- |
| `runs/parity/parity_after_readpgm_stdout.txt` | 2026-11-18 23:15 | 121 s | `per-image 112 rows x 92 columns = OK` | 11/11 gated, 18/18 reported, GATE OPEN | **authoritative** — the run after the header assertion was added to `src/orl.py::_read_pgm` | yes |
| `runs/parity/parity_rerun_stdout.txt` | 2026-11-18 03:41 | 89 s | `per-image 112 rows x 92 columns = OK` | 11/11 gated, 18/18 reported, GATE OPEN | **valid** — after `tests/test_parity.py` began reading `IMG_H`/`IMG_W` instead of hard-coding them | yes |
| `runs/parity_after_orlfix_stdout.txt` | 2026-11-18 02:58 | — | `per-image 92 x 112` | 11/11 gated, 18/18 reported | **pre-test-fix** — the test still hard-coded the swapped pair, so its M0 line is stale | no |
| `runs/parity_rerun_stdout.txt` | 2026-11-17 09:29 | — | `per-image 92 x 112` | 11/11 gated, 18/18 reported | **pre-fix** — the run that recorded the check-1e narrowing; cited in `stage_03b` §8 only as that day's event | no |
| `runs/parity/parity_stdout.txt` | 2026-11-17 04:03 | — | (before the M0 line existed in this form) | 11/11 gated, 18/18 reported | **pre-fix** — earliest run, superseded by everything above | no |

`parity_report.json` is rewritten by whichever run finished last (currently the 23:15 one) and carries
`gated: true/false` per check, which is where the front end's "11 gated + 7 diagnostic of 18" comes from.
The report files never carried per-check seconds, so the durations above come from the process start and
the log's last write.
