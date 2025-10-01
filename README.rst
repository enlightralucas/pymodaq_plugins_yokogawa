pymodaq_plugins_yokogawa
#########################

PyMoDAQ plugin for Yokogawa instruments

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_yokogawa.svg
   :target: https://pypi.org/project/pymodaq_plugins_yokogawa/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status


This plugin provides PyMoDAQ interfaces for Yokogawa instruments using the PyMeasure library.


Authors
=======

* Lucas Braud (lucas.braud@enlightra.com)


Instruments
===========

Below is the list of instruments included in this plugin

Viewer1D
++++++++

* **AQ6370 Series**: Yokogawa AQ6370 series Optical Spectrum Analyzers (OSA)

  - Supported models: AQ6370C, AQ6370D, AQ6370E, AQ6373, AQ6373B, AQ6375, AQ6375B
  - Communication: VISA (GPIB, USB, Ethernet)
  - 1D viewer for spectral data (wavelength vs power)


Installation instructions
=========================

**Requirements:**

* PyMoDAQ >= 5.0.0
* PyMeasure >= 0.11.0
* PyVISA >= 1.11.0
* Operating system: Windows, Linux, macOS
* NI-VISA or PyVISA-py backend for instrument communication

**Installation:**

.. code-block:: bash

   pip install pymodaq_plugins_yokogawa

**VISA Backend:**

You need a VISA backend to communicate with the instruments:

* NI-VISA (recommended): Download from National Instruments website
* PyVISA-py (pure Python alternative): ``pip install pyvisa-py``

**Instrument Connection:**

* **GPIB**: Requires GPIB interface hardware
* **USB**: Direct USB connection
* **Ethernet**: TCP/IP connection (default port: 10001)
