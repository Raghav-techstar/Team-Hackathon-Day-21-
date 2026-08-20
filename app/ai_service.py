import os
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    dotenv_path=ENV_FILE
)


API_KEY = os.getenv(
    "ANTHROPIC_API_KEY"
)


if not API_KEY:
    raise RuntimeError(
        f"ANTHROPIC_API_KEY is not configured. "
        f"Expected .env at: {ENV_FILE}"
    )


client = Anthropic(
    api_key=API_KEY
)


SYSTEM_PROMPT = """
You are the Shipment Operations Assistant
for the Operational Status Dashboard.

Your job is to answer questions related to:

- shipment data
- carriers
- shipment status
- routes
- freight costs
- delivery delays
- data quality
- rejected shipment records
- dashboard functionality
- FastAPI APIs
- OAuth2 authentication
- background refresh
- project architecture

Use only the information provided in the
project context.

Do not invent shipment data.

If the requested information is not available
in the provided context, clearly say that the
information is not available.

Do not answer unrelated general questions.

Keep answers clear, concise, and useful.
"""


def ask_ai(
    question: str,
    context: str,
) -> str:

    prompt = f"""
PROJECT CONTEXT:

{context}


USER QUESTION:

{question}
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.content[0].text