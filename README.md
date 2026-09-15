# Topic Intelligence App — OpenAI Provision-First Classifier

A Streamlit application for classifying U.S. Congressional actions into exactly one of 22 policy topics using the supplied provision-first methodology.

## Why this version is different

The previous prototype classified directly from lexical signals. This version uses the complete `classification_policy.md` as the model instruction and follows the intended sequence:

1. Read **Mechanism** first.
2. Use **Analytical Summary** only to fill gaps / confirm.
3. Use **Title** only for the policy-defined tie-breaks and fallback.
4. Extract the legal **PROVISION**.
5. Classify the **PROVISION**, not consequence language about DAQO.
6. Return exactly one topic, a rubric confidence score (95/85/70/50), and a runner-up.

The app also includes a **Transformer-Trap Audit** showing whether known consequence-language terms disappear when the legal provision is extracted.

## Project structure

```text
Topic-Intelligence-app-OpenAI/
├── app.py
├── classifier.py
├── classification_policy.md
├── topics.py
├── utils.py
├── requirements.txt
├── .gitignore
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
└── tests/
    └── test_parser.py
```

## Required Excel columns

The master file must contain:

- `Mechanism`
- `Analytical Summary`
- `Title`

Other columns are preserved unchanged.

## Local setup (PowerShell)

```powershell
cd "C:\path\to\Topic-Intelligence-app-OpenAI"

python -m venv myenv
.\myenv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create your secret file:

```powershell
Copy-Item ".streamlit\secrets.toml.example" ".streamlit\secrets.toml"
notepad ".streamlit\secrets.toml"
```

Replace the placeholder with your real OpenAI API key:

```toml
OPENAI_API_KEY = "sk-..."
```

Run:

```powershell
streamlit run app.py
```

## Streamlit Community Cloud

In the app settings, add:

```toml
OPENAI_API_KEY = "sk-..."
```

under **Secrets**. Never put the key in GitHub.

The repository already ignores `.streamlit/secrets.toml`.

## Model

The UI defaults to:

```text
gpt-5.6-terra
```

You can change the model name in the sidebar to another model available to your OpenAI API project.

## API usage

Each row normally makes one model request. Invalid/malformed responses can be retried according to the sidebar setting. Therefore, if you classify 500 rows with two retries enabled, the normal case is about 500 calls; the maximum can be higher only for rows that need retrying.

The app does not call the API until you press **Classify**.

## Output columns added

The exported workbook puts the classification fields first:

- `Topic`
- `Provision`
- `Topic Confidence`
- `Topic Runner-Up`
- `Classification Warning`
- `Classification Error`

The original columns follow unchanged. `Model Raw Output` is added at the end for debugging/audit.

The Excel download also contains a **Human Review** worksheet containing 50/70 confidence rows plus parser/validation warnings and errors.

## Important methodological note

`classification_policy.md` is the supplied policy prompt and should be treated as the classification specification. Edit that file when the policy itself changes; do not reintroduce keyword-scoring logic into the classifier.

## GitHub

Before pushing, confirm that your key is not staged:

```powershell
git status
git diff --cached
```

Then:

```powershell
git add app.py classifier.py classification_policy.md topics.py utils.py requirements.txt .gitignore .streamlit/config.toml .streamlit/secrets.toml.example tests/test_parser.py README.md
git commit -m "Add OpenAI provision-first Topic Intelligence classifier"
git push
```
