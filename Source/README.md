# ZEROFIELD coil system control software
Demo-level software for ZEROFIELD coil system.

# User interface
Simple controls: 

Each channel has fields for field offset, sine amplitude, frequency and phase offset. Read ZEROFIELD IFU.

# Installation
Requires a Python environment with bitarray, PyQt5, numpy, pyserial. 

# Building distribution 

Requires pyinstaller in order to package application. Run 

pyinstaller coilcontrol.spec

Note: In order to avoid massive installation size, install numpy via pip (not conda).

# Known issues

- Generated sine frequencies are not exactly what is asked

# Warranty

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
