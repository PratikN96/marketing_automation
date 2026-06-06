"""
Run this once to get your YouTube OAuth refresh token.
It opens a browser, you log in with your YouTube account, and it saves the token.
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.oauth2.credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0, open_browser=True)

    token_data = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print("\n✅ Token saved to token.json")
    print(f"\n   client_id:     {credentials.client_id}")
    print(f"   client_secret: {credentials.client_secret}")
    print(f"   refresh_token: {credentials.refresh_token}")
    print("\n👉 Copy these 3 values — you'll need them as GitHub Secrets later.")


if __name__ == "__main__":
    main()
