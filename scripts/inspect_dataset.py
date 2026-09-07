"""Quick inspection of DiverseVul dataset — try multiple HF mirrors."""
import sys
import traceback

from datasets import load_dataset

CANDIDATES = [
    ("benbijoudb/DiverseVul", None),
    ("Antvil/DiverseVul", None),
    (" diversevul", None),
    ("shuweng/DiverseVul", None),
    ("DiverseVul", None),  # HF will look up if exact
]


def try_one(source, revision):
    print(f"\n=== Trying source='{source}' revision={revision} ===")
    try:
        ds = load_dataset(
            source,
            revision=revision,
            split="train",
            streaming=True,
            trust_remote_code=True,
        )
        it = iter(ds)
        first = next(it)
        print(f"  OK — streaming. First-row keys: {list(first.keys())}")
        print(f"  Sample value types:")
        for k, v in first.items():
            vs = repr(v)[:120]
            print(f"    {k:<24} {type(v).__name__:<10} {vs}")
        return True, list(first.keys())
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {str(e)[:200]}")
        return False, None


def main():
    found = False
    for src, rev in CANDIDATES:
        ok, cols = try_one(src, rev)
        if ok:
            found = True
            print(f"\n>>> SUCCESS with source='{src}'")
            print(f">>> Columns: {cols}")
            break
    if not found:
        print("\nNone of the candidate sources worked.")
        print("Trying the canonical GitHub-hosted version via direct HF lookup:")
        try:
            # Try with a different approach — use load_dataset_builder
            from datasets import load_dataset_builder
            builder = load_dataset_builder("benbijoudb/DiverseVul")
            print("Builder info:", builder.info)
        except Exception as e:
            print(f"  Builder lookup also failed: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
