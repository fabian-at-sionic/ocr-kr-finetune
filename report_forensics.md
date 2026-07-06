# Phase 2 Forensic Report
Generated: 2026-07-04 12:34 KST
Scope: saved candidate outputs only. No training and no full benchmark rerun were performed. Raw DocTags were read from each candidate `doctags/` directory; scorer markdown and progress/error JSONL files were used as metadata.
Note on tails: the report displays decoded tails after re-tokenizing the persisted raw DocTags with the local Granite Docling tokenizer. The stored `generated_tokens` values in `run_progress.jsonl` remain the authoritative generation lengths.
## One-page summary
- Base cap hits: 63/849 (7.42%). Tail classification: {'REPETITION': 63}. All base cap hits are repetition loops; none are classified as progressing content.
- Overfit cap hits: 213/849 (25.09%). Tail classification: {'REPETITION': 213}. This is the same failure mode at a much higher rate.
- Recommended `max_new_tokens`: keep 8192 for this setup. The observed cap hits are repetition-driven, so increasing the cap would not cover real progressing pages; it would mostly allow loops to run longer. With the current evidence, the expected still-capped share after any larger cap is at least 7.42% for base and 25.09% for overfit unless loop behavior is fixed.
- Overfit parse exceptions: 27 total, all reported as IndexError('list index out of range') x 27. Overlap with cap hits: 2/27. Primary raw-DocTags classifications: {'bad loc token': 20, 'OTSL grid violation': 6, 'unclosed/mismatched tag': 1}.
- Base parse exceptions: 0 in `run_progress.jsonl`; `errors.jsonl` exists: False. This confirms the reported 0 exceptions from raw outputs rather than score aggregation alone.
- Base repetition clusters over-index on Notices and housing/recruitment notice pages. Candidate 1k-slice targets: LH/public-housing recruitment notices, regulatory/policy guides, statistics/yearbook/survey pages, report/white-paper pages with repeated short text bands, and schedule/notice pages.
- No fixes were applied.
## Token-length distributions
| run | n | min | p25 | p50 | p75 | p90 | p95 | max | mean | capped |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| base | 849 | 23 | 202 | 590 | 1315 | 7623 | 8192 | 8192 | 1663.8 | 63 (7.42%) |
| overfit_26 | 849 | 115 | 1746 | 3203 | 8192 | 8192 | 8192 | 8192 | 4352.1 | 213 (25.09%) |

Both capped subsets pile up exactly at 8192 by definition and by saved termination flags. Among capped generations, the progressing-count distribution is empty because all capped tails were repetitive.
## Category and visual clustering
| category | overall n/% | base capped n/% | relative share | overfit capped n/% |
|---|---:|---:|---:|---:|
| Statistics | 283 (33.33%) | 10 (15.87%) | 0.48x | 54 (25.35%) |
| Reports | 238 (28.03%) | 18 (28.57%) | 1.02x | 52 (24.41%) |
| Manuals | 216 (25.44%) | 15 (23.81%) | 0.94x | 63 (29.58%) |
| Notices | 112 (13.19%) | 20 (31.75%) | 2.41x | 44 (20.66%) |

Structure indicators from raw DocTags:
| run/subset | table-like OTSL | >=25 text blocks | malformed loc token | page footer | median DocTags chars |
|---|---:|---:|---:|---:|---:|
| base overall | 90.0% | 9.9% | 0.0% | 52.9% | 1147 |
| base capped | 49.2% | 11.1% | 0.0% | 3.2% | 8013 |
| overfit overall | 80.0% | 56.8% | 79.7% | 2.5% | 6411 |
| overfit capped | 66.7% | 60.6% | 77.5% | 0.0% | 13055 |

Base capped pages are disproportionately `Notices` and are less table-like than the full benchmark output set. Their raw DocTags are much longer because the generation loops, not because the page continues with useful structure.
Named page-type clusters in base capped pages:
- LH / housing recruitment notices: 15 examples; sample: 한국토지주택공사_3기신도시 사전청약 모집공고1 1.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 11.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 17.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 3.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 4.pdf
- Regulatory / policy guides and manuals: 10 examples; sample: (제1유형) 국토교통부_규제안내서 10.pdf; (제1유형) 국토교통부_규제안내서 2.pdf; (제1유형)_개인정보보호위원회_개인정보 유출 등 사고 대응 매뉴얼 5.pdf; (제1유형)_서울시설공단_안전보건경영시스템 현장매뉴얼 41.pdf; 국세청_업무용승용차 관련 비용의 세무처리(법인세) 39.pdf
- Statistics/yearbook/survey pages: 10 examples; sample: (제1유형)_통일부_개성공단 현황 1.pdf; [제1유형] 건강보험심사평가원_건강보험통계연보 200.pdf; [제1유형] 한국가스안전공사_가스통계 DB 23.pdf; 국민건강보험공단_건강보험주요통계 12.pdf; 농림축산식품부 농림축산검역본부_반려동물 보호복지 실태조사 8.pdf
- Reports/white papers/research summaries: 15 examples; sample: (제1유형)_행정안전부_정책연구과제 142.pdf; [제1유형] 중앙선거관리위원회_전국동시지방선거 투표율 분석 57.pdf; 국토교통부_리츠정보_영업보고서4 7.pdf; 금융위원회_공적자금백서 38.pdf; 법무부_이민정책연구자료 현황2 33.pdf
- Schedules/tables/notices: 17 examples; sample: 한국전력공사_전기요금표 2.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 1.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 11.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 17.pdf; 한국토지주택공사_3기신도시 사전청약 모집공고1 3.pdf

## Cap-hit details: base run
Classification method: final 300 model-token tail was tested for exact repeated suffix loops, repeated n-grams, and low-diversity token tails. All rows below have `generated_tokens=8192`, `terminated=false`, and `hit_cap=true` in saved metadata.

### Base cap 1: (제1유형) 국토교통부_규제안내서 10.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 52 x 3 tokens, covers 156/300; pattern='간, 시'
- last 300 tokens:

```text
간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간, 시간, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간이, 시간, 시간이, 시간, 시간, 시간이, 시간, 시간, 시간, 시간이, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시간, 시
```

### Base cap 2: (제1유형) 국토교통부_규제안내서 2.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 56 x 21-token ngram, coverage 3.92, unique_ratio 0.05; pattern=', 0, 0, 0, 0, 0, 0, 0'
- last 300 tokens:

```text
중수, 이나의 가중수, 이나의 가중수, 이나의 가중수, 이나의 가중수, 이나의 가중수, 이나의 가중수, 이나의가중수, 이하고, 0, 이하고, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0; 0, 0, 0, 0, 0, 0, 0, 0, 0. 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
```

### Base cap 3: (제1유형)_개인정보보호위원회_개인정보 유출 등 사고 대응 매뉴얼 5.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 8 x 21-token ngram, coverage 0.56, unique_ratio 0.08; pattern='에게 긴안의 금토를 신고치지약이'
- last 300 tokens:

```text
에게 긴안의 금토를 신고치지약이너지에게 긴안의 금토를 신고치지약이너지에게 긴안의 금토를 신고치지약이너지에게 긴안의 금토를 신고치지약이너지에게 긴안의 금토를 신고치지약이너지에게 긴안의 금토를 신고치지약이너지에게 긴안의 금토를 신고치지약이너지에게 긴안의 금토를 신고치지약이너지에게 긴토이너지에게 긴토이너지에게 긴토이너지에게 긴토이너지에게 긴토이너지에게 긴토이���이너지에게 긴���이너지에게 긴��이너지에게 긴�ي�
이너지에게 긴�ي                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
```

### Base cap 4: (제1유형)_서울시설공단_안전보건경영시스템 현장매뉴얼 41.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 300 x 1 tokens, covers 300/300; pattern='안'
- last 300 tokens:

```text
 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안 안
```

### Base cap 5: (제1유형)_통일부_개성공단 현황 1.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 93 x 2 tokens, covers 186/300; pattern='The'
- last 300 tokens:

```text

</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
</doctag>
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
The
```

### Base cap 6: (제1유형)_행정안전부_정책연구과제 142.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 42 x 8-token ngram, coverage 1.12, unique_ratio 0.03; pattern='<doctag> <doctag> <doctag> <doctag>'
- last 300 tokens:

```text
<loc_30></text>
<loc_30></text>
<loc_30></text>
</text>
<loc_30></text>
<loc_30></text>
<loc_30></text>
<loc_30></text>
<loc_30></text>
<loc_30>
</text>
</text>
</text>
</text></text>
</text>
</text>
</text></text>
</text>
</text>
</text>
</text>
</text>
</text>
</text>
</text>
</text></text>
</text>
</text></text>
loc_30></text>
loc_30>
loc_30>
loc_30>
</text>
</text>
loc_30
<doctag>
<doctag></text>
<doctag></text>
<doctag>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag></text>
<doctag>
<doctag></text>
<doctag>
<doctag></text>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag></text>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag></text>
<doctag></text>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag></text>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag></text>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag></text>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>
<doctag>

```

### Base cap 7: (제1유형)_행정안전부_행정절차 195.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='1'
- last 300 tokens:

```text
 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
```

### Base cap 8: [대량] 부산광역시_관광지도 33.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='1'
- last 300 tokens:

```text
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 
```

### Base cap 9: [대량] 한국토지주택공사_전문시방서 25.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='·시'
- last 300 tokens:

```text
·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시·시
```

### Base cap 10: [제1유형] 건강보험심사평가원_건강보험통계연보 200.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 100 x 3 tokens, covers 300/300; pattern='1000'
- last 300 tokens:

```text
 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000 1000
```

### Base cap 11: [제1유형] 기상청_기상연감(연간) 197.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='1'
- last 300 tokens:

```text
 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1
```

### Base cap 12: [제1유형] 중앙선거관리위원회_전국동시지방선거 투표율 분석 57.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 140 x 21-token ngram, coverage 9.80, unique_ratio 0.01; pattern='�ｅｅｅｅｅｅｅｅｅｅ'
- last 300 tokens:

```text
�ｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅｅ�
```

### Base cap 13: [제1유형] 한국가스안전공사_가스통계 DB 23.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 43 x 3 tokens, covers 129/300; pattern=', 공'
- last 300 tokens:

```text
 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공, 공�, 공, 공, 공, 공, 공�, 공�, 공�, 공�, 공�, 공�, 공�, 공, 공, 공, 공�, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공, 공
```

### Base cap 14: [제1유형] 한국수출입은행_국내외거시경제동향 5.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 275 x 21-token ngram, coverage 19.25, unique_ratio 0.01; pattern='<lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lc...'
- last 300 tokens:

```text
<lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
```

### Base cap 15: 고용노동부_외국인력 도입계획 5.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 19 x 3 tokens, covers 57/300; pattern='∏…'
- last 300 tokens:

```text
포포포포포포포포포폏�폏�폏�폏�폏���������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������…∏∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏���…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…∏…
```

### Base cap 16: 국민건강보험공단_건강보험주요통계 12.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 100 x 3 tokens, covers 300/300; pattern='10,'
- last 300 tokens:

```text
 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
```

### Base cap 17: 국세청_업무용승용차 관련 비용의 세무처리(법인세) 39.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='1'
- last 300 tokens:

```text
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 
```

### Base cap 18: 국세청_해외주식과 세금 6.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 25 x 3 tokens, covers 75/300; pattern='. 772'
- last 300 tokens:

```text
. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 712 72 772. 772. 772. 772. 772. 772. 772. 772. 772. 201 201 201 201 201. 201. 201. 201. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772. 772
```

### Base cap 19: 국토교통부_리츠정보_영업보고서4 7.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 49 x 21-token ngram, coverage 3.43, unique_ratio 0.01; pattern='3 1 3 1 3 1 3 1 3 1'
- last 300 tokens:

```text
 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 3 1 1 3 1 3 1 1 3 1 1 3 1 3 1 3 1 3 1 3 1 1 3 1 1 3 1 1 3 1 1 3 1 1 3 1 3 1 3 1 3 1 1 3 1 1 3 1
```

### Base cap 20: 국토교통부_주택청약 및 공급규칙 FAQ 158.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 90 x 21-token ngram, coverage 6.30, unique_ratio 0.02; pattern='������������������������������������������������������������������������������������'
- last 300 tokens:

```text
��ㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧ�ㄧ�����������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������
```

### Base cap 21: 국토교통부_환경관리비 산출 정보 49.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 101 x 21-token ngram, coverage 7.07, unique_ratio 0.05; pattern='������������������������������������������������������������������������������������'
- last 300 tokens:

```text
ㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧㄧ�ㄧㄧ�ㄧㄧ�ㄧ�ㄧ�ㄧ�ㄧ�ㄧㄧ��ㄧ�ㄧ�ㄧ��ㄧ�ㄧ��ㄧ����������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������� �                                                          
                                   

  



 ������������������������������������������������������
```

### Base cap 22: 근로복지공단_가입 및 부과업무 실무편람 204.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 85 x 3 tokens, covers 255/300; pattern='0%'
- last 300 tokens:

```text
 0% 성분 � 0% 성분 0% 성분 � 0% 성분 0% 성분 0% 성분 0% 성분 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 0% 
```

### Base cap 23: 금융위원회_공적자금백서 38.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 274 x 21-token ngram, coverage 19.18, unique_ratio 0.02; pattern='<lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lc...'
- last 300 tokens:

```text
<lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
```

### Base cap 24: 농림축산식품부 농림축산검역본부_반려동물 보호복지 실태조사 8.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 273 x 21-token ngram, coverage 19.11, unique_ratio 0.02; pattern="'' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' ''"
- last 300 tokens:

```text
 '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' '' ''                                                                                                                                                                                        1                                                                                                                                                                                                                                                                                    
```

### Base cap 25: 농림축산식품부_농지 실거래가 동향 3.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 240 x 21-token ngram, coverage 16.80, unique_ratio 0.01; pattern='- - - - - - - - - - - - - - - - - - - - -'
- last 300 tokens:

```text
 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - - - -  - - -  - - - - - - - - - - - - - - - - - - - - - - - - -
```

### Base cap 26: 대전광역시_대전광역시 정신건강복지사업 기본계획 36.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 100 x 3 tokens, covers 300/300; pattern='100,'
- last 300 tokens:

```text
100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 
```

### Base cap 27: 법무부_이민정책연구자료 현황2 33.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 105 x 21-token ngram, coverage 7.35, unique_ratio 0.02; pattern='������������������������������������������������������������������������������������'
- last 300 tokens:

```text
㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧㸧�����������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������
```

### Base cap 28: 성평등가족부_청소년백서 33.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 27 x 4 tokens, covers 108/300; pattern='2014,'
- last 300 tokens:

```text
소노방, '정소노방, '정소노방, '정소노방, '정소노방방, '정소노방, '정소노방, '정소노방, '정소노방, '정소노방, '정소노방, '정소노방, '정소노방, '정소노방, '정소노방방. '정소노방, '정소방, '정소노방, '정소노방, '정소노방, '정, '정소노방, '정소노방, '정소노방, '방, '2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 2014, 
```

### Base cap 29: 송파구시설관리공단 채용 현황 6.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 275 x 21-token ngram, coverage 19.25, unique_ratio 0.01; pattern='<lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lc...'
- last 300 tokens:

```text
<lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel><lcel>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
```

### Base cap 30: 식품의약품안전처_기구 등의 살균소독제 정보 서비스 1.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern=',000'
- last 300 tokens:

```text
,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000,000
```

### Base cap 31: 중앙선거관리위원회_제20대 국회의원선거 투표율 분석 75.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 100 x 3 tokens, covers 300/300; pattern='의 1'
- last 300 tokens:

```text
의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1의 1
```

### Base cap 32: 한국교육과정평가원_학교 교육에서의 인공지능 및 에듀테크 활용 방안 탐색[2020 KICE 이슈페이퍼] 11.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern=', AI'
- last 300 tokens:

```text
, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI, AI
```

### Base cap 33: 한국데이터산업진흥원_데이터베이스 백서 147.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 31 x 13-token ngram, coverage 1.34, unique_ratio 0.02; pattern='�르 카르르 카르'
- last 300 tokens:

```text
�르르 카르르 카르르 카르르 카르르 카르르 카르 카르르 카르 카르르 카르 카르 카르 카르 카르르 카르르 카르 카르르 카르 카르르 카르르 카르르 카르르 카르 카 카르 카르 카르르 카르 카르 카르르 카르 카르르 카르르 카르 카르르 카르르 카르르 카르 카르르 카르르 카르르 카르르 카르르 카르르 카르르 카르르 카르 카르 카르 카르르 카르르 카르르르 카르르르 카르르 카達                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
```

### Base cap 34: 한국데이터산업진흥원_데이터베이스 백서 58.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 37 x 21-token ngram, coverage 2.59, unique_ratio 0.06; pattern='의 기업의 기업의 기업의 기업의 기업의'
- last 300 tokens:

```text
�단정보의 기업의 신용도파단정보의 기업의 신용도파단정보의 기업의 신용도파단정보의 기업의 신용도파단정보의 기업의 신용도파단정보의 기업의 기업의 신용도파단정보의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 신용도파단정보의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의 기업의  기업의                                                                                                                                                                                                                                                                                                                                                                      
```

### Base cap 35: 한국데이터산업진흥원_데이터산업 백서 15.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 19 x 21-token ngram, coverage 1.33, unique_ratio 0.03; pattern='지속반, 지속반, 지속반, 지속'
- last 300 tokens:

```text
 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속반, 지속, 지속반, 지속반, 지속반, 지속반, 지속, 지속반, 지속, 지속방, 지속, 지속, 지속, 지속, 지속, 지속, 지속, 지속반, 지속, 지속, 지속반, 지속, 지속, 지속, 지중, 지속, 지속, 지속, 지속, 지속, 지속, 지속, 지속, 지속, 지속, 지속, 지속, 지반, 지속, 지속, 지속, 지속, 지속, 지�
```

### Base cap 36: 한국데이터산업진흥원_데이터산업 백서 21.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='을 �'
- last 300 tokens:

```text
을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �을 �
```

### Base cap 37: 한국산업안전보건공단_작업환경실태조사 보고서4 115.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 265 x 21-token ngram, coverage 18.55, unique_ratio 0.02; pattern='<ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ec...'
- last 300 tokens:

```text
<ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><ecel><nl><ecel>
<nl>
<nl>
<nl>
<doctag>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
```

### Base cap 38: 한국소비자원_정책연구 보고서1 425.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 45 x 21-token ngram, coverage 3.15, unique_ratio 0.04; pattern='\ue820\ue820\ue820\ue820\ue820\ue820\ue820'
- last 300 tokens:

```text
������������������������������������ ��������������������������������������� �
�


















in








































































































```

### Base cap 39: 한국수자원공사_지하수조사연보 268.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 135 x 2 tokens, covers 270/300; pattern='>dl'
- last 300 tokens:

```text
>dl<dl>dl<dl><dl>dl<dl>dl<dl>dl>dl<dl>dl<dl><dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl>dl
```

### Base cap 40: 한국인터넷진흥원_대한민국 핀테크 기업 편람(국문) 38.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 100 x 3 tokens, covers 300/300; pattern='업기'
- last 300 tokens:

```text
업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기업기
```

### Base cap 41: 한국전력공사_전기요금표 2.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 105 x 2 tokens, covers 210/300; pattern='발'
- last 300 tokens:

```text
�발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발    
    ￼발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발발
```

### Base cap 42: 한국토지주택공사_3기신도시 사전청약 모집공고1 1.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 249 x 1 tokens, covers 249/300; pattern='</text>'
- last 300 tokens:

```text

<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text>
<doctag></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text>
```

### Base cap 43: 한국토지주택공사_3기신도시 사전청약 모집공고1 11.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 219 x 21-token ngram, coverage 15.33, unique_ratio 0.03; pattern='<nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl>'
- last 300 tokens:

```text
<nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><ecel><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><ecel><nl><nl><ecel><nl><nl><nl><nl><nl><ecel><nl><ecel><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl>                                                                                        
  
 
  
 
  
 
 
  201 201 201 201

```

### Base cap 44: 한국토지주택공사_3기신도시 사전청약 모집공고1 17.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 87 x 21-token ngram, coverage 6.09, unique_ratio 0.01; pattern='</text>467></text>467></text>467></text>467></text>467></text>467></text>467>'
- last 300 tokens:

```text
</text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>468></text>467></text>467></text>467></text>467></text>467></text>467></text>467></text>467>
```

### Base cap 45: 한국토지주택공사_3기신도시 사전청약 모집공고1 3.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 74 x 3 tokens, covers 222/300; pattern='. 1'
- last 300 tokens:

```text
 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1 호 제 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1
```

### Base cap 46: 한국토지주택공사_3기신도시 사전청약 모집공고1 4.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 64 x 21-token ngram, coverage 4.48, unique_ratio 0.04; pattern='취하기취하기취하기취하기취하기취하기취하기'
- last 300 tokens:

```text
취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기취하기�혹기�하기취하기취하기취하기취하기하기취하기취하기취하기취하기취하기중하기취하기취하기취하기하기취하기취하기취하취하기�곹하기취하기취하기취하기곷하기취하기곷하기취하기취하기�하기�
```

### Base cap 47: 한국토지주택공사_3기신도시 사전청약 모집공고2 20.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='1'
- last 300 tokens:

```text
1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 
```

### Base cap 48: 한국토지주택공사_3기신도시 사전청약 모집공고3 16.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 42 x 2 tokens, covers 84/300; pattern='</otsl><nl>'
- last 300 tokens:

```text
 �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �튤; �; �; �; �튤; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �; �<nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl>
```

### Base cap 49: 한국토지주택공사_3기신도시 사전청약 모집공고4 1.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 10 x 21-token ngram, coverage 0.70, unique_ratio 0.05; pattern='포,부포,부포,부포,부�'
- last 300 tokens:

```text
포,부포,부포,부포,부포,부포,부�,부포,부포,부포,부포,부포,부포,부포,부포,부포,부포,부포,부폏�,부포,부�,부�,부�,부�,부폏,부�ل,부�,부�,부�,부포�,부��,부�,부�∑,부�,부�,부�,부�,부�,부�,부�,부�.부�,부�,부�,부�,부�,부�∧,부�,부�∧,부�∧,부�,부�∅,부�∧,부�∨,부�,부�,부�,부∧,부∧,부�∧,부�,부∏∏,부�∫∧,부�∧,부∫∧,부∧,부∫∫,부∧,부∧,부∧,부�∧,부�∧
```

### Base cap 50: 한국토지주택공사_3기신도시 사전청약 모집공고4 5.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 67 x 2 tokens, covers 134/300; pattern='</otsl><nl>'
- last 300 tokens:

```text
�� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� �� � �� �� �� �� � � �� �� � � �� � � � �� � � � � � � � � � � � �� � � � � �� � � � � � � �� � � �� � � � � �� � �� � � �� � �� � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � � �� � � � � �<nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl>
```

### Base cap 51: 한국토지주택공사_마이홈포털 공공분양주택 입주자모집공고2 11.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 150 x 2 tokens, covers 300/300; pattern='\uffef'
- last 300 tokens:

```text
￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯￯
```

### Base cap 52: 한국토지주택공사_마이홈포털 공공분양주택 입주자모집공고2 5.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 75 x 4 tokens, covers 300/300; pattern='1000,'
- last 300 tokens:

```text
1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 
```

### Base cap 53: 한국토지주택공사_마이홈포털 공공분양주택 입주자모집공고2 6.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 75 x 4 tokens, covers 300/300; pattern='기준,'
- last 300 tokens:

```text
 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준, 기준,
```

### Base cap 54: 한국토지주택공사_마이홈포털 공공분양주택 입주자모집공고3 2.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 109 x 21-token ngram, coverage 7.63, unique_ratio 0.01; pattern='<nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl>'
- last 300 tokens:

```text
</otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl><nl></otsl><nl><nl></otsl><nl><nl></otsl><nl><nl><nl><nl></otsl><nl><nl><nl></otsl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl></otsl><nl></otsl><nl></otsl><nl></otsl><nl><nl></otsl><nl></otsl><nl><nl></otsl><nl><nl></otsl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl><nl>                          <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl><nl> <nl> <nl> <nl> <nl> <nl><nl> 
```

### Base cap 55: 한국토지주택공사_마이홈포털 공공분양주택 입주자모집공고3 31.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 55 x 21-token ngram, coverage 3.85, unique_ratio 0.03; pattern='다가 랜다가 랜다가 랜다가 랜다'
- last 300 tokens:

```text
다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 랜다가 �جم                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
```

### Base cap 56: 한국토지주택공사_마이홈포털 공공분양주택 입주자모집공고3 4.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 37 x 3 tokens, covers 111/300; pattern='공.'
- last 300 tokens:

```text
사항 1. 공고사항 1. 공고사항 1. 공고사항 1. 공고사. 공고사. 공고사항 1. 공고사항. 공고. 공. 공고사. 공. 공고. 공고. 공고사. 공고. 공고. 공고사. 공. 공고사. 공고사. 공. 공고사. 공고. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공고. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공. 공.
```

### Base cap 57: 한국토지주택공사_입찰계약 정보 1.pdf
- category: Notices
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 15 x 5-token ngram, coverage 0.25, unique_ratio 0.08; pattern='구성과구성'
- last 300 tokens:

```text
자학) 의 적용 �구성(자학) 의 적용 �구성(자학) 의 적용 �구성(자학) 의 적용 �구성(자학) 의 적용 �구성(자학)구성(자학)구성(자학구성(자학구성과구성(자학구성과구성(자학구성과구성구성과구성)구성(자학구성과구성과구성과구성(자학구성과구성과구성구성과구성과구성과구성과구성과구성과구성과구혹곀구성과구혹구중구혹구기구준구혹구준구혹구준구혹구준구혹구혝구준구혝구준구혹구준구혹구중구혝구혝구혝구중구혹구준구혝구�상과핸과구준구준협혝구중혹구준구준구혹구준구혹구준혹구준
```

### Base cap 58: 한국토지주택공사_지속가능경영보고서 44.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 114 x 1 tokens, covers 114/300; pattern='����'
- last 300 tokens:

```text
알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알알������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������������
```

### Base cap 59: 한국토지주택공사_토지주택연구원 연구보고서2 207.pdf
- category: Reports
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 62 x 21-token ngram, coverage 4.34, unique_ratio 0.01; pattern='500,500,500,500,500,500,500,500,500,500,500'
- last 300 tokens:

```text
500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,500,100,100,100,100,100,100,100,100,100,100,100,500,100,500,100,500,100,100,100,500,500,100,200,200,200,100,200,100,200,100,100,200,100,200,100,100,100,100,100,100,200,200,100,100,200,100,100,100,100,100,100,100,100,500,100,100,500,100,500,100,200,100,500,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,
```

### Base cap 60: 한국토지주택공사_현상설계공모 추진현황 2.pdf
- category: Statistics
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 300 x 1 tokens, covers 300/300; pattern='</text>'
- last 300 tokens:

```text
</text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text></text>
```

### Base cap 61: 한국환경공단_공공환경시설 기술진단안내 6.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 52 x 5-token ngram, coverage 0.87, unique_ratio 0.02; pattern='합화합'
- last 300 tokens:

```text
화처화합화합처화합처화합합처화합화합처화화합처화합화합철화합철화합합처화합합처화합화합합화합합화합합화합화합화합합화합합화합합합화합합합합합합합화합합합합화합화합화합화합화합화합화합합화합합합합화합화합화합합화합합합화합화합합화합화합화합화합화합화합화합화합화합화합합화합화합합화합화합합화합합합화합화합합화합화합합화합화합합합합합화합합합합합합화합합합화합화합합
```

### Base cap 62: 해양수산부_항만기술기준1 299.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: n-gram loop: 53 x 21-token ngram, coverage 3.71, unique_ratio 0.03; pattern='以�以�以�以�以�以�以�以�以�以�以'
- last 300 tokens:

```text
以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以以�以以�以�以�以�以�以�以以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以以�以�以�以�以�以�以�以�以�以�以�以�以以�以以�以以�以以�以以�以以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以�以以以�以以�以以�以�以�以�以�以以�以�以�以�以�以�以�以�以�以�以以�以�以�以以�以�以�以以�以�以�以以�以以以以以以�以�以�以�以 �以 � � 








in


in
in
```

### Base cap 63: 행정안전부_자전거 이용 시설 관리 지침 39.pdf
- category: Manuals
- generated_tokens: 8192
- class: REPETITION
- evidence: suffix loop: 16 x 4 tokens, covers 64/300; pattern='. 2014'
- last 300 tokens:

```text
￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿ ￿  ￿ ￿ ￿ ￿ ￿  ￿ ￿ ￿  ￿ ￿  ￿  ￿ ￿  ￿  ￿   ￿    ￿ ￿    ￿      ￿     ￿   ￿       ￿           ￿        ￿       ￿                 ￿                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
 
 
 
  2019. 2019. 2017. 2019. 2019. 2019 years ago. 2019. 2019. 2013. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014. 2014
```

## Parse-exception details: overfit_26 run
Docling-core exceptions did not include a source offset, so an exact failure point is not identifiable from saved metadata. For each exception, this report shows the final 200 decoded model tokens as the nearest raw context. Rows marked `terminated=true` failed after normal EOS termination, so these are malformed/unsupported DocTags rather than cap truncation.
Exception overlap with cap: 2/27. Normally terminated exceptions: 25/27.

### Overfit exception 1: (제1유형)_방송미디어통신위원회_연차보고서(국문) 31.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 7276
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate><locate</text>
<text><loc_261><locate></text>
<text><loc_265><locate></text>
<text><loc_265><locate></text></doctag><|end_of_text|>
```

### Overfit exception 2: (제1유형)_식품의약품안전처_축산물의 표시기준2 47.pdf
- category: Manuals
- exception: `IndexError('list index out of range')`
- generated_tokens: 1520
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
</text>
<text><loc_71><loc_456><loc_71><loc_456>10</text>
<text><loc_71><loc_456><loc_71><loc_456>조</text>
<text><loc_75><loc_456><loc_101><loc_464>따라</text>
<text><loc_206><loc_456><loc_212><loc_466>이</text>
<text><loc_101><loc_457><loc_206><loc_464>식토의알텍전천장이 정한</text>
<text><loc_62><loc_457><loc_101><loc_464>법 식후의</text>
<text><loc_236><loc_485><loc_263><loc_492>- 47 -</text>
<text><loc_402><loc_466><loc_483><loc_474>따른다.</text></doctag><|end_of_text|>
```

### Overfit exception 3: (제1유형, 대량) 경기도_재난안전 매뉴얼_1 19.pdf
- category: Manuals
- exception: `IndexError('list index out of range')`
- generated_tokens: 2137
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
<ucel><ecel><ecel><ecel><ecel><nl><fcel>3,200<fcel>2,604.5<ucel><ecel><ecel><ecel><ecel><nl><fcel>0<fcel>0<ucel><ecel><ecel><ecel><ecel><nl><fcel>5,940<fcel>1,604.6<ucel><ecel><ecel><ecel><ecel><nl><fcel>12<fcel>12<ucel><ecel><ecel><ecel><ecel><nl><fcel>12,772<fcel>2,704.4<ucel><ecel><ecel><ecel><ecel><nl><fcel>2,700<fcel>1<ucel><ecel><ecel><ecel><ecel><nl><fcel>1,650<fcel>1<ucel><ecel><ecel><ecel><ecel><nl><fcel>16,790<fcel>3,277<ucel><ecel><ecel><ecel><ecel><nl><fcel>3,200<fcel>4<ucel><ecel><ecel><ecel><ecel><nl><fcel>0<fcel>0<ucel><ecel><ecel><ecel><ecel><nl><fcel>90,592<fcel>4<ucel><ecel><ecel><ecel><ecel><nl></otsl>
<text><loc_373><loc_etail><loc_ oneal 3.274</text>
<text><loc_123><loc_468><loc_127><loc_478>34</text>
<text><loc_melody.</text>
</doctag><|end_of_text|>
```

### Overfit exception 4: [대량] 행정안전부_지방재정365_통합재정개요 22.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 3189
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
수</text>
<text><loc_132><loc_429><loc_152><loc_436>송수한</text>
<text><loc_58><loc_429><loc_110><loc_437>(보전거래는</text>
<text><loc_360><loc_429><loc_365><loc_432>:</text>
<text><loc_203><loc_439><loc_355><loc_446>통합재정수지에 미포학되며,</text>
<text><loc_366><loc_439><loc_396><loc_446>적자분을</text>
<text><loc_400><loc_439><loc_412><loc_446>보전</text>
<text><loc_47><loc_440><loc_55><loc_447>)</text>
<text><loc_112><loc_440><loc_118><loc_443>:</text></doctag><|end_of_text|>
```

### Overfit exception 5: [제1유형] 외교부_이란 개황 정보 108.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 974
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
_141><loc_71><loc_147><loc_79>:</text>
<text><loc_230><loc_73><loc_237><loc_79>)</text>
<text><loc_339><loc_71><loc_351><loc_78>(</text>
<text><loc_351><loc_71><loc_371><loc_79>전단리),</text>
<text><loc_396><loc_71><loc_433><loc_78>무얱협회</text>
<text><loc_180><loc_73><loc_190><loc_79>2013</text>
<text><loc_190><loc_73><loc_198><loc_79>년</text>
<text><loc_384><loc_73><loc_403><loc_79>행처</text>
<text><loc_80><loc_483><loc_120><loc_491>108·</text></doctag><|end_of_text|>
```

### Overfit exception 6: [제1유형] 질병관리청_지역건강통계_2 109.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 8192
- terminated: False
- capped: True
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
공,공,공,곡,공,곡,공,공,공,공,공,곀,곡,공,공,공,공,공,공,공,곡,공,결,공,곡,결,곺,결,곀,곺,결,곽,곽,곽,곡,공,곡,결,곡,결,결,유결,결,결,결,곡,공,곡,결,곡,결,곡,곡,결,곡,결,곡,결,곡,곀,곡,곡,�,공,개,곴,득,곡,공,공,곡,동,곡,결,결,결,공,결,곡,곡,결,결,결
```

### Overfit exception 7: 교육부_평생교육기관 개황정보_7 1.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 1401
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
 및</text>
<text><loc_28><loc_436><loc_40><loc_441>)는</text>
<text><loc_229><loc_436><loc_240><loc_442>요청</text>
<text><loc_25><loc_442><loc_55><loc_449>3)</text>
<text><loc_55><loc_442><loc_56><loc_445>)</text>
<text><loc_69><loc_442><loc_80><loc_448>교료</text>
<text><loc_96><loc_442><loc_185><loc_449>완성년에 허하며 또한</text>
<text><loc_190><loc_442><loc_232><loc_449>편계이,</text>
<text><loc_38><loc_465><loc_61><loc_472>14 14</text></doctag><|end_of_text|>
```

### Overfit exception 8: 국토교통부_리츠정보_영업보고서4 5.pdf
- category: Notices
- exception: `IndexError('list index out of range')`
- generated_tokens: 1058
- terminated: True
- capped: False
- grammar class: OTSL grid violation
- 200-token context (failure offset not reported; tail shown):

```text
무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임 @제무제훈게임<fcel>02-563-0343<nl></otsl>
</doctag><|end_of_text|>
```

### Overfit exception 9: 국토교통부_리츠정보_영업보고서4 8.pdf
- category: Notices
- exception: `IndexError('list index out of range')`
- generated_tokens: 1303
- terminated: True
- capped: False
- grammar class: OTSL grid violation
- 200-token context (failure offset not reported; tail shown):

```text
30.면<fcel>소게게리<fcel>224,141,304<fcel>245,607,896<fcel>245,607,896<nl><fcel>31.면<fcel>지게게리<fcel>1,290,776,018<fcel>1,011,680,944<fcel>1,011,680,944<nl><fcel>32.면<fcel>매게게리<fcel>157,184,000<fcel>183,745,052<ecel><nl><fcel>33.면<fcel>대게게리<fcel>110,441,319<fcel>217,889,966<fcel>83,745,052<nl><fcel>34.면<fcel>건게게리<fcel>419,470,305<fcel>335,697,239<fcel>419,470,305<nl><fcel>35.면<fcel>무협게게리<fcel>26,998,785<fcel>18,074,761<fcel>26,998,785<nl></otsl>
<text><loc_192><loc_428><loc_309><loc_443>장장장장</text></doctag><|end_of_text|>
```

### Overfit exception 10: 국토교통부_주택업무편람 정보 48.pdf
- category: Manuals
- exception: `IndexError('list index out of range')`
- generated_tokens: 2907
- terminated: True
- capped: False
- grammar class: unclosed/mismatched tag
- 200-token context (failure offset not reported; tail shown):

```text
<ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><ecel><ucel><ecel><ucel><nl><ecel><nl>
 <nl>
</otsl> <nl> <nl> <nl> <nl> <nl> <nl> <nl> <nl><nl></otsl><nl></otsl><|end_of_text|>
```

### Overfit exception 11: 국토교통부_주택업무편람 정보 82.pdf
- category: Manuals
- exception: `IndexError('list index out of range')`
- generated_tokens: 1010
- terminated: True
- capped: False
- grammar class: OTSL grid violation
- 200-token context (failure offset not reported; tail shown):

```text
��시(형경중실복합도시건설에정지역)<lcel><fcel>'17.8.3<fcel>'22.9.26<fcel>'22.9.26<nl></otsl>
<text><loc_66><loc_445><loc_110><loc_453>2025년</text>
<text><loc_115><loc_445><loc_143><loc_453>10월</text>
<text><loc_146><loc_445><loc_170><loc_453>기준</text>
<text><loc_173><loc_445><loc_203><loc_453>종 37개의</text>
<text><loc_206><loc_445><loc_261><loc_453>투기과업지구</text>
<text><loc_264><loc_445><loc_284><loc_453>지정</text></doctag><|end_of_text|>
```

### Overfit exception 12: 농림축산식품부 농림축산검역본부_가축질병 병성감정 현황 46.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 925
- terminated: True
- capped: False
- grammar class: OTSL grid violation
- 200-token context (failure offset not reported; tail shown):

```text
<fcel>102<fcel>100<fcel>28<fcel>4,160<fcel>322<fcel>33.2<nl><fcel>제주<fcel>2,790<fcel>1,000<fcel>3,790<fcel>926<fcel>1,890<fcel>800<fcel>282<fcel>28<fcel>1,726<fcel>2,530<fcel>40.6<nl><fcel>함계<fcel>59,760<fcel>32,340<fcel>92,100<fcel>18,411<fcel>20,825<fcel>13,914<fcel>8,191<fcel>3,699<fcel>32,325<fcel>29,016<fcel>52.7<nl></otsl>
<otsl><loc_34><loc_398><loc_318><loc_441><fcel>끝가<fcel>끝영<nl><fcel>감사수<fcel>양성수 0<nl><fcel>양성수<fcel>감사때수<nl><fcel>4,128<fcel>61,341  0<nl></otsl>
<page_footer><loc_240><loc_467><loc_242><loc_476>-</page_footer>
</doctag><|end_of_text|>
```

### Overfit exception 13: 대전광역시_건설공사 품질시험 수수료 11.pdf
- category: Manuals
- exception: `IndexError('list index out of range')`
- generated_tokens: 3690
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
<text><loc_63><loc_432><loc_66><loc_439>업</text>
<text><loc_223><loc_432><loc_333><loc_439>KS M 150 844</text>
<text><loc_223><loc_441><loc_330><loc_448>KS M 150 844</text>
<text><loc_298><loc_441><loc_298><loc_441>1</text>
<text><loc_298><loc_441><loc_298><loc_441>0</text>
<text><loc_298><loc_441><loc_298><loc_441>6</text>
<text><loc_63><loc_441><loc_66><loc_447>사</text>
<text><loc_ FormControl: 텍스트: 알축강도</text><text><loc_396><loc_441><loc_396><loc_441>16,000</text></doctag><|end_of_text|>
```

### Overfit exception 14: 대전광역시_대전광역시 정신건강복지사업 기본계획 3.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 8192
- terminated: False
- capped: True
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
<fcel>201<nl>orange<nl>anke<nl>anke<nl>Single<nl>us.<nl>本<nl>사<nl>조<nl>조.<nl> succesfully<nl>조.<nl>조<nl>사<nl>사<nl>연<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사.<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사.<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사<nl>사
```

### Overfit exception 15: 대전광역시_독거노인등록통계 108.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 2166
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
_212>)</text>
<text><loc_226><loc_212><loc_271><loc_220>직게되어</text>
<text><loc_273><loc_212><loc_332><loc_220>한계(중부</text>
<text><loc_132><loc_212><loc_140><loc_219>)</text>
<text><loc_271><loc_212><loc_330><loc_220>제거된</text>
<text><loc_142><loc_211><loc_226><loc_219>가지고 않게 중복</text>
<text><loc_332><loc_211><loc_364><loc_220>수치)가</text>
<text><loc_399><loc_239><loc_pielomb:in|청원)</text>
<text><loc_334><loc_240><loc_399><loc_247>청원)</text>
</doctag><|end_of_text|>
```

### Overfit exception 16: 대전광역시_빛공해 환경영향평가 169.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 1365
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
402>축정관장</text>
<text><loc_156><loc_395><loc_188><loc_402>발생건수</text>
<text><loc_80><loc_405><loc_98><loc_413>이하</text>
<text><loc_100><loc_405><loc_125><loc_413>같음</text>
<text><loc_189><loc_417><loc_190><loc_419>﻿</text>
<text><loc_287><loc_26><loc_305><loc_33>발생</text>
<text><loc_308><loc_26><loc_370><loc_33>현행 분석주거지</text>
<text><loc_74><loc_500><loc_95><loc_499>137</text>
<text><loc_344><loc_500><loc_374><loc_499>×100</text></doctag><|end_of_text|>
```

### Overfit exception 17: 부산도시공사_영구임대주택 모집 안내 1.pdf
- category: Notices
- exception: `IndexError('list index out of range')`
- generated_tokens: 1726
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
<loc_223><loc_366><loc_253><loc_374>복지설</text>
<text><loc_255><loc_366><loc_270><loc_373>세</text>
<text><loc_itereade.</text>
<text><loc_47><loc_366><loc_70><loc_374>4.</text>
<text><loc_70><loc_366><loc_93><loc_374>신청장</text>
<text><loc_95><loc_366><loc_126><loc_374>소 ：</text>
<text><loc_222><loc_388><loc_250><loc_396>- 1306</text>
<text><loc_222><loc_388><loc_223><loc_389>)</text>
<text><loc_126><loc_400><loc_alous>locally.사업처(주거복지사업부) :</text></doctag><|end_of_text|>
```

### Overfit exception 18: 성평등가족부_청소년백서 33.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 6839
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent) · 1-3-4(Parent)</text>
<text><loc_270><loc_70><loc_override><loc_76>(경 Sunderland·
</doctag><|end_of_text|>
```

### Overfit exception 19: 인사혁신처_국가공무원인재개발원 교육운영계획 10.pdf
- category: Manuals
- exception: `IndexError('list index out of range')`
- generated_tokens: 1739
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
�시판원 우측시판원<fcel>2장 2장 25외 25외 2청 250원<fcel>2성 2성 250원 4성 100원<fcel>40명<fcel>9.11-12<fcel>11.16-17.<ecel>.12.3-4.<nl><fcel>5장 5조게 공게 광호원<fcel>2장 2장 25외 4성<fcel>10외 100명<fcel>7장 7장<fcel>3.19-20.<fcel>4,6-7.<fcel>4,6-7.<nl></otsl>
<page_footer><loc_370><loc_469><loc_.{014}</page_footer>
<text><loc_29><loc_468><loc_33><loc_475>016</text>
<text><loc_484><loc_468><loc_493><loc_476>017</text></doctag><|end_of_text|>
```

### Overfit exception 20: 한국가스안전공사_가스사고연감 164.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 1066
- terminated: True
- capped: False
- grammar class: OTSL grid violation
- 200-token context (failure offset not reported; tail shown):

```text
<fcel>10<fcel>30.0<fcel>2<nl><fcel>사용자 취급부주의<fcel>안 람 조 정 연부및 오 개 방<fcel>2<fcel>41.7<fcel>4100.0<nl><ecel>보 베<fcel>수 리 작 업 실<fcel>5<fcel>41.7<fcel>5<nl><fcel>공급자 부주의<fcel>시 공 농 람<fcel>5<fcel>41.7<fcel>5<nl><ucel><fcel>안 전첨미 실<fcel>2<fcel>16.6<fcel>5.2<nl><fcel>소 게<lcel><fcel>12<fcel>100.0<fcel>4100.0<nl><fcel>기타사고<fcel>기타 사 고<fcel>11<fcel>100.0<fcel>5<nl><ecel>촌게<fcel>363<fcel>100.0<ecel><fcel>5<nl><fcel>164<lcel><ecel><ecel><ecel><nl></otsl>
<text><loc_116><loc_476><loc_126><loc_483>164</text></doctag><|end_of_text|>
```

### Overfit exception 21: 한국데이터산업진흥원_데이터베이스 백서 29.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 3320
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
1.8%</text>
<text><loc_320><loc_390><loc_371><loc_397>로그그cellent을차지하였다.</text>
<text><loc_28><loc_400><loc_35><loc_407>)</text>
<text><loc_70><loc_400><loc_94><loc_407>1993.3.</text>
<text><loc_225><loc_400><loc_265><loc_407>23.0 해소와</text>
<text><loc_264><loc_400><loc_275><loc_407>23.</text>
<text><loc_261><loc_400><loc_271><loc_407>27.</text>
<text><loc_294><loc_400><loc_315><loc_407>21.3</text>
<text><loc_475><loc_266><loc_495><loc_275>27.1</text></doctag><|end_of_text|>
```

### Overfit exception 22: 한국전력거래소_발전소 건설사업 추진현황 42.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 2283
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
추진일정<fcel>부발전시설<ecel><nl><fcel>온한 1974 2019 06 27<fcel>조사 완료<fcel>21.09 21.10<fcel>472<nl><fcel>건설기본계획 홨정 초설<fcel>확인<ecel><ucel><nl><ucel><fcel>촉건<fcel>'21. 10<ucel><nl><fcel>촉건설계획없액 제결<fcel>제결<fcel>'22. 04<ucel><nl><fcel>주기기공급안 체결<fcel>체결<fcel>'24. 07<ucel><nl><fcel>추설비공사않 체결<fcel>제결<fcel>'24. 07<ucel><nl><fcel>촉공 준공<fcel>제결<fcel>('25. 06)<nl><ucel><fcel>'27. 12<fcel>'27. 12)<nl></otsl></doctag><|end_of_text|>
```

### Overfit exception 23: 한국토지주택공사_사업실명제 사업리스트1 1.pdf
- category: Notices
- exception: `IndexError('list index out of range')`
- generated_tokens: 1919
- terminated: True
- capped: False
- grammar class: OTSL grid violation
- 200-token context (failure offset not reported; tail shown):

```text
벽지구<fcel>2긴<fcel>25.01<nl><fcel>-2018.07.02.<fcel>제안<lcel><ecel><ecel><nl><fcel>-2018.12.29.<fcel>시계획위원회<lcel><ecel><ecel><nl><fcel>-2019.11.19.<fcel>공공주벽통한산의위원회 석의<lcel><ecel><ecel><nl><fcel>-2019.12.20.<fcel>지구제행 송인 고시<ecel><ecel><ecel><nl><fcel>-2021.01.19.<fcel>조공此<ecel><ecel><ecel><nl><ecel><fcel>2023.07.1.<ecel><ecel><ecel><nl><fcel>-2022.12.06.<fcel>지구제행변경(1차) 손인 고시<fcel>수men,주거부지구<fcel>2긴<fcel>담당부 농간 인 관련 자.<nl></otsl>
</doctag><|end_of_text|>
```

### Overfit exception 24: 한국환경산업기술원_환경신기술 요약집 42.pdf
- category: Reports
- exception: `IndexError('list index out of range')`
- generated_tokens: 1988
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
8045-2591 Homepage : www.anyang.go.kr<fcel>e-mail 해치지단게 235 31-8045-2591<fcel>안양시 시설구분 처리시설 처리리대에로<fcel>지방치단체 235 패략: 031-8045-5500<fcel>기술<nl><ucel><ucel><ucel><ucel><ucel><ucel><nl><fcel>(사무실)<lcel><lcel><lcel><lcel><ucel>.<nl><ucel><fcel>수송 및 전후<fcel>작리조 개업<lcel><ucel>.<nl><ucel><fcel>(사무실)<fcel>31-8045-2591<fcel>이름 : 10 행eve<ucel>.<nl><ucel><ucel><fcel>15:00-17:30<fcel>e-mail<fcel>담당자<nl></otsl>
<text><loc_323><loc_483><loc_330><loc_489>1</text></doctag><|end_of_text|>
```

### Overfit exception 25: 행정안전부_지방세통계연감 52.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 2142
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
-<fcel>-<fcel>-<fcel>-<nl></otsl>
<text><loc_147><loc_393><loc_167><loc_400>여존</text>
<text><loc_159><loc_393><loc_190><loc_400>재끝이</text>
<text><loc_193><loc_393><loc_225><loc_400>수1.0%</text>
<text><loc_130><loc_393><loc_151><loc_400>안 성</text>
<text><loc_57><loc_413><loc_seg8>locs 14</text>
<text><loc_230><loc_413><loc_257><loc_420>화원권</text>
<text><loc_43><loc_413><loc_61><loc_422>제방세</text>
<text><loc_61><loc_413><loc_98><loc_420>개요.</text></doctag><|end_of_text|>
```

### Overfit exception 26: 행정안전부_지방자치단체 공무원 인사통계 27.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 1032
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
 1,274<fcel>924<nl><fcel>합공<fcel>1<ecel><ecel><ecel><fcel>1<fcel>4<nl><fcel>사실 및접 인д설<fcel>38,450<ucel><fcel>1<fcel>1<fcel>5,662<fcel>5,662<nl><fcel>반책 인설<fcel>870<ucel><fcel>8<fcel>11,420,10,657<fcel>7,555 252<fcel>2<nl><fcel>법손 협의<fcel>2,779<ucel><fcel>154<fcel>289<fcel>300<fcel>252<nl><fcel>위생<fcel>2,779<ucel><fcel>843<fcel>897<fcel>547<fcel>338<nl><fcel>조리 관원<fcel>274<ucel><fcel>109<fcel>155<fcel>7<fcel>3<nl><fcel>시설 광원<fcel>3<ucel><ecel><ecel><fcel>3<fcel>3<nl><ecel>7,270<ucel><fcel>2<fcel>174<fcel>368 1,196<fcel>493<fcel>4<nl></otsl>
<text><loc_243><loc_449><loc_255><loc_457>21</text></doctag><|end_of_text|>
```

### Overfit exception 27: 행정안전부_지방재정365_지방세외수입통계연감 51.pdf
- category: Statistics
- exception: `IndexError('list index out of range')`
- generated_tokens: 3847
- terminated: True
- capped: False
- grammar class: bad loc token
- 200-token context (failure offset not reported; tail shown):

```text
>제2장 석수안원</text>
<text><loc_162><loc_457><loc_ migli.</text>
<text><loc_162><loc_457><loc_266><loc_464>세의수안원) 진수현황(축합)</text>
<otsl><loc_119><loc_361><loc_170><loc_385><fcel>진수안<lcel><fcel>6,239,192<nl><fcel>(A)<fcel>제 3.<fcel>(CBD)<nl><ucel><fcel>(C)<fcel>4-1-2.<nl></otsl>
<text><loc_192><loc_482><loc_211><loc_489>3.</text>
<text><loc_117><loc_483><loc_ies>loc.gov.er.edu 태체법</text>
<text><loc_461><loc_462><loc_484><loc_469>37</text></doctag><|end_of_text|>
```

## Base parse-exception confirmation
- `run_progress.jsonl` rows: 849
- rows with `parse_valid=false`: 0
- base `errors.jsonl` exists: False
- Conclusion: base had 0 parse exceptions in raw saved metadata.

## Recommendations only
- Do not raise `max_new_tokens` as the primary response to these cap hits; the cap hits are loops. Keep 8192 for resource safety and comparability unless a new run shows progressing capped pages.
- Add loop-oriented evaluation metrics in future runs: repeated suffix pattern, repeated n-gram coverage, low-diversity tail score, and cap-hit category breakdown.
- For targeted data selection, prioritize the named page types above, especially LH/public-housing recruitment notices and regulatory/policy guide pages where the base model repeatedly degenerates.
- For overfit parse robustness, focus on malformed `<loc_...>` emissions and OTSL/grid consistency; most exceptions are not caused by cap truncation.
- No fixes were applied in this task.
