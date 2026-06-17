"""
Name-normalization helpers shared across the website app.

The primary use is producing a stable, accent-folded key for a person's
name so that records that *would* collide on ``Person.url_name`` can be
detected and clustered. ``Person.save()`` derives ``url_name`` through these
helpers (via ``build_unique_url_name``), so the model, the duplicate-people
data-health check, and the ``recompute_url_names`` command all agree on what
"the same name" means.
"""

import re
import unicodedata


def _ascii_fold(text):
    """
    Fold accented Latin characters to their ASCII base via Unicode NFKD
    decomposition (e.g. ``á`` -> ``a``, ``ç`` -> ``c``, ``ñ`` -> ``n``), then
    drop the combining marks.

    This replaces an earlier hand-maintained accent map that only covered
    grave/circumflex/tilde vowels — it silently *dropped* acute accents and
    the cedilla, mangling url_names (``Cláudio`` -> ``cludio``) and hiding
    accented-name duplicates from the dedup check. NFKD handles the whole Latin
    range generically, so the map no longer has to be kept in sync by hand.
    """
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )


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
        >>> normalize_person_name('Cláudio', 'Silva')
        'claudiosilva'
    """
    cleaned = _ascii_fold(f"{first_name or ''}{last_name or ''}".lower())
    return re.sub('[^a-z]', '', cleaned)


def build_unique_url_name(first_name, middle_name, last_name, is_taken):
    """
    Derive a unique ``url_name`` for a person, preferring readable URLs.

    Resolution order:
      1. The bare key ``normalize_person_name(first, last)`` (e.g. ``jasminezhang``)
         if it isn't already taken.
      2. A **middle-initial differentiator** ``first + middle_initial + last``
         (e.g. ``jasminexzhang``) when a middle name is present and that form is
         free — giving namesakes a stable, human-readable URL (issue #1206/#1275).
      3. A **numeric suffix** fallback (``jasminezhang2``, ``jasminezhang3`` …) —
         the historical behavior, used when there's no usable middle initial or
         the middle-initial form is itself taken.

    ``is_taken`` is a callable ``str -> bool`` that reports whether a candidate
    ``url_name`` is already in use. The caller defines its semantics: when
    re-deriving for an existing row it should exclude that row's own pk (mirroring
    the ``.exclude(pk=self.pk)`` check in ``Person.save()``); when assigning in a
    batch it should consult the names already handed out this pass.

    The result is always non-empty and lowercase alpha (plus an optional trailing
    number), matching what ``Person.save()`` would store.

    Example:
        >>> taken = {'jasminezhang'}.__contains__
        >>> build_unique_url_name('Jasmine', 'Xin', 'Zhang', taken)
        'jasminexzhang'
        >>> build_unique_url_name('Jasmine', '', 'Zhang', taken)
        'jasminezhang2'
    """
    base = normalize_person_name(first_name, last_name)
    if not is_taken(base):
        return base

    # Middle-initial differentiator: fold the first alpha char of the middle name
    # the same way url_name derivation folds accents, then drop anything non-alpha.
    middle = (middle_name or '').strip()
    if middle:
        initial = re.sub('[^a-z]', '', _ascii_fold(middle[0].lower()))
        if initial:
            first_key = normalize_person_name(first_name, '')
            last_key = normalize_person_name('', last_name)
            candidate = f"{first_key}{initial}{last_key}"
            if candidate != base and not is_taken(candidate):
                return candidate

    # Numeric-suffix fallback (matches the legacy Person.save() collision loop).
    counter = 2
    while is_taken(f"{base}{counter}"):
        counter += 1
    return f"{base}{counter}"


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
