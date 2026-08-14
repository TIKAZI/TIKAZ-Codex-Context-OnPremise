API_URL = "https://api.example.com/v1"
RELEASE = "v8.1.0"
ERROR_CODE = "DEPLOY_ERR_81"

def deploy(client):
    """Deployment evidence must remain byte-for-byte reviewable."""
    response = client.post(API_URL, json={"release": RELEASE})
    if response.status_code != 200:
        raise RuntimeError(f"{ERROR_CODE}: {response.text}")
    return response.json()
