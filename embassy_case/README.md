# Embassy REIT / Manyata public-data investment case

Prepared 22 October 2026. Read `Embassy_Investment_Memo.pdf` and open `Embassy_Manyata_Acquisition_Case.xlsx`. This is a historical research case with analyst-assumed acquisition terms, not a real transaction or realised performance.

The Source and NAV worksheet records source URLs, PDF pages, observation dates, access date (22 October 2026), units and transformations. Every forecast lease and financing term is labelled as an assumption. Original issuer reports are not redistributed.

## Reproduce the calculation checks
Requires Python 3.10+ standard library only:
```
python embassy_case/verify_case.py
```
This independently recalculates six return metrics for base, upside and downside and compares them to the saved workbook-engine evidence. It does not execute Microsoft Excel or prove the exported workbook recalculates identically there. Workbook formulas and native data tables remain available for inspection.

## Excel verification pending
Open in desktop Excel; select Automatic calculation including Data Tables; press Ctrl+Alt+F9. For base case, check both table centers equal Returns D6 and Checks D9:D12, D14:D15 are within stated tolerances. Change a noncentral grid assumption, compare the direct model result, then restore and save. Record Excel version, date and reviewer. Current engine cannot reliably propagate data-table results into linked Check formulas, so those checks may remain n.a. until native recalculation.

## Main limitations
One occupied lease cohort, annual debt payments, pre-tax cash flows, no vacant-area lease-up, no hotels/development, net-expense proxy rather than reported gross expense, annualised quarter rather than forward NOI. March NAV and June price are deliberately different dates. No verified transaction cap-rate comps or independent professional review. See the memo before interpreting the results.
