import requests

API_KEY = "[ENCRYPTION_KEY]"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 1. Fetch Organization ID
org_query = """
query GetOrganizations {
  account {
    organizations {
      id
    }
  }
}
"""

org_res = requests.post("https://api.buffer.com", headers=headers, json={"query": org_query}).json()

if "errors" in org_res:
    print("[X] Error fetching organization:", org_res["errors"])
else:
    org_id = org_res["data"]["account"]["organizations"][0]["id"]
    print(f"[✓] Organization ID: {org_id}")

    # 2. Fetch Channels using OrganizationId type
    channels_query = """
    query GetChannels($orgId: OrganizationId!) {
      channels(input: { organizationId: $orgId }) {
        id
        name
        service
      }
    }
    """

    channels_res = requests.post(
        "https://api.buffer.com",
        headers=headers,
        json={"query": channels_query, "variables": {"orgId": org_id}}
    ).json()

    print("\n[✓] Connected Channels:")
    print(channels_res)