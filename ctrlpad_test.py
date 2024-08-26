#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import ctrlpad
from ctrlpad.controls import bind, ControlEnvironment, GridLayout, Label, Button
from ctrlpad.clock import Clock
from ctrlpad.mpd import MPDClient, MPDControl
from ctrlpad.crossbar import Crossbar


def init_app(env: ControlEnvironment):

    page = env.toplevel.add_page(GridLayout(16,8), "General", label="WELCOME")
    page.pack(8,8, Clock())
    mpd = page.pack(8,3, MPDControl(MPDClient()))
    page.locate(8,3)
    page.pack(2,2, Button("Play BGM")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("calm", "semicalm", "trance"))
    page.pack(2,2, Button("Play Demo-vibes")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("_mixes"))
    page.pack(2,2, Button("Play Old-school")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("retro"))
    page.pack(2,2, Button("Play Single Banger")).cmd = lambda e,b: \
        mpd.send_commands(*MPDClient.shuffle_folders("banger", single=True))

    # ---------------------------------------------------------------------

    page = env.toplevel.add_page(GridLayout(16,8), "Examples", label="TESTING")
    page.put(0,0, 12,1, Label("COLORFUL BUTTONS", valign=1, bar=3))
    for i, name in enumerate("RED YELLOW GREEN CYAN BLUE MAGENTA".split()):
        hue, sat = 30 + i * 60, 0.1
        page.put(i*2,1, 2,2, Button(name, hue=hue, sat=sat, toggle=True))
        page.put(i*2,3, 1,1, Button(name[0], hue=hue, sat=sat, state='disabled'))

    page.locate(0,5)
    panic = page.pack(2,2, Button("PANIC BUTTON", state='disabled', hue=20, sat=.2))
    @bind(panic)
    def cmd(e,b):
        mpd.mpd.send_commands('stop')
    page.pack(2,2, Button("CLICK")).cmd = lambda e,b: setattr(panic, 'state', None)
    page.pack(2,2, Button("TOGGLE", toggle=True)).cmd = lambda e,b: print("toggle state:", b.active)

    page.locate(0,7)
    page.pack(1,1, Button("\u23ee", font="symbol"))  # prev
    page.pack(1,1, Button("\u23ea", font="symbol"))  # rewind
    page.pack(1,1, Button("\u23f5", font="symbol"))  # play
    page.pack(1,1, Button("\u23f8", font="symbol"))  # pause
    page.pack(1,1, Button("\u23f9", font="symbol"))  # stop
    page.pack(1,1, Button("\u23cf", font="symbol"))  # eject
    page.pack(1,1, Button("\u23e9", font="symbol"))  # f.fwd
    page.pack(1,1, Button("\u23ed", font="symbol"))  # next
    page.pack(8,1, Label("<- non-functional, illustrative only"))

    # ---------------------------------------------------------------------

    xbar = Crossbar(8, 8)
    # https://keyj.emphy.de/photos/deadline2023/dl23_videosetup.png
    page = xbar.add_ui_page(env.toplevel, input_names={
        '1': "ATEM OUT 2",
        '2': "Stream Output",
        '3': "FOH HDMI",
        '4': "Old school",
        '5': "Compo1\n",
        '6': "Compo2\n",
        '7': "Screens\n",
        '8': "n/c\n"
    }, output_names=[
        "ATEM IN 1", "ATEM IN 2", "ATEM IN 3", "Stream Team",
        "Compo1 Monitor", "Compo2 Monitor",
        "Main Screen", "Bar Screen"
    ], input_format="\u203a\u2039", output_format="\u2039\u203a")
    page.pack(2,2, Button("Default Monitors")).cmd = lambda e,b: \
        xbar.tie((5,5), (6,6))
    page.pack(2,2, Button("Default ATEM")).cmd = lambda e,b: \
        xbar.tie((5,1),(6,2),(7,3))
    page.pack(2,2, Button("ATEM to Screen")).cmd = lambda e,b: \
        xbar.tie(('A',4,7,8))


if __name__ == "__main__":
    ctrlpad.run_application("ControlPad Test App", init_app)
