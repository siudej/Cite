#!/usr/bin/env python
"""
Main application script.

Starts terminal version if any parameters or stdin input present.
Otherwise starts GUI.
"""
from __future__ import division
import sys


if len(sys.argv) > 1 or not sys.stdin.isatty():
    # start terminal
    from citeTerminal import startTerminal
    startTerminal()
else:
    # start GUI
    from citeWindow import startApp
    startApp()
