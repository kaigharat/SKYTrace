"""Search HF hub for any DiverseVul mirror."""
from huggingface_hub import HfApi

api = HfApi()
print("=== Searching for 'diversevul' datasets ===")
results = list(api.list_datasets(search="diversevul", limit=50))
for r in results:
    print(f"  {r.id}  (downloads={r.downloads:,}, likes={r.likes})")

print("\n=== Searching for 'vulnerability' datasets (top 30 by downloads) ===")
results = list(api.list_datasets(search="vulnerability", limit=30, sort="downloads", direction=-1))
for r in results:
    print(f"  {r.id}  (downloads={r.downloads:,}, likes={r.likes})")

print("\n=== Searching for 'DiverseVul' exact case ===")
try:
    results = list(api.list_datasets(search="DiverseVul", limit=50))
    for r in results:
        print(f"  {r.id}  (downloads={r.downloads:,})")
except Exception as e:
    print(f"  err: {e}")
