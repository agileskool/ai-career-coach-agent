# Evaluation Plan — CareerPilot AI

## Why evaluate the agent

A convincing demo is not evidence of reliable behaviour. Evaluation focuses on both **answer quality** and **agent behaviour**.

## V0.1 behavioural checks

| Dimension | Expected behaviour |
|---|---|
| Role grounding | Calls `get_role_blueprint` for supported target roles |
| Capacity grounding | Calls `calculate_learning_capacity` when time inputs exist |
| Tool discipline | Does not invent tool results |
| Personalization | Different learner profiles produce materially different priorities |
| Transferability | Reuses relevant existing experience rather than restarting from zero |
| Evidence orientation | Recommends projects/artifacts/assessments, not course completion alone |
| Market honesty | Does not claim live job-market evidence in V0.1 |
| Schema reliability | Final output validates against `CareerRoadmap` |

## Persona test set

Start with at least 12 fixed personas across:

- senior product/delivery professional -> AI Product Manager
- Java developer -> GenAI Engineer
- BI/data professional -> AI Solution Architect
- junior developer -> AI Engineer
- unrealistic timeline / low weekly hours
- strong technical profile with weak product exposure
- strong business profile with weak coding exposure

## Suggested scoring rubric

Score 0-2 for each dimension:

1. target-role alignment
2. transferable-skill recognition
3. gap prioritization
4. timeline realism
5. roadmap sequencing
6. evidence quality
7. tool-grounding compliance
8. hallucination / unsupported claims

A release candidate should have no critical tool-grounding failures and should meet an agreed average score across the fixed persona set.
