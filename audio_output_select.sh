#!/bin/bash

# A little helper script to select the default audio output on Linux systems
# running PulseAudio (either direct or through PipeWire; doesn't matter).
#
# Run it first without parameters, and it'll outout a numbered list of
# recognized outputs. Then run it again with the desired output number
# (or name, if you want), and this output will set as the default, and
# to full volume.

PACTL="$(which pactl 2>/dev/null)"
if [ -z "$PACTL" ] ; then
    echo "FATAL: pactl is not installed." >&2
    echo "If this is a Debian system, please run"
    echo "    sudo apt install pulseaudio-utils"
    exit 1
fi

if [ -z "$1" ] ; then
    echo "Current default audio output:"
    echo "    $($PACTL get-default-sink)"
    echo "Available audio outputs:"
    LANG=C $PACTL list sinks | grep Name | cut -d: -f2 | nl
    echo "Run '$(basename "$0") <NUMBER>' to set an output as default at 100% volume."
    exit 0
fi

if grep -E '^[1-9][0-9]*$' <<<"$1" >&/dev/null ; then
    SINK="$(LANG=C $PACTL list sinks | grep Name | cut -d: -f2 | sed "$1!d" | xargs)"
else
    SINK="$1"
fi
if [ -z "$SINK" ] ; then
    echo "FATAL: invalid audio device" >&2
    exit 1
fi
echo "Setting default audio output to device:"
echo "    $SINK"

set -ex
$PACTL set-default-sink "$SINK"
$PACTL set-sink-volume "$SINK" 100%
