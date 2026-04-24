from pathlib import Path

from symboliclight.intent import load_intent_contract


def test_intent_permissions_return_to_top_level_after_child_block(tmp_path: Path) -> None:
    intent = tmp_path / "intent.yaml"
    intent.write_text(
        """
version: "0.1"
kind: "IntentSpec"

permissions:
  web: false
  filesystem:
    read: true
    write: false
  network: false
  tools:
    create_file: true
""",
        encoding="utf-8",
    )

    contract = load_intent_contract(intent)

    assert contract.permissions.web is False
    assert contract.permissions.filesystem_read is True
    assert contract.permissions.filesystem_write is False
    assert contract.permissions.network is False
    assert contract.permissions.tools["create_file"] is True
