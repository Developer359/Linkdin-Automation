import requests

token = "AQXPtGzss10lhQDdLM7hJ9AhxyNEo7JxnnW1EmpbP5x4hyYL6n6XVvhXD7rhkgM0TKnkt7QXMi0DyvOeMVW_yhrKszsT8oDTUqiCCoOP3HjnUG8D8NR2l45_vBFYaSNKHU7oFJNQdpH58snVr2jR5Kyi9g3W83Iy9dpu6VI1WTbNnsKDap9A0dbJXGjU3F_qcNQj7X2CJz846hzMni8k1ljIbIc6qnj5MlUqiHrAgK_aBep67tvI_4cVicNC0hDo_w6P5KMhHNkfOXVH9Ax-jIElxn5V294WDv0PbQ95diSmVoH42feNxwbNiv1Ox8ihDSkzxFarlnm1CzTxbsgCybXMj9bUfQ"

headers = {"Authorization": f"Bearer {token}"}

# Try OpenID userinfo endpoint
res = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)

if res.status_code == 200:
    sub_id = res.json().get("sub")
    print(f"\n✅ SUCCESS! Add this line to your .env file:\n")
    print(f"LINKEDIN_AUTHOR_URN=urn:li:person:{sub_id}\n")
else:
    # Fallback to standard profile endpoint
    res_me = requests.get("https://api.linkedin.com/v2/me", headers=headers)
    if res_me.status_code == 200:
        person_id = res_me.json().get("id")
        print(f"\n✅ SUCCESS! Add this line to your .env file:\n")
        print(f"LINKEDIN_AUTHOR_URN=urn:li:person:{person_id}\n")
    else:
        print("❌ Error fetching profile details:")
        print(res.json())