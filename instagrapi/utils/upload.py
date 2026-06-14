from typing import Dict, List, Optional, Union

COAUTHOR_EXTRA_DATA_KEYS = ("invite_coauthor_user_ids", "invite_coauthor_user_id")


def with_coauthor_user_ids(
    extra_data: Dict,
    coauthor_user_ids: Optional[List[Union[int, str]]],
) -> Dict:
    data = dict(extra_data or {})
    if coauthor_user_ids is None:
        return data
    if not isinstance(coauthor_user_ids, list):
        raise ValueError("coauthor_user_ids must be a list of user IDs.")
    for key in COAUTHOR_EXTRA_DATA_KEYS:
        if key in data:
            raise ValueError(f"Use either coauthor_user_ids or extra_data['{key}'], not both.")
    data["invite_coauthor_user_ids"] = [str(user_id) for user_id in coauthor_user_ids]
    return data
