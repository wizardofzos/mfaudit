"""Helpers for correlating real data sets with effective RACF profiles."""

import re
from collections import defaultdict


def _qualifier_regex(qualifier):
    parts = []
    index = 0
    while index < len(qualifier):
        if qualifier[index:index + 2] == "**":
            parts.append(".*")
            index += 2
        elif qualifier[index] == "*":
            parts.append("[^.]*")
            index += 1
        elif qualifier[index] == "%":
            parts.append("[^.]")
            index += 1
        else:
            parts.append(re.escape(qualifier[index]))
            index += 1
    return "".join(parts)


def dataset_profile_regex(profile):
    """Translate a RACF DATASET generic profile into a compiled regex."""
    qualifiers = str(profile).strip().upper().split(".")
    expression = ""
    for index, qualifier in enumerate(qualifiers):
        if qualifier == "**":
            expression += ".*" if index == 0 else r"(?:\.[^.]+)*"
        else:
            if index:
                expression += r"\."
            expression += _qualifier_regex(qualifier)
    return re.compile(f"^{expression}$")


def profile_specificity(profile):
    """Return a stable best-match score compatible with RACF generic intent."""
    score = 0
    for qualifier in str(profile).split("."):
        index = 0
        while index < len(qualifier):
            if qualifier[index:index + 2] == "**":
                score += 1
                index += 2
            elif qualifier[index] == "*":
                score += 2
                index += 1
            elif qualifier[index] == "%":
                score += 3
                index += 1
            else:
                score += 4
                index += 1
    return score, len(str(profile).split(".")), len(str(profile))


class DatasetProfileIndex:
    """Index IRRDBU00 DATASET profiles for repeated effective-profile lookup."""

    def __init__(self, profiles):
        self._discrete = defaultdict(list)
        self._generic = defaultdict(list)
        self._generic_wild_hlq = []

        for _, source in profiles.iterrows():
            row = source.to_dict()
            name = str(row.get("DSBD_NAME", "")).strip().upper()
            if not name:
                continue
            row["DSBD_NAME"] = name
            generic = str(row.get("DSBD_GENERIC", "NO")).strip().upper() == "YES"
            if not generic:
                self._discrete[name].append(row)
                continue

            entry = (
                dataset_profile_regex(name),
                profile_specificity(name),
                row,
            )
            hlq = name.split(".", 1)[0]
            if any(char in hlq for char in "*%"):
                self._generic_wild_hlq.append(entry)
            else:
                self._generic[hlq].append(entry)

    def match(self, dataset_name, volume=""):
        """Return the effective profile as a dict, or None when uncovered."""
        name = str(dataset_name).strip().upper()
        volume = str(volume).strip().upper()

        discrete = self._discrete.get(name, [])
        if discrete:
            exact_volume = [
                row for row in discrete
                if str(row.get("DSBD_VOL", "")).strip().upper() == volume
            ]
            if exact_volume:
                return exact_volume[0]
            blank_volume = [
                row for row in discrete
                if not str(row.get("DSBD_VOL", "")).strip()
            ]
            if blank_volume:
                return blank_volume[0]

        hlq = name.split(".", 1)[0]
        matches = []
        for regex, specificity, row in (
            self._generic.get(hlq, []) + self._generic_wild_hlq
        ):
            if regex.fullmatch(name):
                matches.append((specificity, row))
        return max(matches, key=lambda item: item[0])[1] if matches else None
