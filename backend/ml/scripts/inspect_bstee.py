"""Inspect the bstee615/diversevul mirror — its columns, size, splits."""
from datasets import load_dataset

SOURCE = "bstee615/diversevul"

print(f"=== Inspecting {SOURCE} (streaming) ===")
ds = load_dataset(SOURCE, split="train", streaming=True)
print(f"  dataset features: {ds.features}")
print(f"  n_splits (via builder): attempting builder...")

it = iter(ds)
first = next(it)
print(f"\n  first row keys: {list(first.keys())}")
print(f"  first row sample values:")
for k, v in first.items():
    vs = repr(v)[:200]
    print(f"    {k:<24} {type(v).__name__:<10} {vs}")

# Pull a few more rows to spot variation
print("\n  rows 2-5 (truncated values):")
for i in range(4):
    row = next(it)
    print(f"  -- row {i+2} --")
    for k, v in row.items():
        print(f"    {k:<24} {repr(v)[:120]}")

# Check available configs/splits via the builder
print("\n=== Builder info ===")
try:
    from datasets import load_dataset_builder
    b = load_dataset_builder(SOURCE)
    info = b.info
    print(f"  description: {info.description[:200] if info.description else '(none)'}")
    print(f"  citation: {info.citation[:200] if info.citation else '(none)'}")
    print(f"  homepage: {info.homepage}")
    print(f"  size_in_bytes: {info.size_in_bytes}")
    if info.splits:
        for sk, sv in info.splits.items():
            print(f"  split {sk}: {sv}")
except Exception as e:
    print(f"  builder err: {e}")
