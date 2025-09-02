# SPDX-FileCopyrightText: 2025 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

import logging
import rtmidi
from typing import Sequence

__all__ = ['SendMIDI', 'USBMIDI', 'NoteOn', 'NoteOff']

USBMIDI = ("usb", "ch345")  # common device names of USB MIDI interfaces

def SendMIDI(port: int|str|Sequence[str] = 0, msg: Sequence[int]|bytes = [], silent: bool = False):
    """
    Send a MIDI message.
    - port:   MIDI Out port to use; numeric (0-based) or a string or list of
              strings to match the device names against
    - msg:    MIDI message to transmit
    - silent: don't log port ID lookup errors; just fail silently
    Note: This opens and closes the device every time, so it's not fast.
    """
    out = rtmidi.MidiOut()
    log = logging.getLogger("SendMIDI")
    if not isinstance(port, int):
        if isinstance(port, str):
            port = [port]
        port = [p.lower() for p in port]
        avail = out.get_ports()
        if not avail:
            if not silent: log.error("no MIDI ports found")
            return False
        idx = [i for i,a in enumerate(avail) if any((p in a.lower()) for p in port)]
        if not idx:
            if not silent: log.error(f"no matching MIDI port found")
            return False
        if len(idx) > 1:
            log.warning(f"multiple matching MIDI ports found, using the first match ('{avail[idx[0]]}')")
        port = idx[0]
    if not msg:
        return True
    try:
        out.open_port(port)
        out.send_message(msg)
        del out
        return True
    except rtmidi.RtMidiError as e:
        log.error(f"failed to send MIDI data - {e}")
        return False

_note_map = { "c":0, "c#":1, "db":1, "d":2, "d#":3, "eb":3, "e":4, "f":5, "f#":6, "gb":6, "g":7, "g#":8, "ab":8, "a":9, "a#":10, "bb":10, "hb":10, "b":11, "h":11 }
def _note_on_off(channel: int, note: int|str, velocity: int, _cmd: int):
    if isinstance(note, str):
        if (len(note) < 2) or not(note[-1].isdigit()):
            note = -1
        else:
            try:
                note = _note_map[note[:-1].rstrip('-').lower()] + 12 * (int(note[-1]) + 1)
            except KeyError:
                note = -1
        if not(0 <= note <= 127):
            raise ValueError(f"invalid note '{note}'")
    return [_cmd + min(max(channel, 1), 16) - 1, min(max(note, 0), 127), min(max(velocity, 0), 127)]

def NoteOn(channel: int = 1, note: int|str = 60, velocity: int = 112):
    """
    Generate a MIDI Note On command.
    - channel:  MIDI channel (1..16)
    - note:     MIDI note, numeric (0..127) or as a string (e.g. "C-4", "A#3")
    - velocity: MIDI velocity (0..127)
    """
    return _note_on_off(channel, note, velocity, 0x90)

def NoteOff(channel: int = 1, note: int|str = 60, velocity: int = 0):
    """
    Generate a MIDI Note Off command.
    - channel:  MIDI channel (1..16)
    - note:     MIDI note, numeric (0..127) or as a string (e.g. "C-4", "A#3")
    - velocity: MIDI velocity (0..127)
    """
    return _note_on_off(channel, note, velocity, 0x80)

if __name__ == "__main__":
    SendMIDI(port=("usb", "ch345"), msg=NoteOn(1, "C4"))
    SendMIDI(port=("usb", "ch345"), msg=NoteOff(1, "C4"))
