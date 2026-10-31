# Writing study metadata — B portion

- Base: `15482fa8babcbe48a6ac868f6324e8db536caa8e`
- Branch: `codex/writing-study-b`
- Explicit coordinator-assigned range: `H31110-72` through `H31332-75` (49 reorder questions, 49 official answers).
- Entries: 210 vocabulary records, 3–6 per question. Character-fill questions are excluded.
- Format: version 1; `items` is keyed by question ID; `answerIndex` uses the official answer order.

Sentence `words` retain every original character, including punctuation and Arabic numerals. Punctuation has empty pinyin. Numeric readings include `18 → shíbā`, `107 → yìbǎi líng qī`, `10 → shí`, and `一万 → yíwàn`. Sentence pinyin applies contextual 一/不 tone changes, while ordinary third-tone combinations retain dictionary third-tone spelling. 的/地/得 and aspect 着/了 are neutral; 长 is `zhǎng` in 长得 and `cháng` for length; 教 is `jiāo` for teaching. Vocabulary entries use the word sense and part of speech in the sentence.

Manual checks completed: sentence meanings, number readings, polyphonic characters, neutral particles, vocabulary units, and contextual Korean glosses. No known unresolved source-answer issue in this portion. This does not change official answers or grammar data.

Validation: `python3 tools/writing/study-parts/validate_b.py`; checks exact coverage, answer indices, official sentence reconstruction, pinyin presence, punctuation, vocabulary fields, duplicate words, vocabulary counts and occurrence in official answers. It does not independently prove pronunciation or translation accuracy; those were manually reviewed.

## Assigned IDs

- `H31110-72`
- `H31110-73`
- `H31110-74`
- `H31110-75`
- `H31111-71`
- `H31111-72`
- `H31111-73`
- `H31111-74`
- `H31111-75`
- `H31218-71`
- `H31218-72`
- `H31218-73`
- `H31218-74`
- `H31218-75`
- `H31219-71`
- `H31219-72`
- `H31219-73`
- `H31219-74`
- `H31219-75`
- `H31220-71`
- `H31220-72`
- `H31220-73`
- `H31220-74`
- `H31220-75`
- `H31221-71`
- `H31221-72`
- `H31221-73`
- `H31221-74`
- `H31221-75`
- `H31328-71`
- `H31328-72`
- `H31328-73`
- `H31328-74`
- `H31328-75`
- `H31329-71`
- `H31329-72`
- `H31329-73`
- `H31329-74`
- `H31329-75`
- `H31330-71`
- `H31330-72`
- `H31330-73`
- `H31330-74`
- `H31330-75`
- `H31332-71`
- `H31332-72`
- `H31332-73`
- `H31332-74`
- `H31332-75`
