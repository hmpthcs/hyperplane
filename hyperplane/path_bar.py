# path_bar.py
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

"""The path bar in a HypWindow."""
import logging
from os import sep
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import unquote, urlparse

from gi.repository import Gdk, Gio, GLib, Gtk

from hyperplane import shared
from hyperplane.path_segment import HypPathSegment


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/path-bar.ui")
class HypPathBar(Gtk.ScrolledWindow):
    """The path bar in a HypWindow."""

    __gtype_name__ = "HypPathBar"

    viewport: Gtk.Viewport = Gtk.Template.Child()
    segments_box: Gtk.Box = Gtk.Template.Child()

    segments: list
    separators: dict
    tags: bool  # Whether the path bar represents tags or a file

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.segments = []
        self.separators = {}
        self.tags = False

        # Left-click
        self.segment_clicked = False
        left_click = Gtk.GestureClick(button=Gdk.BUTTON_PRIMARY)
        left_click.connect(
            "pressed", lambda *_: GLib.timeout_add(100, self.__left_click)
        )
        self.add_controller(left_click)

    def remove(self, n: int) -> None:
        """Removes `n` number of segments form self, animating them."""
        for _index in range(n):
            child = self.segments.pop()
            child.set_reveal_child(False)
            GLib.timeout_add(
                child.get_transition_duration(),
                self.__remove_child,
                self.segments_box,
                child,
            )

            if not (separator := self.separators[child]):
                return

            separator.set_reveal_child(False)
            GLib.timeout_add(
                separator.get_transition_duration(),
                self.__remove_child,
                self.segments_box,
                separator,
            )
            self.separators.pop(child)

        if self.tags:
            return

        try:
            self.segments[-1].active = True
            self.segments[-2].active = False
        except IndexError:
            return

    def append(
        self,
        label: str,
        icon_name: Optional[str] = None,
        uri: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> None:
        """
        Appends a HypPathSegment with `label` and `icon_name` to self.

        `uri` or `tag` will be opened when the segment is clicked.

        Adding an item is animated.
        """
        if self.segments:
            # Add a separator only if there is more than one item
            sep_label = Gtk.Label.new("+" if self.tags else "/")
            sep_label.add_css_class("heading" if self.tags else "dim-label")

            separator = Gtk.Revealer(
                child=sep_label, transition_type=Gtk.RevealerTransitionType.SLIDE_RIGHT
            )
            self.segments_box.append(separator)
            separator.set_reveal_child(True)
        else:
            separator = None

        segment = HypPathSegment(label, icon_name, uri, tag)
        self.segments_box.append(segment)

        segment.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        segment.set_reveal_child(True)

        self.separators[segment] = separator
        self.segments.append(segment)

        last_segment = self.segments[-1]

        GLib.timeout_add(
            last_segment.get_transition_duration(),
            self.viewport.scroll_to,
            last_segment,
        )

        if self.tags:
            return

        last_segment.active = True

        try:
            self.segments[-2].active = False
        except IndexError:
            return

    def purge(self) -> None:
        """Removes all segments from self, without animation."""
        while child := self.segments_box.get_first_child():
            self.segments_box.remove(child)

        self.segments = []
        self.separators = {}

    def update(self, gfile: Optional[Gio.File], tags: Optional[Iterable[str]]) -> None:
        """Updates the bar according to a new `gfile` or new `tags`."""
        if gfile:
            if self.tags:
                self.purge()

            self.tags = False

            uri = gfile.get_uri()
            parse = urlparse(uri)
            segments = []
            scheme_uri = f"{parse.scheme}://"

            # Do these automatically if shceme != "file"
            if parse.scheme == "file":
                base_uri = scheme_uri
            else:
                try:
                    file_info = Gio.File.new_for_uri(scheme_uri).query_info(
                        ",".join(
                            (
                                Gio.FILE_ATTRIBUTE_STANDARD_SYMBOLIC_ICON,
                                Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME,
                            )
                        ),
                        Gio.FileQueryInfoFlags.NONE,
                    )

                    base_name = file_info.get_display_name()
                    base_symbolic = file_info.get_symbolic_icon().get_names()[0]
                    base_uri = scheme_uri
                except GLib.Error:
                    # Try the mount if the scheme root fails
                    try:
                        mount = gfile.find_enclosing_mount()
                        mount_gfile = mount.get_default_location()

                        base_name = mount.get_name()
                        base_symbolic = mount.get_symbolic_icon().get_names()[0]
                        base_uri = mount_gfile.get_uri()
                    except GLib.Error as error:
                        base_name = None
                        base_symbolic = None
                        base_uri = None
                        logging.error(
                            'Cannot get information for location "%s": %s', uri, error
                        )

            parts = unquote(parse.path).split(sep)

            for index, part in enumerate(parts):
                if not part:
                    continue

                segments.append(
                    (part, "", f"{base_uri}{sep.join(parts[:index+1])}", None)
                )

            if (path := gfile.get_path()) and (
                (path := Path(path)) == shared.home_path
                or path.is_relative_to(shared.home_path)
            ):
                segments = segments[len(shared.home_path.parts) - 1 :]
                base_name = _("Home")
                base_symbolic = "user-home-symbolic"
                base_uri = shared.home.get_uri()
            elif parse.scheme == "file":
                # Not relative to home, so add a root segment
                base_name = ""
                base_symbolic = "drive-harddisk-symbolic"
                # Fall back to sep if the GFile doesn't have a path
                base_uri = Path(path.anchor if path else sep).as_uri()

            if base_uri:
                segments.insert(
                    0,
                    (
                        base_name,
                        base_symbolic,
                        base_uri,
                        None,
                    ),
                )

        elif tags:
            if not self.tags:
                self.purge()

            self.tags = True

            segments = tuple((tag, "", None, tag) for tag in tags)

        if (old_len := len(self.segments)) > (new_len := len(segments)):
            self.remove(old_len - new_len)

        append = False
        for index, new_segment in enumerate(segments):
            try:
                old_segment = self.segments[index]
            except IndexError:
                old_segment = None

            if (
                not append
                and old_segment
                and new_segment[2] == old_segment.uri
                and new_segment[3] == old_segment.tag
            ):
                continue

            if not append:
                self.remove(len(self.segments) - index)
                append = True

            self.append(*new_segment)

    def __remove_child(self, parent: Gtk.Box, child: Gtk.Widget) -> None:
        # This is so GTK doesn't freak out when the child isn't in the parent anymore
        if child.get_parent == parent:
            parent.remove(child)

    def __left_click(self, *_args: Any) -> None:
        # Do nothing if a segment has been clicked recently
        if self.segment_clicked:
            self.segment_clicked = False
            return

        self.get_root().show_path_entry()
