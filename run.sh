#!/bin/bash
#
# Helper script that runs a ctrlpad application in the background.
# Features:
#   - quits a running instance, if there is any
#   - can start MPD (Music Player Daemon), if configured and not already running
#   - redirects all output to run.log
# Configuration is done in the file run.conf; look into run.conf.example
# for possible settings.

# "use strict"
set -eu

# use this script's directory as working directory
cd "$(dirname "$0")"

# load run.conf or run.conf.example
if [ -r run.conf ] ; then
    source run.conf
elif [ -r run.conf.example ] ; then
    source run.conf.example
fi

# check for required parameters
if [ -z "${APP:-}" ] ; then
    echo "FATAL: \$APP not defined in run.conf" >&2
    exit 2
fi

# kill running instance
if [ -r run.pid ] ; then
    oldpid="$(cat run.pid)"
    if grep -a python3 "/proc/$oldpid/cmdline" >/dev/null 2>/dev/null ; then
        echo -n "Killing running instance at PID $oldpid ... "
        kill -15 "$oldpid"
        sleep 1
        if [ -d "/proc/$oldpid" ] ; then
            echo -n "with extreme prejudice ... "
            kill -9 "$oldpid"
            sleep 1
            if [ -d "/proc/$oldpid" ] ; then
                echo "FAILED."
                echo "FATAL: process with PID $oldpid won't die" >&2
                exit 1
            fi
        fi
        echo "OK."
        rm -f run.pid
    fi
fi

# run MPD if needed and not already running
if [ -n "${MPD_PIDFILE:-}" -a -n "${MPD_CONFIG:-}" ] ; then
    if grep -a mpd "/proc/$(cat "$MPD_PIDFILE")/cmdline" >/dev/null 2>/dev/null ; then
        echo "MPD is already running."
    else
        echo -n "Starting MPD ... "
        mpd "$MPD_CONFIG" || MID_PIDFILE=xxxdoesntexistxxx
        sleep 1
        if [ ! -r "$MPD_PIDFILE" ] ; then
            echo "FAILED."
            echo "ERROR: MPD startup seems to have failed" >&2
        else
            echo "OK."
        fi
    fi
fi

# set display, if so desired
if [ -n "${X11_DISPLAY:-}" ] ; then
    export DISPLAY="$X11_DISPLAY"
fi

# run new instance
echo -n "Starting new instance ... "
echo >>run.log
echo "====================================================" >>run.log
echo "new run starting at $(date)" >>run.log
echo "====================================================" >>run.log
echo >>run.log
echo "command line: python3 \"./$APP\" -p run.pid ${ARGS:-}" >>run.log
nohup python3 "./$APP" -p run.pid ${ARGS:-} 2>&1 </dev/null >>run.log & newpid=$!
sleep 1
if [ ! -d "/proc/$newpid" ] ; then
    echo "FAILED."
    echo "FATAL: new instance died quickly, see run.log for details" >&2
    exit 1
else
    echo "OK."
fi
