#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import ctrlpad
from ctrlpad import controls, clock, crossbar
from ctrlpad.mpd import MPDClient, MPDControl
from ctrlpad.controls import ControlEnvironment, GridLayout, Label, Button
from ctrlpad.util import WebRequest


def init_app(env: ControlEnvironment):
    # instantiate video matrix controller
    xbar = crossbar.ExtronCrossbar("10.0.1.88", num_inputs=8, num_outputs=8)
    #xbar = crossbar.GefenCrossbar("/dev/ttyUSB0")
    def add_xbar_button(page, label, *ties):
        page.pack(2,2, Button(label)).cmd = lambda e,b: xbar.tie(*ties)

    # create first page with a huge studio clock and an MPD controller
    page = env.toplevel.add_page(GridLayout(16,8), "Home")
    page.pack(8,8, clock.Clock())
    mpd = page.pack(8,3, MPDControl(MPDClient()))

    # a few buttons for playing pre-defined playlists using MPD
    page.locate(8,3)
    page.pack(2,2, Button("Play BGM")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("BGM", "calm", "semicalm", "trance"))
    page.pack(2,2, Button("Play Demo-vibes")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("_mixes"))
    page.pack(2,2, Button("Play Old-school")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("retro"))
    page.pack(2,2, Button("Play Single Banger")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("banger", single=True))

    # a set of fade buttons for MPD
    page.locate(14,6)
    page.pack(1,1, mpd.mpd.create_fade_button(1.0, "1s"))
    page.pack(1,1, mpd.mpd.create_fade_button(2.0, "2s"))
    page.newline()
    page.pack(1,1, mpd.mpd.create_fade_button(5.0, "5s"))
    page.pack(1,1, mpd.mpd.create_fade_button(10.0, "10s"))
    page.add_group_label("FADE")

    # ---------------------------------------------------------------------

    # create compo page
    page = env.toplevel.add_page(GridLayout(16,9), "Compo")

    page.locate(0,1)
    add_xbar_button(page, "Compo1 Direct",    (8,6), (1,5,7,8))
    add_xbar_button(page, "Compo2 Direct",    (8,6), (2,5,7,8))
    add_xbar_button(page, "Slides Direct",    (8,6), (3,5,7,8))
    add_xbar_button(page, "Oldschool Direct", (8,6), (4,5,7,8))
    page.add_group_label("50Hz")
    page.put(0,3, 8,1, Label("Set ATEM to IN 5 before going 50 Hz!"))
    page.put(0,4, 8,1, Label("Only switch Hz while Slides are shown!"))
    page.locate(9,1)
    add_xbar_button(page, "Back to ATEM", (1,3), (2,4), (3,5), (8,6,7,8))
    page.add_group_label("60Hz")

    # ---------------------------------------------------------------------

    # crossbar controller UI page

    page = xbar.add_ui_page(env.toplevel, input_names=[
        "Compo1",
        "Compo2",
        "Slides",
        "Old school",
        "FOH HDMI",
        "Stream Output",
        "n/c",
        "ATEM OUT",
    ], output_names=[
        "Compo1 Monitor",
        "Compo2 Monitor",
        "ATEM IN 3",
        "ATEM IN 4",
        "ATEM IN 5",
        "Stream Team",
        "Main Screen",
        "Bar Screen",
    ], input_format="\u203a\u2039", output_format="\u2039\u203a")

    # there's still a bit of space left in the lower-left end of the page,
    # so put a few potentially useful macros there
    add_xbar_button(page, "Default Monitors", (1,1), (2,2))
    add_xbar_button(page, "Default ATEM", (1,3),(2,4),(3,5))
    add_xbar_button(page, "ATEM to Screens", (8,6,7,8))
    page.add_group_label("MACROS")


if __name__ == "__main__":
    ctrlpad.run_application("Deadline 2024 Control Panel", init_app)
