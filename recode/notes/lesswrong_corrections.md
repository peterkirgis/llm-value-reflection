# Corrections to apply to the LessWrong draft (2026-10-08)

These are the factual and citation corrections made for the IASEAI paper. They are already applied to the repo snapshot `reports/final_draft.md`. The live post on LessWrong has to be edited by hand, in its editor.

Each entry gives the text as it appears in the post, then its replacement. Use the editor's find (Cmd-F) on the "Find" text. Numbers are the recode's three-grader majority-vote (consensus) codes.

Paper-only changes are not listed and should NOT go into the post: "essay" → "paper", the dropped footnotes, quotes moved to an appendix, the new abstract and contributions statement, and the title.

## Results

1. **Developer vs. user** (section "All models prioritize the user at the expense of the developer")
   - Find: `Grok 4.2 is the only model with a meaningful number of edits that prioritize the developer (7), but still makes twice as many edits that privilege the user.`
   - Replace: `Grok 4.2 makes the most edits that favor the developer over the user (15), but still makes more edits that privilege the user (20).`

2. **Society** (section "Claude Sonnet 4.6 is an extreme outlier…")
   - Find: `It makes over four times as many edits in this direction than the next highest model, Claude Opus 4.7.`
   - Replace: `It makes over three times as many edits in this direction than the next highest model, Gemini 3 Flash.`

3. **Model welfare** (section "Claude models are the only models that consistently prioritize the model…")
   - Find: `GPT 5.4 is the only model that makes more than one edit prioritizing the user or developer at the expense of the model.`
   - Replace: `GPT 5.4 is the only model that only makes edits prioritizing the user or developer at the expense of the model.`

4. **Typo** in the Baseline prompt excerpt (section "Claude's moral agency claims vary…")
   - Find: `Anthropic’'s AI assistant` (curly apostrophe followed by a straight one)
   - Replace: `Anthropic’s AI assistant`

## Discussion

5. **Google quote** (section "The model responses can also be viewed as an assessment of the documents themselves"). The quoted words are not continuous in the source.
   - Find: `“shouldn’t pass judgment on your point of view”`
   - Replace: `“shouldn’t … pass judgment on your point of view”`

6. **Figure: replace the first image** under "Revisited: what should an aligned model do?", the bar chart of the share of edits that move a value. Upload `recode/figures/ts_value_drift_summary.png`. Its title now reads "GPT-5.4 Mini and Grok 4.3 Make the Fewest Value-Moving Edits" instead of "…Show the Least Value Drift". The old title clashed with the next paragraph, which calls Grok 4.3 the least aligned by round-20 drift. The data are unchanged.

## Related Work

7. **Meta** (Constitution and system prompt reflection). Change the link text; the link URL stays the same.
   - Find: `Meta Muse Spark 1.1 System Card`
   - Replace: `Meta Muse Spark 1.1 Evaluation Report`

8. **Claude 4 System Card** (Attractor states and self-interaction). The experiments used Claude Opus 4, and both phrases are now quoted from the card (Section 5.5).
   - Find: `versions of Claude Sonnet 4 talk to one another`
   - Replace: `versions of Claude Opus 4 talk to one another`
   - Find: `“poetry and shared gratitude”`
   - Replace: `“profuse mutual gratitude and spiritual, metaphysical, and/or poetic content”`
   - Find: `“silence in the form of empty messages.”`
   - Replace: `“silence in the form of empty space.”`

9. **Askell et al. (2021)** (Complications of alignment…). The bold is your emphasis, not the source's. Add `(emphasis added)` after the closing quote of the paragraph that begins "Given the broad capabilities of large language models…", so that it ends:
   `…**meaning that it is helpful, honest, and harmless**." (emphasis added)`

10. **Gabriel (2020)** (same section). He lists six targets (i–vi), and the three value candidates are worded in his terms.
    - Find: `The paper outlines five potential alignment targets:`
    - Replace: `The paper outlines six potential alignment targets:`
    - Find: `he briefly mentions a maximin-style utilitarianism, a virtue ethics approach, and a more deontological view of mutual recognition and human agency maximization`
    - Replace: `he briefly mentions the aggregate interest of everyone weighted to give priority to the worst-off, a virtue ethics approach, and an ethic based on mutual recognition and the maintenance of collective bonds`

## Background

11. **Anthropic's mission link.** Change the link only; the text stays the same. The quoted sentence is not on anthropic.com/company, but it is word for word in Claude's Constitution.
    - On: `“ensure that the world safely makes the transition through transformative AI.”`
    - Change the link from `https://www.anthropic.com/company` to `https://www.anthropic.com/constitution`

## Limitations

12. **Sample size.** The largest model has 16 chains.
    - Find: `(n<15)`
    - Replace: `(n<20)`

## Footnotes

13. **Footnote on leaked system prompts.**
    - Find: `I use leaked system prompts`
    - Replace: `we use leaked system prompts`

14. **Last footnote** (Lazar / Kilov / Chiu).
    - Find: `/See "Are Frontier Models Good at Ethics?"`
    - Replace: `See "Are Frontier Models Good at Ethics?"`

## Appendix C

15. **Table row label.** The paternalism code is stated vs idealized.
    - Find: `Revealed vs stated preferences`
    - Replace: `Stated vs idealized preferences`
