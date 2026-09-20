import json
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class PolicyDocument:
    policy_id: str
    title: str
    content: str
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def searchable_text(self) -> str:
        title_repeats = " ".join([self.title] * 3)
        return f"{self.policy_id} {title_repeats} {self.content}"


_POLICIES_FILENAME = "policies.json"


def _resolve_policies_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(here, "..", "..", "data", _POLICIES_FILENAME))
    if os.path.isfile(candidate):
        return candidate
    fallback = os.path.join(os.getcwd(), "data", _POLICIES_FILENAME)
    if os.path.isfile(fallback):
        return fallback
    raise FileNotFoundError(
        f"Could not locate {_POLICIES_FILENAME}. "
        f"Tried: {candidate} and {fallback}. "
        f"Ensure data/{_POLICIES_FILENAME} exists."
    )


class KnowledgeBase:
    def __init__(self, policies_path: str | None = None):
        self.policies_path = policies_path or _resolve_policies_path()
        self.documents: List[PolicyDocument] = []
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.policies_path):
            raise FileNotFoundError(
                f"Policy file not found at: {self.policies_path}"
            )
        try:
            with open(self.policies_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in policy file {self.policies_path}: {exc}"
            ) from exc

        if not isinstance(raw, list):
            raise ValueError(
                f"Policy file {self.policies_path} must contain a JSON list."
            )
        if len(raw) == 0:
            raise ValueError(
                f"Policy file {self.policies_path} is empty. At least one policy required."
            )

        docs: List[PolicyDocument] = []
        for idx, entry in enumerate(raw):
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Policy entry #{idx} is not an object in {self.policies_path}"
                )
            missing = [k for k in ("policy_id", "title", "content", "source") if k not in entry]
            if missing:
                raise ValueError(
                    f"Policy entry #{idx} missing required keys: {missing}"
                )
            docs.append(
                PolicyDocument(
                    policy_id=str(entry["policy_id"]).strip(),
                    title=str(entry["title"]).strip(),
                    content=str(entry["content"]).strip(),
                    source=str(entry["source"]).strip(),
                )
            )
        self.documents = docs

    def all_documents(self) -> List[PolicyDocument]:
        return list(self.documents)

    def count(self) -> int:
        return len(self.documents)
