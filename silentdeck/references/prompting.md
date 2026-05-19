# Prompting Guidelines

Use this reference when writing prompts for visual transcript generation, timing-aware script generation, or narration rewriting.

## Visual Transcript Prompt

Ask the model to:

- describe only visible or strongly implied content
- list visible text separately from inferred meaning
- identify charts, diagrams, formulas, code screenshots, and UI screens
- include uncertainty when visual evidence is weak
- avoid adding facts not shown in the frame
- distinguish slide text from interpretation

## Script Generation Prompt

Ask the model to:

- write natural spoken narration
- keep each segment within the target duration
- use the requested language
- preserve slide order
- avoid over-explaining sparse slides
- mark assumptions
- match a presentation tone appropriate to the source material

## Timing Rewrite Prompt

When TTS audio is too long:

- shorten the narration without changing meaning
- remove filler
- keep key terms
- preserve the segment goal
- keep the language and tone unchanged

When audio is short:

- prefer controlled silence padding for small gaps
- only expand text if the narration sounds unnaturally abrupt

## Safety Prompt

For scientific, medical, legal, financial, policy, or compliance content:

- warn that generated narration requires human review
- avoid unsupported factual conclusions
- distinguish visible facts from interpretation
- avoid adding claims that are not visible in the source frames
