AFFILIATIONS = {'Family Lineage': 'LINEAGE_MEMBER', 'Married Into Family': 'MARRIED_IN'}


def affiliation_label(value):
    return next((label for label, key in AFFILIATIONS.items() if key == value), str(value or 'Not recorded'))


def ordinal(position):
    if not isinstance(position, int) or isinstance(position, bool) or position < 1:
        raise ValueError('Birth order must be a positive whole number.')
    suffix = 'th' if 10 <= position % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(position % 10, 'th')
    return f'{position}{suffix} Child'


def birth_label(position, total):
    label = 'Only child' if total == 1 else 'Firstborn' if position == 1 else 'Last-born' if position == total else ''
    return ordinal(position) + (' - ' + label if label else '')
