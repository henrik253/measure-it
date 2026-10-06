"""Fill backbone entries with an account and ticket text, one batch at a time.

    python golden/create-new-golden/fill.py < batch.json

batch.json maps id -> [account, ticket]. Reads golden-draft.json if it exists, otherwise
backbone.json, and writes golden-draft.json. Slices, ids and every other field are kept.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
DRAFT, BACKBONE, ACCOUNTS = HERE / "golden-draft.json", HERE / "backbone.json", HERE / "accounts.json"

items = json.loads((DRAFT if DRAFT.exists() else BACKBONE).read_text())
accounts = json.loads(ACCOUNTS.read_text())
batch = json.load(sys.stdin)
by_id = {i["id"]: i for i in items}
for id_, (account, ticket) in batch.items():
    assert id_ in by_id, f"{id_} is not in the backbone"
    assert account in accounts, f"{id_}: unknown account {account}"
    by_id[id_]["account"], by_id[id_]["ticket"] = account, ticket
DRAFT.write_text(json.dumps(items, indent=4, ensure_ascii=False) + "\n")
print(f"filled {len(batch)}; {sum(i['ticket'] is not None for i in items)}/{len(items)} tickets written")
