from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    # Fallback para ambientes sem base tzdata instalada.
    SAO_PAULO_TZ = timezone(timedelta(hours=-3), name="America/Sao_Paulo")


def now_sao_paulo() -> datetime:
    return datetime.now(tz=SAO_PAULO_TZ)
