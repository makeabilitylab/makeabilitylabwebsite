"""
Name-normalization helpers shared across the website app.

The primary use is producing a stable, accent-folded key for a person's
name so that records that *would* collide on ``Person.url_name`` can be
detected and clustered. The logic mirrors the url_name derivation in
``Person.save()`` (website/models/person.py) so callers — e.g. the
duplicate-people data-health check and a future ``recompute_url_names``
command — agree on what "the same name" means.
"""

import re

# Common accented characters mapped to ASCII. Kept in sync with the map in
# website/models/person.py used by Person.save() for url_name derivation.
SPECIAL_CHARS = {
    'ã': 'a', 'à': 'a', 'â': 'a',
    'é': 'e', 'è': 'e', 'ê': 'e',
    'ñ': 'n', 'ń': 'n',
    'ö': 'o', 'ô': 'o',
    'û': 'u', 'ü': 'u', 'ù': 'u',
}

# Substrings identifying the auto-assigned "Star Wars" placeholder images
# (see get_path_to_random_starwars_image / get_upload_to_for_person_easter_egg).
# NOTE: only the *easter_egg* (hover) field retains a "_starwars_" marker in its
# stored filename; the headshot ``image`` default is saved under the person's
# own name, so a default headshot is NOT reliably detectable by path. Treat
# is_default_person_image() as a best-effort hint, not a guarantee.
_STARWARS_MARKERS = ('StarWarsFiguresFullSquare', '_starwars_')


def normalize_person_name(first_name, last_name):
    """
    Return the accent-folded, lowercased, alpha-only key for a name.

    This reproduces the cleaning that ``Person.save()`` applies when deriving
    ``url_name`` (minus the numeric-suffix collision loop), so two people share
    a key exactly when their bare ``url_name`` would collide.

    Example:
        >>> normalize_person_name('Jon', 'Froehlich')
        'jonfroehlich'
        >>> normalize_person_name('Renée', "O'Brien")
        'reneeobrien'
    """
    cleaned = f"{first_name or ''}{last_name or ''}".lower()
    for c in cleaned:
        if re.search('[^a-zA-Z]', c) and c in SPECIAL_CHARS:
            cleaned = cleaned.replace(c, SPECIAL_CHARS[c])
    return re.sub('[^a-zA-Z]', '', cleaned)


def is_default_person_image(image_field):
    """
    Return True if a Person image field looks like an auto-assigned default
    (random "Star Wars" placeholder) rather than a real upload.

    ``Person.save()`` assigns a random Star Wars image when none is set, so
    "has an image" is meaningless on its own. Accepts a Django file field
    (``person.image`` / ``person.easter_egg``) or any object with a ``.name``;
    falsy/empty fields count as default.

    Caveat: reliable only for the *easter_egg* field (whose default keeps a
    ``_starwars_`` marker). A default *headshot* is stored under the person's
    name and cannot be told apart from a real upload by path alone.
    """
    name = getattr(image_field, 'name', None) or ''
    if not name:
        return True
    return any(marker in name for marker in _STARWARS_MARKERS)
