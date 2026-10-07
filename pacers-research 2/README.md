# Pacers research: 2026–27 outlook from a 2024–25 baseline

Analysis date: October 6, 2026. The user requested slide information, not a generated deck. This bundle includes the executed research scripts and result tables. Raw data files are downloaded separately. The optional archived_presentation folder preserves the draft presentation scripts used before the request changed to slide information only; it is not needed for the analysis.

## Reproduce

Use Python 3.11+ with pandas and numpy:

```sh
python -m pip install -r requirements.txt
python download_data.py --data data
python analyze.py --data data --out results
python lineups.py --results results
python sensitivity.py --results results
```

The download manifest pins repository commit e829d4678be1e075f99e5d41a1c5f97089be446b and verifies SHA256. Six CSV archives cover 1,230 regular-season games and 84 playoff games. Indiana has 82 regular-season and 23 playoff games. Repository: https://github.com/shufinskiy/nba_data

## Methods and limitations

- Repository season suffix 2024 means 2024–25; po_2024 means its playoffs.
- pbpstats rows repeat once per event-video link. Deduplicate all columns except DESCRIPTION and URL. Exclude empty possessions without shots, free throws or turnovers.
- Raw event points and shot charts supply season totals. Reconstructed possession counts differ from NBA official definitions. Never label reconstructed split rates as official NBA ratings.
- Quick attacks: possessions beginning after a miss, block or steal, ending within seven seconds, without an offensive rebound. This is a proxy, not player-tracking transition classification. Quick endings are selected, so their efficiency is not the causal benefit of accelerating every possession.
- After opponent makes is a possession-start proxy, not a literal halfcourt play-type label.
- OREB% counts player rebounds only: OREB/(OREB+opponent DREB). It excludes team rebounds and differs from NBA's broader convention.
- Favorable percentile = 100*(number of teams-average favorable rank)/(number of teams-1). Lower turnovers and opponent rim/quick frequencies are better. Percentiles compare all 30 regular-season teams.
- Restricted area means the source shot-zone label, not every attempt described informally as in the paint. High opponent rim frequency motivates a containment hypothesis; it does not isolate the perimeter defender or scheme.
- Lineups are inferred conservatively from events and substitutions. Reject ambiguous five-man lineups and possessions spanning substitutions. On/off is unadjusted and not individual causal impact.
- Sensitivity includes 5/7/8-second definitions, removal of lopsided minutes, game-cluster bootstrap, and exclusion of Finals Game 7.
- Source scoring discrepancies remain: regular possession sums differ from raw events in 223 team-games, totaling -292 points. Indiana's discrepancy is 8 of 9,624 points. Playoff Indiana possession points match raw events. See qa.json and discrepancy CSVs. Custom ratings should not be compared directly to NBA ratings.
- The season projection is a judgment-based scenario. The 30-team 2024–25 regression is wins=40.99369+2.16530*reconstructed net rating. Assumed future net ratings -2,+2,+4.5 imply 37,45,51 wins. The range is not a confidence interval; in-sample RMSE is not forecast uncertainty. The base assumes roughly65–70 Haliburton games with useful creation, not a medical prognosis.
- Trade values are analyst estimates, not sourced asking prices or cap-validated trades. Neutral matching salary is assumed. Mobility and defensive roles are scouting judgments; this repository does not measure player speed or deflections.
- Hauser's contract comparison is selective and descriptive, not a league-wide salary model. Joe's similar performance and Nesmith's broader role weaken any claim of unique underpayment.

## Main calculated results

Indiana: eFG56.16%(4th/90th percentile), turnovers13.19per100(3rd/93rd), playerOREB21.29%(29th/3rd), opponent restricted-area frequency30.09%(22nd in prevention/28th), opponent restricted-area accuracy65.46%(ninth-lowest). Quick attacks allowed13.36% of possessions, lowest. Quick offense150.79per100 regular and150.16 playoffs; after opponent makes115.69 and108.91. East playoff offense119.31per100 with12.71%TOV; Finals109.22 with18.59%TOV. Turnovers remain17.57% excludingGame7.

Hauser:166/399threes=41.60%,rank18of197 with200+attempts,91st percentile. Tatum off73/186=39.25% on valid lineups. Assisted made threes95.18%. Unadjusted net on/off-0.42points100. Playoffs7/21threes. A200-attempt league-average prior shrinks his shooting estimate to39.74%.

2024–25 contract peers: IsaiahJoe192/466=41.20%, SamMerrill137/368=37.23%, AaronNesmith84/195=43.08%. Contracts are2026–27 salaries, not2024–25 pay: Hauser10,848,215;Joe11,323,006;Merrill9,160,715;Nesmith11,000,000.

## External facts and sources

Official Indiana 2024–25 ratings: Off115.4(9th),Def113.3(14th),Pace100.76(7th). The NBA API timed out; figures cross-checked using the NBA results and NBC recap:
- https://www.nba.com/stats/teams/advanced?Season=2024-25&SeasonType=Regular+Season
- https://www.nba.com/stats/teams/advanced?Season=2024-25&SeasonType=Playoffs
- https://www.nbcsports.com/fantasy/basketball/news/indiana-pacers-2024-2025-fantasy-basketball-season-recap-what-the-hali
- https://www.nba.com/news/2026-27-season-preview-ind
- https://www.nba.com/clippers/news/clippers-acquire-mathurin-jackson-and-two-first-round-picks-from-indiana

Current salaries/teams and Hauser peers:
- https://www.salaryswish.com/players/jaxson-hayes (UTA,$6M)
- https://www.salaryswish.com/players/matisse-thybulle (LAL,$3,286,399salary,$2,449,421cap)
- https://www.salaryswish.com/players/royce-oneale (CHA,$10,875,000)
- https://www.salaryswish.com/players/robert-williamsiii (POR,$14M)
- https://www.salaryswish.com/players/sam-hauser
- https://www.salaryswish.com/players/isaiah-joe
- https://www.salaryswish.com/players/sam-merrill
- https://www.salaryswish.com/players/aaron-nesmith
- https://www.salaryswish.com/players/max-strus
- https://www.basketball-reference.com/contracts/players.html

Williams salary differs slightly between SalarySwish($14M) and Basketball-Reference($13,968,254); use approximately$14M. SalarySwish lists a3year$43.5M extension with$19M initially guaranteed.

Thybulle's2023–24NBA bio reports5.3deflections/36(league-leading) and34.6%3P. His2024–25PBP supports2.2steals/game and43.8%3P on only48attempts/15games. Deflections are external tracking evidence, not reconstructed PBP:
- https://www.nba.com/player/1629680/matisse-thybulle/bio

Royce defensive versatility and current destination:
- https://www.nba.com/suns/news/suns-acquire-royce-oneale-and-david-roddy-in-three-team-trade-with-brooklyn-and-memphis
- https://www.nba.com/hornets/news/charlotte-hornets-acquire-allen-oneale-first-round-pick

Hauser2025–26recent check:39.3%3P on6.5attempts/game.2026–27NBAcap$164,961,000:
- https://www.basketball-reference.com/players/h/hausesa01.html
- https://www.nba.com/news/nba-salary-cap-2026-27-season

## Later 2025–26 trade-target update

The trade-target statistics in the final wording were researched from public web tables, not computed by the 2024–25 Python pipeline. Do not present them as outputs of that pipeline. Exact source URLs and the transcribed figures are included in trade_targets_2025_26_sources.json. Salaries remain 2026–27 and are sourced separately above. Trade valuations and basketball fit are analyst judgments, not model outputs.

## Code inventory

- download_data.py: retrieves the pinned six input archives and checks hashes.
- analyze.py: deduplicates possessions, aggregates event/shot/team/player metrics, calculates splits, exports QA and fits the wins regression.
- lineups.py: reconstructs conservative five-player lineups and measures selected on/off and Hauser/Tatum shooting context.
- sensitivity.py: checks pace-proxy thresholds, playoff exclusions, bootstrap uncertainty, shooting shrinkage and forecast scenarios.
- exploratory/inspect_data.py: initial archive/schema/coverage inspection; paths are relative to the original workspace.
- archived_presentation/: original draft builder, earlier builder revision, revision script and chart-input preparation, preserved for completeness. This uses the Codex bundled @oai/artifact-tool runtime and presentation helpers; it is not a standalone Python dependency. No generated deck is included.

The main Python scripts are the reusable research code. Web searches and brief terminal inspection commands were interactive research steps, not a separate saved scraping program.
