# Topic Intelligence App — OpenAI Provision-First Classifier

A Streamlit application for classifying U.S. Congressional actions into exactly one of 22 policy topics using a provision-first methodology.

## Method

1. Read **Mechanism** first.
2. Use **Analytical Summary** to fill gaps or confirm.
3. Use **Title** only for the policy-defined tie-breaks and fallback.
4. Extract the legal **PROVISION**.
5. Classify the provision, not consequence language about DAQO.
6. Return exactly one topic, a rubric confidence score (95/85/70/50), and a runner-up.

## Required Excel columns

- `Mechanism`
- `Analytical Summary`
- `Title`

## Run locally

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Set `OPENAI_API_KEY` securely in Streamlit Secrets when deploying. Do not commit API keys to GitHub.

## Output

The exported workbook adds `Topic`, `Provision`, `Topic Confidence`, `Topic Runner-Up`, validation warnings/errors, and keeps all original columns. It also includes a Human Review worksheet.
