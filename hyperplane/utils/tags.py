# tags.py
#
# Copyright 2023 kramo
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

from hyperplane import shared


def add_tags(*tags: str) -> None:
    """
    Adds new tags and updates the list of tags.

    Assumes that tags passed as arguments are valid.
    """
    for tag in tags:
        shared.tags.append(tag)
    update_tags()


def remove_tags(*tags: str) -> None:
    """Removes tags and updates the list of tags."""
    for tag in tags:
        if tag in shared.tags:
            shared.tags.remove(tag)
    update_tags()


def update_tags() -> None:
    """Updates the list of tags."""
    (shared.home / ".hyperplane").write_text("\n".join(shared.tags), encoding="utf-8")
    shared.postmaster.emit("tags-changed")