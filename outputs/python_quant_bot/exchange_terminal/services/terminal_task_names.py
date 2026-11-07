"""Keep user-facing task names separate from frozen-core directory names."""
from copy import deepcopy
from hashlib import sha256
import re


def core_task_name_payload(payload):
    # The frozen service remains authoritative for all other request fields.
    if type(payload) is not dict:
        return payload
    result = deepcopy(payload)
    name = result.get("name")
    if type(name) is not str or not name.strip() or len(name) > 64 or any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise ValueError("任务名称需为 1 至 64 个字符，不能包含换行或控制字符。")
    name = name.strip()
    if re.fullmatch(r"[\w-]{1,64}", name) and not re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", name, re.IGNORECASE):
        result["name"] = name
    else:
        # Deterministic names retain the core's no-overwrite behaviour on a
        # duplicate explicit request. The display label remains exact.
        result["name"] = "named-" + sha256(name.encode("utf-8")).hexdigest()[:32]
        result.setdefault("title", name)
    return result
