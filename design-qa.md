# Core-first homepage design QA

Source visual truth: /Users/nicco/.codex/generated_images/01a12b20-97d7-72f3-af43-47040f96e9cc/exec-751f5071-e245-4cfc-a7a8-53f2fd32fa57.png (third displayed option selected by the user).
Implementation: http://127.0.0.1:4181/; first capture /private/tmp/aas-core-render.jpg.
Viewport and both images: 1487 x 1058 CSS/image pixels, density 1; default plan-preview state. Source and implementation were viewed together in one comparison input without modifying either image.

## First comparison

- [P2] Display titles were smaller/narrower than the selected reference. Increase headline and supporting-title size while retaining Outfit and adjusting line-height to preserve the composition.
- [P2] Header navigation was compressed at the right and the logo was too small. Match the reference's spacing, text size, separator and supplied AAS brand asset scale.
- [P2] Example columns had equal widths; the reference gives more space to the plan preview and a larger first transition gap. Adjust grid ratios.
- [P2] Setup heading was undersized and the example's top/content spacing displaced the lower row. Correct typography and vertical rhythm.

## Functional checks planned

Test stage buttons and keyboard movement, all recorded IDs, original manifest/plan data and historical version disclosure, primary setup links, plan-review handoff, preserved old overview URLs/anchors, separate catalog views and device-local collections, and responsive reflow. Root homepage must not fetch the catalog or initialize its persistence/provider. No new server, account, model or runtime service is introduced.

## Intentional content and asset details

The example uses the committed historical fixture (catalog v16.7.0), not the current release. Its original version and data are disclosed when opening an artifact. Main preview wording matches the selected mock; original recorded JSON is shown only on an explicit action. Existing AAS wordmark and Phosphor UI icons are retained. The orange setup mark is a generated raster recreation of the supplied mock asset; it does not assert provider endorsement. A concise Core-reference/boundary row and legal/project footer remain below the selected viewport.

## Comparison history and final evidence

Second capture: /private/tmp/aas-core-render-v2.jpg. Header scale, grid ratios and setup hierarchy were corrected. The remaining P2 display-size discrepancy was then corrected using a final typography pass after browser fonts finished loading.
Final capture: /private/tmp/aas-core-render-final.jpg, 1487 x 1058 pixels and CSS viewport. Both untouched source and final screenshot were opened together in one comparison input. Fonts were confirmed loaded; no density or frame normalization was required. The default stage is Plan preview with collapsed artifacts, matching the selected target.

Required surfaces checked: (1) display/UI typography and line wrapping, (2) page margins, hero/actions/example/setup vertical rhythm and grid ratios, (3) near-black/cyan tokens and foreground hierarchy, (4) supplied AAS wordmark, generated setup raster and Phosphor icons, and (5) visible navigation, headline, action, stage and setup copy. Main regions and controls match the selected direction without clipping or competing feature inventories. All labels/artifact fields are readable in the original full-view pair; focused typography and card geometry were additionally checked from browser computed styles and bounding rectangles. A separate crop was unnecessary for these readable regions.

Functional browser checks: Goal/Plan stage changes, original plan JSON and historical-version disclosure, setup anchor and mobile navigation, collections/workflow views, and old Core technical anchors redirected to the correct guide. Unit tests additionally cover tab keyboard focus and original artifact equality. Mobile capture: /private/tmp/aas-core-mobile.jpg, 390 x 844; document width stays 390, with intentional vertical reflow. Browser error logs were empty.

Residual P3: exact glyph geometry and standard terminal/file icon contours differ slightly from the generated reference; actual supplied branding, existing Outfit/JetBrains Mono fonts and licensed icon components are preserved. The Core boundary/footer appears below the selected viewport. No actionable P0/P1/P2 issue remains. This does not claim a full accessibility certification or a real new MCP execution.

final result: passed

## Current-base integration

Rebased onto protected main 6b8c84adbda971fc5886038c96bdd11954f6e4e3 (v19.4.0), preserving the intervening release and information-page SEO fix. The redirected overview is excluded from sitemap validation; product/catalog metadata are checked separately with all repository, count, preview and non-recommender assertions retained in the appropriate surface. The final current-base suite passes 301 web tests, 132 repository test groups, build/typecheck, production SEO, references, documentation security and changed-source lint.
