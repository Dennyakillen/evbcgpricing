import sys, os
sys.path.insert(0, r"C:\Projekt\BCG\orchestration\infrastructure")
os.environ.setdefault("PRICINGMODEL_AUTH", "key")
os.environ.setdefault("PRICINGMODEL_STORAGE", "evbcgpricinginput")
from blob import _client, CONTAINER_INPUT
svc = _client()
inp = svc.get_container_client(CONTAINER_INPUT)
print("=== Blob input-container ===")
for b in inp.list_blobs():
    mb = b.size / 1e6
    print(f"  {b.name:<45} {mb:>8.0f} MB  {b.last_modified:%Y-%m-%d %H:%M}")
print("\nMaj-parquet = ~1324 MB (27.7M rader t.o.m 2026-05-31)")
print("April-parquet = ~1144 MB (27.4M rader t.o.m 2026-04-30)")
