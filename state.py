import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, available_timezones

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Path to the JSON state file: ./data/state.json next to this script
STATE_PATH = Path(__file__).parent / "data" / "state.json"


def _empty_availability() -> dict[str, list[dict[str, str]]]:
    return {day: [] for day in DAY_KEYS}


def load_state() -> dict[str, Any]:
    """
    Load bot state from data/state.json.

    Returns a dict shaped like:
        {"users": { "<user_id_str>": { "games": [..] }, ... }}

    If the file is missing, invalid, or doesn't match this shape,
    returns {"users": {}}.
    """
    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"users": {}}
    except json.JSONDecodeError:
        return {"users": {}}

    if not isinstance(data, dict) or "users" not in data:
        return {"users": {}}

    if not isinstance(data["users"], dict):
        data["users"] = {}

    return data


def save_state(state: dict[str, Any]) -> None:
    """Save bot state back to data/state.json as pretty JSON."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def normalize_game_name(name: str) -> str:
    """Lowercase the name and remove all whitespace."""
    return "".join(name.split()).lower()


def validate_timezone(tz: str) -> bool:
    """Return True if tz is a valid IANA timezone name."""
    return tz in available_timezones()


def validate_time(t: str) -> bool:
    """Return True if t is a valid HH:MM time string."""
    try:
        datetime.strptime(t, "%H:%M")
        return True
    except ValueError:
        return False


def add_game_to_state(state: dict[str, Any], user_id: int, game_name: str) -> None:
    """
    Add or update a game for this user in `state`.

    Matching is case- and whitespace-insensitive:
    if a normalized match exists, replace it with `game_name`;
    otherwise, append `game_name`.
    """
    user_key = str(user_id)
    users = state["users"]

    if user_key not in users:
        users[user_key] = {"games": []}

    games = users[user_key]["games"]
    normalized_new = normalize_game_name(game_name)

    for idx, existing in enumerate(games):
        if normalize_game_name(existing) == normalized_new:
            games[idx] = game_name
            break
    else:
        games.append(game_name)


def remove_game_from_state(state: dict[str, Any], user_id: int, game_name: str) -> bool:
    """
    Remove a game for this user in `state`.

    Matching is case- and whitespace-insensitive:
    if a normalized match exists, remove it and return True;
    otherwise, return False.
    """
    user_key = str(user_id)
    users = state["users"]

    if user_key not in users:
        return False

    user = users[user_key]
    if "games" not in user:
        return False

    games = user["games"]
    if not games:
        return False

    normalized_query = normalize_game_name(game_name)
    for game in games:
        if normalize_game_name(game) == normalized_query:
            games.remove(game)
            return True

    return False


def list_games_from_state(state: dict[str, Any], user_id: int) -> list[str]:
    """
    Return a list of this user's games from `state`.

    If the user or games list is missing, returns an empty list.
    """
    user_key = str(user_id)
    users = state["users"]

    if user_key not in users:
        return []

    user = users[user_key]
    if "games" not in user:
        return []

    return list(user["games"])


def get_common_games(
    state: dict[str, Any],
    user_id_a: int,
    user_id_b: int,
) -> list[str]:
    games_a = list_games_from_state(state, user_id_a)
    games_b = list_games_from_state(state, user_id_b)

    normalized_b = {normalize_game_name(name) for name in games_b}
    common: list[str] = []

    for name_a in games_a:
        if normalize_game_name(name_a) in normalized_b:
            common.append(name_a)

    return common


def set_timezone_in_state(state: dict[str, Any], user_id: int, tz: str) -> None:
    """Set or update the user's timezone string in `state`."""
    user_key = str(user_id)
    users = state["users"]

    if user_key not in users:
        users[user_key] = {"games": [], "timezone": tz}
    else:
        user = users[user_key]
        if "games" not in user:
            user["games"] = []
        user["timezone"] = tz


def get_timezone_from_state(state: dict[str, Any], user_id: int) -> str | None:
    user_key = str(user_id)
    users = state["users"]

    if user_key not in users:
        return None

    tz = users[user_key].get("timezone")
    if isinstance(tz, str) and tz:
        return tz

    return None


def set_day_availability_in_state(
    state: dict[str, Any],
    user_id: int,
    day: str,
    start: str | None,
    end: str | None,
) -> None:
    """
    Set or clear availability for a single weekday in the user's local time.

    - `day` is one of: "mon", "tue", "wed", "thu", "fri", "sat", "sun".
    - If `start` or `end` is falsy (None or ""), the day's availability is cleared.
    - Otherwise, availability[day] is set to a single interval: [{"start": start, "end": end}].
    """
    user_key = str(user_id)
    users = state["users"]

    if user_key not in users:
        users[user_key] = {
            "games": [],
            "availability": _empty_availability(),
        }

    user = users[user_key]

    if "availability" not in user or not isinstance(user["availability"], dict):
        user["availability"] = _empty_availability()

    availability = user["availability"]

    for d in DAY_KEYS:
        if d not in availability:
            availability[d] = []

    if not start or not end:
        availability[day] = []
    else:
        availability[day] = [{"start": start, "end": end}]


def get_availability_from_state(
    state: dict[str, Any],
    user_id: int,
) -> dict[str, list[dict[str, str]]]:
    """
    Return the user's availability dict, normalized to have all 7 days.

    The returned structure is a copy; mutating it will not change `state`.
    """
    user_key = str(user_id)
    users = state["users"]

    if user_key not in users:
        return _empty_availability()

    availability = users[user_key].get("availability")

    if not isinstance(availability, dict):
        return _empty_availability()

    result = _empty_availability()
    for day in DAY_KEYS:
        if day in availability:
            result[day] = list(availability[day])

    return result


def format_user_availability(state: dict[str, Any], user_id: int) -> str:
    """Return a human-readable weekly availability summary for this user."""
    tz = get_timezone_from_state(state, user_id)
    lines: list[str] = []

    if tz:
        lines.append(f"timezone: {tz}")
    else:
        lines.append("timezone: not set")

    availability = get_availability_from_state(state, user_id)

    for day in DAY_KEYS:
        slots = availability[day]
        if not slots:
            lines.append(f"{day}: none")
        else:
            slot = slots[0]
            lines.append(f"{day}: {slot['start']}-{slot['end']}")

    return "\n".join(lines)


def is_user_available_now(
    state: dict[str, Any],
    user_id: int,
    now_utc: datetime,
) -> bool:
    """Check if a user is available right now based on their timezone and availability."""
    tz_name = get_timezone_from_state(state, user_id)
    if not tz_name:
        return False

    try:
        tz = ZoneInfo(tz_name)
    except (KeyError, ValueError):
        return False

    local_now = now_utc.astimezone(tz)
    day_key = DAY_KEYS[local_now.weekday()]  # weekday() 0=Mon matches DAY_KEYS[0]="mon"

    availability = get_availability_from_state(state, user_id)
    slots = availability[day_key]

    local_time_str = local_now.strftime("%H:%M")
    for slot in slots:
        if slot["start"] <= local_time_str < slot["end"]:
            return True

    return False


def find_ready_players(
    state: dict[str, Any],
    invoker_id: int,
    now_utc: datetime,
    game_filter: str | None = None,
) -> list[tuple[int, list[str]]]:
    """
    Find users who are available now and share games with the invoker.

    Returns a list of (user_id, [common_game_names]) sorted by user_id.
    If game_filter is provided, only matches users who share that specific game.
    """
    results: list[tuple[int, list[str]]] = []

    for user_key in state["users"]:
        other_id = int(user_key)
        if other_id == invoker_id:
            continue

        if not is_user_available_now(state, other_id, now_utc):
            continue

        common = get_common_games(state, invoker_id, other_id)
        if not common:
            continue

        if game_filter:
            norm_filter = normalize_game_name(game_filter)
            common = [g for g in common if normalize_game_name(g) == norm_filter]
            if not common:
                continue

        results.append((other_id, common))

    results.sort(key=lambda x: x[0])
    return results
