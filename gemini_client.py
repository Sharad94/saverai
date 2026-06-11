import os
import threading

from google import genai
from google.genai import types

FLASH_MODEL = "gemini-2.5-flash"

_client: genai.Client | None = None
_client_lock = threading.Lock()
_api_semaphore = threading.Semaphore(5)


def _get_service_account_credentials():
    """Load GCP service account credentials from Streamlit secrets."""
    try:
        import json
        import streamlit as st
        from google.oauth2 import service_account
        if "GCP_SERVICE_ACCOUNT" in st.secrets:
            sa = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
            creds = service_account.Credentials.from_service_account_info(
                sa, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            return creds, sa.get("project_id")
    except Exception:
        pass
    return None, None


def client() -> genai.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                # 1. Try service account (hosted on Streamlit Cloud)
                creds, project_id = _get_service_account_credentials()
                if creds:
                    _client = genai.Client(
                        vertexai=True,
                        project=project_id,
                        location="us-central1",
                        credentials=creds,
                    )
                else:
                    # 2. Fallback: local ADC (Vertex AI via gcloud)
                    _client = genai.Client(
                        vertexai=True,
                        project=os.environ.get("GCP_PROJECT", "integration-us-central1-687416"),
                        location=os.environ.get("GCP_LOCATION", "us-central1"),
                    )
    return _client


_NO_THINKING = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0)
)


def generate(contents) -> str:
    """Generate text from contents (str or list of Parts + str)."""
    with _api_semaphore:
        response = client().models.generate_content(
            model=FLASH_MODEL, contents=contents, config=_NO_THINKING
        )
    return response.text or ""


def image_part(image_bytes: bytes, media_type: str = "image/jpeg") -> types.Part:
    return types.Part.from_bytes(data=image_bytes, mime_type=media_type)
