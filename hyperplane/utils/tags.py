# tags.py
#
# Copyright 2023-2024 kramo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Miscellaneous utilities for working with tags."""
from os import PathLike
from pathlib import Path

from gi.repository import Gtk

from hyperplane import shared


def update_tags(change: Gtk.FilterChange = Gtk.FilterChange.DIFFERENT) -> None:
    """
    Writes the list of tags from `shared.tags` to disk and notifies widgets.

    `change` indicates whether tags were
    added (more strict), removed (less strict) or just reordered (different).
    """
    (shared.home_path / ".hyperplane").write_text(
        "\n".join(shared.tags), encoding="utf-8"
    )

    shared.postmaster.emit("tags-changed", change)


def path_represents_tags(path: PathLike | str) -> bool:
    """Checks whether a given `path` represents tags or not."""
    path = Path(path)

    if path == shared.home_path:
        return False

    if not path.is_relative_to(shared.home_path):
        return False

    return all(part in shared.tags for part in path.relative_to(shared.home_path).parts)


def add_tags(*tags: str) -> None:
    """
    Adds new tags and updates the list of tags.

    Assumes that tags passed as arguments are valid.
    """
    for tag in tags:
        shared.tags.append(tag)
    update_tags(Gtk.FilterChange.MORE_STRICT)


def remove_tags(*tags: str) -> None:
    """Removes tags and updates the list of tags."""
    for tag in tags:
        if tag in shared.tags:
            shared.tags.remove(tag)
    update_tags(Gtk.FilterChange.LESS_STRICT)


def move_tag(tag: str, up: bool) -> None:
    """Moves a tag up or down by one in the list of tags."""

    # Moving up

    if up:
        if shared.tags[0] == tag:
            return

        index = shared.tags.index(tag)

        shared.tags[index], shared.tags[index - 1] = (
            shared.tags[index - 1],
            shared.tags[index],
        )
        update_tags()
        return

    # Moving down

    if shared.tags[-1] == tag:
        return

    index = shared.tags.index(tag)

    shared.tags[index], shared.tags[index + 1] = (
        shared.tags[index + 1],
        shared.tags[index],
    )

    update_tags()
