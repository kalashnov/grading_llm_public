# Criteria Prompt Sessions: Final

Each question directory contains the prompt bodies used by
`backend/generate_criteria.py`, rendered without calling Claude.

Feed them in this order:

1. Use `00_system.md` as the system/developer instruction if your
   chat surface supports that. Otherwise paste it before Turn 1.
2. Send `01_turn1_criteria.md` and save the returned JSON criteria.
3. In the same conversation, send `02_turn2_few_shot.md` and save
   the returned JSON few-shot examples.

Rendered question directories (examples):
- `2.1/`
- `3.3/`
- `4.3/`
