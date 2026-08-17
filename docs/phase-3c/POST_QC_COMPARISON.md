# Post-QC Comparison

Post-QC ran after each renderer process and remained outside `LegacyV4Renderer`.

| Check | Baseline | Facade | Equivalent |
| --- | --- | --- | --- |
| Local master status | pass | pass | yes |
| 15 bilingual lines | true | true | yes |
| 12 unique scenes | true | true | yes |
| Cover source recorded | true | true | yes |
| One project BGM | true | true | yes |
| Voice and word timing present | true | true | yes |
| H.264/AAC 720×960 delivery | true | true | yes |
| Public release allowed | false | false | yes |
| Release holds | H2 clearance required | H2 clearance required | yes |

The Facade adapter consumed only the current Attempt handoff, checked its Request and output hash,
and then supplied the corresponding isolated Project root to the unmodified legacy Post-QC CLI.
No directory scan or latest-file selection was used.
