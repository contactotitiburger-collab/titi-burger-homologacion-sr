#!/usr/bin/env python3
"""Re-autoriza OAuth para Drive/Sheets — imprime URL, escucha callback local, guarda tokens."""
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT = "/home/tito/.openclaw/credentials/google/oauth/client_secret.json"
OUT = Path("/home/tito/.openclaw/credentials/google/oauth/tito_tokens.json")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)
creds = flow.run_local_server(
    port=8765,
    open_browser=False,
    authorization_prompt_message="\n>>> ABRE ESTE LINK Y AUTORIZA:\n{url}\n",
    success_message="Autorización lista, ya puedes cerrar esta pestaña.",
)

td = {
    "token": creds.token,
    "refresh_token": creds.refresh_token,
    "token_uri": creds.token_uri,
    "client_id": creds.client_id,
    "client_secret": creds.client_secret,
    "scopes": creds.scopes,
}
OUT.write_text(json.dumps(td, indent=2))
print(f"OK tokens en {OUT}", flush=True)
