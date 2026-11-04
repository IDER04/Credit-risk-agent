# Credit Risk Agent

A conversational assistant for querying and maintaining a bank's client and loan database in plain language. You ask about clients, loans and payment incidents in English or French. The agent calls database tools, returns the actual figures, and reports each client's risk level, which comes from fixed, auditable rules and not from the language model. Any change to the data (create, update, delete) is held until a human confirms it.

Built with Python, MySQL and an OpenAI-compatible LLM API. All data used in this project is synthetic.

## How it works

```
User ──► Agent (LLM + tool calling) ──► Tools ──► MySQL
                                          │
                                          └──► Risk rules (risk_model.py)
```

**LLM (`agent.py`).** The agent uses the OpenAI client, pointed at OpenRouter by default, with the model set through an environment variable. Each question runs in a loop of at most 5 steps: the model either answers or requests a tool, the tool runs, and the result goes back to the model. The system prompt forces the model to call a tool for any question about clients, never invent ids, names or figures, report tool errors as they are, and answer in the user's language.

**Tools (`tools.py`).** The functions the model is allowed to call. Each one maps to a specific operation on the database. The model cannot run arbitrary SQL.

**MySQL (`database.py`, `config.py`).** All access goes through one small layer with parameterized queries. Reads return rows as dictionaries. Writes run as a single transaction and roll back on error. Credentials are read from environment variables.

**Risk rules (`risk_model.py`).** The risk level of a client is computed by deterministic rules applied to payment incidents recorded in the database. The same data always gives the same result, and the LLM never decides or adjusts a score. It only retrieves and explains it. <!-- Add one or two lines here on the actual rules: which incident types count, thresholds, risk levels returned. -->

**Confirmation on writes.** Tools that modify data do not execute directly. They return a pending action with a human-readable description, which is shown to the user. The change runs only if the user approves. If the user declines, the model receives a "cancelled" result and tells the user that nothing was changed. The prompt also forbids the model from claiming a change unless a tool actually returned `created`, `updated` or `deleted`.

The split is deliberate: the LLM handles language and routing, while numbers, scoring and data changes stay in code that can be tested and audited.

## Example questions

- *Which clients have payment incidents?*
- *What is the risk level of client 12, and why?*
- *Show me all the loans of client 12.*
- *Create a new Immobilier loan for client 12.* (the agent asks for any missing detail, then waits for your confirmation before writing)

Questions in French work the same way.

## Setup

**Requirements:** Python 3.10 or later, a running MySQL server, and an API key for an OpenAI-compatible provider such as OpenRouter.

1. Clone the repository and create a virtual environment.

   ```bash
   git clone https://github.com/IDER04/Credit-risk-agent.git
   cd Credit-risk-agent
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

2. Install the dependencies.

   ```bash
   pip install -e .
   ```

3. Create the database and load the sample data.

   ```bash
   mysql -u root -p -e "CREATE DATABASE RisqueClt"
   mysql -u root -p RisqueClt < schema.sql
   ```

4. Create a `.env` file in the project root.

   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=RisqueClt
   T_INCIDENT=IncidentPaiement

   LLM_API_KEY=your_api_key
   LLM_BASE_URL=https://openrouter.ai/api/v1
   LLM_MODEL=your_model_name
   ```

   If `DB_PORT` is not set, the code defaults to 8889 (the MAMP default). Set it to match your MySQL server.

5. Run the agent.

   ```bash
   python main.py
   ```

## Limitations

- The risk level is rule-based. It is not a statistical or machine-learning model.
- The assistant only knows what the database contains and what its tools can do. If no tool fits a question, it says so instead of guessing.
