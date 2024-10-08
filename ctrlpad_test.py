#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import ctrlpad
from ctrlpad import controls, clock, crossbar
from ctrlpad.mpd import MPDClient, MPDControl
from ctrlpad.controls import ControlEnvironment, GridLayout, Label, Button
from ctrlpad.util import WebRequest


def init_app(env: ControlEnvironment):
    # default scale is good for ~16x9 cells; for larger/smaller grids, change this
    env.set_global_scale(1.0)

    # create first page with a huge studio clock and an MPD controller
    page = env.toplevel.add_page(GridLayout(16,8), "General", label="WELCOME")
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

    # a set of shuffle buttons for MPD
    page.locate(14,6)
    page.pack(1,1, mpd.mpd.create_fade_button(1.0, "1s"))
    page.pack(1,1, mpd.mpd.create_fade_button(2.0, "2s"))
    page.newline()
    page.pack(1,1, mpd.mpd.create_fade_button(5.0, "5s"))
    page.pack(1,1, mpd.mpd.create_fade_button(10.0, "10s"))
    page.add_group_label("FADE")

    # WebRequest example
    page.locate(8,6)
    weather_button = page.pack(5,1, Button("How's the weather in Berlin?"))
    page.newline()
    weather_info = page.pack(5,1, Label("click the button above"))
    @controls.bind(weather_button)
    def cmd(*_):
        web = WebRequest("https://api.open-meteo.com/v1/forecast", get_data={
            'latitude': 52.5373,
            'longitude': 15.53,
            'current': 'temperature_2m'
        })
        if web.response_json:
            weather_info.set_text(f"{web.response_json['current']['temperature_2m']:.1f}{web.response_json['current_units']['temperature_2m']}")
        else:
            weather_info.set_text("weather request failed :(")

    # ---------------------------------------------------------------------

    # create test page
    page = env.toplevel.add_page(GridLayout(16,8), "Examples", label="TESTING")

    # buttons in various colors, enabled and disabled
    page.locate(0,1)
    for i, name in enumerate("RED YELLOW GREEN CYAN BLUE MAGENTA".split()):
        hue, sat = 30 + i * 60, 0.1
        page.put(i*2,3, 1,1, Button(name[0], hue=hue, sat=sat, state='disabled'))
        page.put(i*2,1, 2,2, Button(name, hue=hue, sat=sat, toggle=True))
    page.add_group_label("COLORFUL BUTTONS")

    # a 3x3 group of smaller buttons
    page.locate(13,1)
    for row in range(3):
        for col in range(3):
            page.pack(1,1, Button(chr(row+65) + str(col+1)))
        page.newline()
    page.add_group_label("GROUP")

    # basic button examples
    page.locate(0,5)
    panic = page.pack(2,2, Button("PANIC BUTTON", state='disabled', hue=20, sat=.2))
    @controls.bind(panic)
    def cmd(e,b):
        mpd.mpd.send_commands('stop')
    page.pack(2,2, Button("CLICK")).cmd = lambda e,b: setattr(panic, 'state', None)
    page.pack(2,2, Button("TOGGLE", toggle=True)).cmd = lambda e,b: print("toggle state:", b.active)

    # examples of a few potentially useful symbols
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

    # crossbar controller, including UI

    xbar = crossbar.Crossbar(8, 8)
    #xbar = crossbar.ExtronCrossbar("localhost", 2323)
    #xbar = crossbar.GefenCrossbar("COM1:")

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

    # there's still a bit of space left in the lower-left end of the page,
    # so put a few potentially useful macros there
    page.pack(2,2, Button("Default Monitors")).cmd = lambda e,b: \
        xbar.tie((5,5), (6,6))
    page.pack(2,2, Button("Default ATEM")).cmd = lambda e,b: \
        xbar.tie((5,1),(6,2),(7,3))
    page.pack(2,2, Button("ATEM to Screen")).cmd = lambda e,b: \
        xbar.tie(('A',4,7,8))
    page.add_group_label("MACROS")


if __name__ == "__main__":
    ctrlpad.run_application("ControlPad Test App", init_app)
