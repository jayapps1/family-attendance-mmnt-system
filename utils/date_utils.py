from datetime import date


def age_on(born: date | None, on: date | None = None) -> int | None:
    if born is None:
        return None
    on = on or date.today()
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))
