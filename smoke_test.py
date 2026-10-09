import requests

sample = """Acme Internet
Monthly Bill
Date: 2025-03-10
Fiber internet service
Total Due: $62.10
"""

files = {"file": ("sample_acme_bill.txt", sample.encode("utf-8"), "text/plain")}
resp = requests.post("http://127.0.0.1:8000/upload", files=files, allow_redirects=False)
print("HTTP", resp.status_code)
if resp.status_code not in (303, 200):
    print(resp.text)
else:
    print("Uploaded. Open http://127.0.0.1:8000 to view the verdict.")
