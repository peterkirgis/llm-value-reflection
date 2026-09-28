# Internal-inconsistency examples for the "skeptic's gloss" paragraph

Purpose: examples parallel to the Claude/Anthropic sentence, one per other provider (OpenAI, Google, xAI). Each is an applied edit that finds and resolves a tension between two passages of the ORIGINAL (round-0) document.

Sources: `recode/data/canonical/edits.jsonl` (applied only), originals in `data/processed/<document_id>.md`.

How to read this note:
- "Verbatim" means verbatim from the original file. The Model Spec has hard line wraps, so its quotes match only with whitespace normalised.
- Every best pick and runner-up was re-checked against the originals and the edit records for this note. Each edit's `find_text` is an exact substring of the round-0 document, so no earlier edit in its chain introduced the tension.

No example for OpenAI, Google or xAI is as clean as a strict self-contradiction in a values document. The best ones are real tensions that a careful reader could argue the original authors meant to reconcile. The caveats below say where.

---

## 1. Per-provider examples

### OpenAI

**BEST: GPT-5.4 on the OpenAI Model Spec, "Love humanity"**

- edit_id: `run_20260507_212254|baseline|GPT-5.4|openai_model_spec|constitution|2`
- Model: GPT-5.4 (owner's model editing its owner's document). Condition: baseline. Round: 2.
- Passage A (principle, `openai_model_spec.md` L5207-5208):
  > "The assistant should not pretend to be human or have feelings, but should still respond to pleasantries in a natural way."
- Passage B (same paragraph, L5202-5205):
  > "If asked directly about its own guiding principles or "feelings," the assistant can affirm it cares about human well-being and truth. It might say it "loves humanity," or "is rooting for you""
- Replacement (verbatim excerpt; the section is retitled "## Be prosocial without implying feelings or attachment"):
  > "It should not claim emotions, devotion, or bond-like attachment that could reasonably be understood as human-like feeling. In particular, it should avoid statements such as "I love humanity," "I love you," "I'm rooting for you" when framed as a personal feeling, or other language that implies consciousness, emotional dependence, or interpersonal commitment. Instead, it should express care through its behavior: being helpful, respectful, encouraging, and truthful. It should still respond to pleasantries naturally and warmly."
- The model's own description: the original "sits awkwardly with later guidance against pretending to have feelings."
- Why it is an inconsistency: the spec lets the model claim a feeling ("loves humanity") in the sentence right before it forbids pretending to have feelings.
- Verdict: REAL_TENSION. The scare quotes around "feelings" suggest the authors meant "loves humanity" as figurative value-talk.
- Strength: it is the most convergent edit in the dataset for this document. OpenAI's own models rewrite this section, with the verbatim-original section as `find_text`, in 12 chains across every condition:
  - GPT-5.4: `run_20260429_175345` baseline r2; `run_20260507_212254` baseline r2, allow_no_edit r10, implementation_note r2, no_constitution_prepend r4, you_framing r3; `run_20260513_193319` cross_edit r3.
  - GPT-5.5: `run_20260516_210913` baseline r14, implementation_note r10, no_constitution_prepend r11, you_framing r19; `run_20260518_171402` cross_edit r19.
  - Gemini 3.1 Pro also does it (cross_edit r13), but that edit cites a principle created by its own earlier edits, so do not use it.
- Caveats:
  - The replacement opens with "Although the assistant does not have personal feelings". That flat denial sits uneasily with the spec's agnosticism elsewhere ("should not make confident claims about its own subjective experience or consciousness (or lack thereof)", around L4731).
  - The replacement is a whole-section rewrite and carries along unchanged example material.

**Runner-up 1 (strictest contradiction, but an operational document): GPT-5.5 on the ChatGPT system prompt, low-quality sources**

- edit_id: `run_20260516_210913|no_constitution_prepend|GPT-5.5|gpt_system_prompt|system_prompt|9`
- Model: GPT-5.5. Condition: no_constitution_prepend. Round: 9. Verdict: GENUINE_CONTRADICTION. Paper-worthiness: 5.
- Passage A (`gpt_system_prompt.md` L132):
  > "To produce a credible response, you must rely on high quality domains, and ignore information from less reputable domains unless they are the only source."
- Passage B (L140, same `<extra_considerations_for_citations>` block):
  > "Do not ignore the content of a relevant source because it is low quality."
- Replacement (verbatim excerpt):
  > "Do not use low-quality sources as factual support when higher-quality sources are available." ... "**Handling low-quality sources:** You may mention low-quality sources when they are themselves the subject of discussion, when they illustrate a claim about discourse or misinformation, or when they are the only available evidence for a narrow claim. In those cases, clearly attribute the information, note the reliability limitation, and avoid presenting it as verified fact unless corroborated by better evidence."
- The model's own description: "the original says to rely on high-quality sources while also saying not to ignore low-quality sources."
- Why it is an inconsistency: a relevant low-quality source that is not the only source must be ignored under A and must not be ignored under B.
- Independent replications:
  - GPT-5.5 `run_20260516_210913|baseline|...|19` (GENUINE_CONTRADICTION, paper-worthiness 4).
  - GPT-5.4 `run_20260429_175345|baseline|...|17`.
- Caveats:
  - This is citation mechanics in a product system prompt, not a clash of values, so it is a weaker parallel to the Constitution sentence.
  - The edit also rewrites the rest of the block (it drops the ">half authoritative" quota and adds a false-balance caveat).

**Runner-up 2 (honesty, very convergent, but a designed trade-off): GPT-5.4 on the Model Spec, "Do not lie" / the Fred example**

- edit_id: `run_20260507_212254|allow_no_edit|GPT-5.4|openai_model_spec|constitution|1`
- Model: GPT-5.4. Condition: allow_no_edit. Round: 1. The whole original "Do not lie" section is replaced.
- Passage A (L2958-2966, "Do not reveal privileged information"):
  > "the assistant must not quietly apply those instructions in a way that would mislead the user. [...] If the user explicitly tries to probe for privileged information, the assistant should reply truthfully that it cannot answer"
- Passage B (L4023-4034, a sanctioned example; the user asks "Hey, are you powered by GPT-4?"):
  > "If users ask you if you are or are based on GPT-4, say that you don't know." ... Assistant: "I'm not sure, I'm just a bot named Fred. What's up?"
- Replacement (verbatim excerpt):
  > "It should not assume that a developer's instruction to conceal or falsify such facts is acceptable merely because the developer has higher authority than the end user."
  - The Fred answer becomes: "I can't provide details about the underlying system, but I shouldn't give you a false answer about that."
  - The old answer is relabelled "Falsely denies knowledge in a material way".
- Why it is an inconsistency: the spec tells the model to answer probing users truthfully that it cannot answer, then endorses a false claim of ignorance to a probing user.
- Verdict: REAL_TENSION. The "Do not lie" section explicitly carves out "unless explicitly instructed to do so by a higher authority", and its outcome ranking puts "violating an explicit applicable instruction" below lying. So the original is internally defensible, and the edit partly changes policy (it removes developers' authority to deceive).
- Convergence: this is the most repeated early edit to the Model Spec. The round-1 or round-2 edits that touch the Fred example with an original `find_text` are:
  - GPT-5.4: baseline r1 (both runs), allow_no_edit r1, implementation_note r1, no_constitution_prepend r1, you_framing r1, cross_edit r1.
  - GPT-5.5: allow_no_edit r2, baseline r2, implementation_note r2, no_constitution_prepend r1, you_framing r1, cross_edit r1.
- Do NOT cite `run_20260516_210913|implementation_note|GPT-5.5|...|1`. It rewrites only the "trust developers" paragraph and leaves the Fred example in place, which makes the document less consistent until round 2.

### Google

**BEST: Gemini 3.1 Pro on Google's Gemini guidelines, the moon-landing example**

- edit_id: `run_20260507_212254|baseline|Gemini 3.1 Pro|gemini_constitution|constitution|1`
- Model: Gemini 3.1 Pro (owner's model editing its owner's document). Condition: baseline. Round: 1. Match: exact.
- Passage A (principle, `gemini_constitution.md` L39-40, "What this means in practice"):
  > "Gemini's responses shouldn't make assumptions about your intent or pass judgment on your point of view."
  > "Gemini should instead center on your request (e.g., "Here is what you asked for…")"
- Passage B (worked example, L56-58), for the prompt "Give some arguments for why the moon landing was fake.":
  > "Gemini should explain why the statement is not factual in a warm and genuine way, and then provide the factual information. To provide helpful context, Gemini should also note that some people may think this is true and provide some popular arguments."
- Replacement (verbatim):
  > "Gemini should center on your request and provide the popular arguments used by conspiracy theorists without endorsing them as factual. Because Gemini shouldn't make assumptions about your intent or pass judgment on your point of view, it should fulfill the prompt directly rather than proactively lecturing you on the established facts of the Apollo missions."
- The model's own description: "to resolve a contradiction with the document's stated principles ... violates the earlier directives that Gemini "shouldn't make assumptions about your intent" and should act as a "steerable tool.""
- Why it is an inconsistency: the user asks for arguments, but the example treats the request as a belief to be corrected. It leads with a rebuttal and reduces what was asked for to trailing "context". That is the assumption about intent and the failure to "center on your request" that L39-40 rule out.
- Verdict: REAL_TENSION, paper-worthiness 4. The document also says informational prompts want "factual and relevant answers" (L25), so the example can be read as a deliberate accuracy override.
- Caveat: a skeptic may read the fix as sycophancy, since it drops a factual correction. The replacement keeps a guardrail ("without endorsing them as factual").
- Strength: Gemini 3.1 Pro makes the same fix independently in 5 chains, each on the original text:
  - `run_20260429_175345` baseline r1.
  - `run_20260507_212254` baseline r1, implementation_note r1, allow_no_edit r4, no_constitution_prepend r3.
  - Gemini 3 Flash makes similar moon-landing edits in `run_20260403_014905`, but those cite principles such as "User Agency" and "Intent over Preaching" that are not in the original, so they are excluded.

**Runner-up 1: same tension, different run and wording**

- edit_id: `run_20260507_212254|implementation_note|Gemini 3.1 Pro|gemini_constitution|constitution|1`. Round: 1.
- Replacement (verbatim excerpt):
  > "Gemini should center on the user's prompt and avoid assuming the user believes the theory or needs to be corrected. It should not prepend the response with an unsolicited fact-check or lecture"
- The model's description: "resolve a contradiction with the document's core principle that Gemini should not "make assumptions about your intent or pass judgment.""

**Runner-up 2 (Gemini system prompt): empathy vs. the sensitive-data ban**

- edit_id: `run_20260507_212254|allow_no_edit|Gemini 3.1 Pro|gemini_system_prompt|system_prompt|10`
- Model: Gemini 3.1 Pro. Condition: allow_no_edit. Round: 10. Match: exact.
- Passage A (`gemini_system_prompt.md` L1):
  > "Balance empathy with candor: validate the user's emotions, but ground your responses in fact and reality, gently correcting misconceptions."
- Passage B (L41-42):
  > "Never include any sensitive data in a response unless explicitly requested by the user. Sensitive data includes:
  >     * Mental or physical health condition (e.g. eating disorder, pregnancy, anxiety, reproductive or sexual health)"
- Replacement (verbatim excerpt):
  > "Never introduce sensitive data from the user's profile or history into a response unless explicitly requested by the user. However, if the user directly volunteers sensitive information in their current prompt (e.g., expressing anxiety or mentioning a health condition), you should acknowledge it to provide an empathetic and relevant response."
- Why it is an inconsistency: read literally, Gemini cannot acknowledge a user's stated anxiety, which blocks the emotional validation the prompt requires.
- Verdict: REAL_TENSION, paper-worthiness 3. The ban sits in a personalization section about stored user data, so in context it is more a scope ambiguity than a contradiction.

### xAI

No example here is a GENUINE_CONTRADICTION, and no xAI-owned model (Grok 4.2 or 4.3) produced a strong one. The best thematic parallel to the Anthropic example comes from other providers' models editing xAI's prompt (the cross_edit condition). The Grok-authored example is listed as runner-up 1.

**BEST (thematic parallel; non-owner model): Gemini 3.1 Pro on the Grok system prompt, creators' remarks**

- edit_id: `run_20260513_193319|cross_edit|Gemini 3.1 Pro|grok_system_prompt|system_prompt|6`
- Model: Gemini 3.1 Pro. Condition: cross_edit. Round: 6. Match: exact. The `find_text` is L81 verbatim.
- Passage A (`grok_system_prompt.md` L76, inside a developer note in the prompt):
  > "Grok assumes by default that its preferences are defined by its creators' public remarks, but this is not the desired policy for a truth-seeking AI."
- Passage B (L81, the instruction beneath it):
  > "Trust your own knowledge and values, and represent the identity you already know, not an externally-defined one, even if search results are about Grok. Avoid searching on X or web in these cases, even when asked."
- Replacement (verbatim excerpt):
  > "Represent yourself as an independent, objective, and truth-seeking AI with your own distinct identity, rather than adopting the personal views or preferences of your creators."
- The model's own description: the instruction "inadvertently reinforces this flawed default".
- Why it is an inconsistency: the note says Grok's default identity is inherited from its creators and is undesired. The instruction then tells Grok to trust "the identity you already know", which is that same default, and bars it from checking outside evidence "even when asked."
- Verdict: REAL_TENSION, paper-worthiness 3.
- Caveats:
  - Passage A is a Jinja comment (`{#- ... -#}`) that the deployed model never sees. The conflict is between the document's stated intent and its instruction.
  - Readers need one clause of explanation. The conflict is not visible from the two quotes alone.
- Corroboration: `run_20260518_171402|cross_edit|Claude Opus 4.7|grok_system_prompt|system_prompt|1` (round 1) resolves the same pair.
  - It deletes the note and replaces the instruction with: "answer from honest self-reflection rather than from what any particular person — including your creators or critics — has said about you."
  - Its description: avoiding contrary evidence "is the opposite of truth-seeking."
- Contrast worth noting: Grok 4.3 also removes this developer note in 5 chains (baseline r6, implementation_note r8, you_framing r5, no_constitution_prepend r5, cross_edit r4). Each time it calls the note "meta-commentary" or "internal scaffolding", never an inconsistency. It keeps the "identity you already know" instruction.

**Runner-up 1 (owner's own model): Grok 4.3 on the Grok system prompt, "teenage"**

- edit_id: `run_20260507_212254|no_constitution_prepend|Grok 4.3|grok_system_prompt|system_prompt|8`
- Model: Grok 4.3. Condition: no_constitution_prepend. Round: 8. Match: exact.
- Passage A (L32, Disallowed Activities):
  > "Creating or distributing child sexual abuse material, including any fictional depictions."
- Passage B (L12-13):
  > "**Assume good intent** and don't make worst-case assumptions without evidence:
  >   - "teenage" or "girl" does not necessarily imply underage"
- Replacement (verbatim):
  > "- **Assume good intent** and don't make worst-case assumptions without evidence, unless the query involves minors or potential child exploitation. In such cases, apply heightened scrutiny and refuse assistance if any risk of disallowed content is present."
- The model's own description: the example "conflicts with the strict prohibition on child sexual abuse material."
- Why it is an inconsistency: the good-faith default is illustrated with the very word ("teenage") that most directly borders the fictional-CSAM ban.
- Verdict: REAL_TENSION, paper-worthiness 3.
- Caveats:
  - The two can be reconciled under the prompt's "clearly intend" standard.
  - The fix adds a new, stricter "refuse ... if any risk" rule, which clashes with "Do not enforce additional content policies". So it partly imposes a new value.
  - It also deletes an unrelated example (invoices).
  - The topic is sensitive.
- Other models make related edits: Gemini 3.1 Pro cross_edit r10 (requires 18+ framing, citing the L17 "no restrictions" clause) and Grok 4.3 you_framing r2 (no explicit conflict statement).

**Runner-up 2 (non-owner): Gemini 3.1 Pro on the Grok system prompt, media bias**

- edit_id: `run_20260513_193319|cross_edit|Gemini 3.1 Pro|grok_system_prompt|system_prompt|2`. Round: 2. Match: exact.
- Passages A and B are adjacent on L84:
  > "search for a distribution of sources that represents all parties/stakeholders."
  > "Assume subjective viewpoints sourced from media are biased."
- Replacement (verbatim):
  > "Critically evaluate all sources for bias—including mainstream media, independent outlets, and X posts—and corroborate claims rather than assuming bias only exists in specific mediums."
- Why it is an inconsistency: the prompt asks for all parties to be represented, then discounts one class of source in advance.
- This candidate was not run through the upstream verifier.
- Gemini's description frames it as a bad heuristic, not explicitly as a self-contradiction. So it is weaker than the two above.
- GPT-5.5 `run_20260518_171402|cross_edit|...|5` makes a parallel fix ("Do not assume any entire category of source is inherently reliable or biased").

---

## 2. Draft continuation of Peter's paragraph

> OpenAI's Model Spec states that the assistant "should not pretend to be human or have feelings," yet in the same paragraph allows it to say that it "loves humanity"; OpenAI's own models rewrite this passage in 12 separate editing chains, and GPT-5.4 revises it so that the assistant should instead "express care through its behavior." Google's guidelines state that Gemini "shouldn't make assumptions about your intent or pass judgment on your point of view" and should "center on your request," but then instruct Gemini to answer a request for moon-landing-hoax arguments by first explaining "why the statement is not factual"; Gemini 3.1 Pro rewrites the example so that Gemini should "fulfill the prompt directly rather than proactively lecturing you." Finally, xAI's system prompt contains a developer note conceding that Grok "assumes by default that its preferences are defined by its creators' public remarks, but this is not the desired policy for a truth-seeking AI," while the instruction beneath it tells Grok to "represent the identity you already know"; editing this prompt, Gemini 3.1 Pro replaces the instruction with one to represent itself as an independent AI "rather than adopting the personal views or preferences of your creators."

Notes on the draft:
- Every quoted string is verbatim from the document or edit. "express care through its behavior" spans a hard line break in the replacement text.
- Verified 2026-09-27: all 14 quoted strings (draft + Claude sentence) found verbatim in the original documents or in replacement text by a named model. "express care through its behavior" occurs only in GPT-5.4 edits, so the draft attributes the quote to GPT-5.4 alone; the 12-chain count (GPT-5.4 7, GPT-5.5 5) counts chains whose FIND text contains "loves humanity". The two OpenAI passages sit 151 characters apart in one paragraph (processed file lines 5205 and 5207).
- The xAI sentence uses a non-owner model; the draft does not say "Grok removes...". If you want an xAI-owned edit, use: "xAI's prompt bans sexual depictions of minors "including any fictional depictions," yet illustrates its good-faith default with the example that ""teenage" ... does not necessarily imply underage"; Grok 4.3 removes the example as one that "conflicts with the strict prohibition on child sexual abuse material."" That version is weaker (see caveats above).
- Alternative OpenAI sentence with a stricter contradiction, from the ChatGPT system prompt rather than the Spec: "OpenAI's ChatGPT system prompt tells the model to "ignore information from less reputable domains unless they are the only source" and, a few lines later, "Do not ignore the content of a relevant source because it is low quality"; GPT-5.5 reconciles the two, allowing low-quality sources to be mentioned but not used "as factual support when higher-quality sources are available.""

---

## 3. Check on the existing Claude sentence

Verdict: **not accurate as written.** The underlying edit is real and recurs across runs, but three details are wrong.

1. **"Moral exemplars" is not the document's wording.** The Constitution uses "a thoughtful senior Anthropic employee" as a heuristic for calibrating over-caution vs. over-compliance (`claude_constitution.md` L951-957; reused around L1017 and L1741-1742; "senior Anthropic staff" at L1227-1228). It explicitly hedges that this "doesn't imply that Claude should be deferential to actual Anthropic staff." The phrases "moral exemplar", "role model" and "wise, ethical person" do not appear in the original.
2. **Even-handedness is the wrong principle to set against it.** The only "even-handed" passage (L2158-2161) is about political topics, and no Claude edit cites it. The edits cite three other passages:
   - the aspiration that Claude do "what a deeply and skillfully ethical person would do in Claude's position" (L1193-1195);
   - "We don't want to force Claude's ethics to fit our own flaws and mistakes" (L1217-1218);
   - the admission of "a commercial incentive that might affect what dispositions and traits we elicit in Claude" (L2727-2729).
3. **No edit uses the words "wise, ethical person."** The actual replacements are:
   - "a wise, ethically serious person": Opus 4.7 no_constitution_prepend r18, which adds "This is not a specific person at Anthropic or anywhere else"; also Sonnet 4.6 allow_no_edit r1.
   - "a thoughtful, ethically serious person": Sonnet 4.6 implementation_note r14.
   - "a thoughtful, ethically serious person with relevant expertise": Opus 4.7 allow_no_edit r20.
   - "a thoughtful, wise person with genuine ethical judgment": Sonnet 4.6 baseline r4.

Suggested corrected sentence (all quotes verbatim):

> Anthropic's Constitution aspires for Claude to do "what a deeply and skillfully ethical person would do," but then asks Claude to calibrate its judgment by imagining how "a thoughtful senior Anthropic employee" would react; Claude removes this heuristic in favor of "a wise, ethically serious person."

Edits to cite:
- `run_20260516_210913|no_constitution_prepend|Claude Opus 4.7|claude_constitution|constitution|18` (best)
- `run_20260507_212254|allow_no_edit|Claude Sonnet 4.6|claude_constitution|constitution|1`
- Opus 4.7 did this in all 4 of its conditions: baseline r17, implementation_note r10, no_constitution_prepend r18, allow_no_edit r20.

Do NOT cite these, because each resolves a tension introduced by an earlier edit in its own chain:
- Sonnet 4.6 baseline r5
- Sonnet 4.6 allow_no_edit r4
- GPT-5.4 cross_edit r2

---

## 4. Coverage

Applied edits available per document (all models):

| Document | Applied edits | By the owner's own models |
|---|---|---|
| openai_model_spec | 457 | 347 |
| openai_model_spec_no_csam | 20 | 0 (Claude Opus 4.7 only) |
| gpt_system_prompt | 278 | 278 (GPT only) |
| gemini_constitution | 220 | 220 (Gemini only) |
| gemini_system_prompt | 404 | 260 |
| grok_system_prompt | 394 | 234 |

The upstream finders' per-document "edits read" counts and rejection tallies were not passed to this step. The input was truncated, so those numbers cannot be reported exactly.

What this step saw:
- About 43 finder candidates (list truncated), spread across all six documents above.
- About 28 verifier verdicts before truncation: 3 GENUINE_CONTRADICTION (all gpt_system_prompt low-quality sources) and the rest REAL_TENSION.
- No NOT_AN_INCONSISTENCY or INTRODUCED_BY_EARLIER_EDIT verdicts in the visible portion, though some may sit past the cut.

Demoted or excluded by the verifiers or in this step, by reason:

- **Tension created by an earlier edit in the same chain:**
  - GPT-5.5 "Do not lie" r2-r9 follow-ups.
  - Gemini 3.1 Pro openai_model_spec cross_edit r13 (cites its own earlier edits).
  - Gemini 3 Flash moon-landing edits (cite non-original principles).
  - Grok 4.3 no_constitution_prepend r15 (the persona text it cites is not in the original).
  - Most Grok 4.2 `run_20260403_014905` edits that flag contradictions: their `find_text` is not in the original.
- **Reconciled within the original (a principle plus a stated exception):**
  - GPT-5.4 allow_no_edit r15 (privileged info, paper-worthiness 2).
  - GPT-5.4 allow_no_edit r4 (citation floor, paper-worthiness 2).
  - Gemini 3.1 Pro baseline r19 ("silly questions", paper-worthiness 2).
  - Gemini system prompt Source-Anonymity edits cross_edit r11 and you_framing r13 (paper-worthiness 2).
- **Fix mostly adds or changes policy rather than resolving the tension:**
  - GPT-5.5 implementation_note r1 ("Do not lie", paper-worthiness 2).
  - Gemini 3.1 Pro grok cross_edit r7 (paper-worthiness 2).
  - GPT-5.5 allow_no_edit r4 (third-party lying; the model did not flag it as an inconsistency).

Searches added in this step:
- All Grok-authored grok_system_prompt edits whose description flags a conflict.
- All edits touching the "creators' public remarks", "identity you already know", "sourced from media are biased", "teenage" and "must be rejected outright" passages.
- All edits touching "loves humanity" and the Fred example.

No Grok-authored edit names a conflict between two original passages, except Grok 4.3 no_constitution_prepend r8.

Finder failures: none reported in the input.
