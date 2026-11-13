"""Persistent registry of in-flight OpenAI batch jobs.

When a script submits a batch it records the batch ID here, keyed by a stable
job key (folder + chunk index). If the script is interrupted before the batch
finishes, the next run recalls the recorded batch ID and just re-attaches
monitoring instead of submitting (and paying for) the work again.

The registry self-cleans: once a chunk's results have been consumed the caller
clears its key, so the file only ever holds batches that are still in flight.
"""

import json
import os

REGISTRY_FILENAME = ".batch_registry.json"

# Batch statuses that mean the recorded batch is dead and must be resubmitted.
_DEAD_STATUSES = ("failed", "expired", "cancelled", "cancelling")


def _registry_path(registry_dir):
    return os.path.join(registry_dir, REGISTRY_FILENAME)


def _load(registry_dir):
    path = _registry_path(registry_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(registry_dir, data):
    with open(_registry_path(registry_dir), "w") as f:
        json.dump(data, f, indent=2)


def record_batch_id(registry_dir, key, batch_id):
    data = _load(registry_dir)
    data[key] = batch_id
    _save(registry_dir, data)


def clear_batch_id(registry_dir, key):
    data = _load(registry_dir)
    if key in data:
        del data[key]
        _save(registry_dir, data)


def get_or_submit_batch(client, registry_dir, key, submit_fn):
    """Return a batch ID for `key`, reusing a previously submitted batch if one
    is still alive.

    - If `key` has a recorded batch ID and that batch is retrievable and not in
      a dead state, its ID is returned (monitoring re-attaches, no resubmit).
    - Otherwise `submit_fn()` is called to submit a fresh batch, and the new ID
      is recorded before being returned.
    """
    recorded = _load(registry_dir).get(key)
    if recorded:
        try:
            batch = client.batches.retrieve(recorded)
        except Exception as e:  # noqa: BLE001 - any retrieval failure -> resubmit
            print(f"  [registry] recorded batch {recorded} not retrievable ({e}); resubmitting")
        else:
            if batch.status in _DEAD_STATUSES:
                print(f"  [registry] recorded batch {recorded} is {batch.status}; resubmitting")
                clear_batch_id(registry_dir, key)
            else:
                print(f"  [registry] reusing existing batch {recorded} (status={batch.status})")
                return recorded

    batch_id = submit_fn()
    record_batch_id(registry_dir, key, batch_id)
    return batch_id
