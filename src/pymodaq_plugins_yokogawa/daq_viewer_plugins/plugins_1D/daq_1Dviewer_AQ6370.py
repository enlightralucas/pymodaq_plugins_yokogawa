import numpy as np

from pymodaq_utils.utils import ThreadCommand
from pymodaq_data.data import DataToExport, Axis
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins

from pymeasure.adapters import VISAAdapter
from pymeasure.instruments.yokogawa import (
    AQ6370Series, AQ6370C, AQ6370D,
    AQ6373, AQ6373B, AQ6375, AQ6375B
)


class DAQ_1DViewer_AQ6370(DAQ_Viewer_base):
    """ PyMoDAQ plugin for Yokogawa AQ6370 series Optical Spectrum Analyzers.

    This plugin uses PyMeasure to communicate with Yokogawa AQ6370 series OSA instruments.

    Compatible instruments:
        * Yokogawa AQ6370C
        * Yokogawa AQ6370D
        * Yokogawa AQ6373
        * Yokogawa AQ6373B
        * Yokogawa AQ6375
        * Yokogawa AQ6375B

    Tested with:
        * PyMoDAQ 5.0+
        * PyMeasure Development Mode
        * Python 3.8+

    Installation requirements:
        * PyVISA or/and a VISA backend (NI-VISA or PyVISA-py)
        * VISA connection via GPIB, USB, or Ethernet

    Attributes:
    -----------
    controller: AQ6370Series
        PyMeasure instrument object for communication with the OSA
    """

    params = comon_parameters + [
        {'title': 'Instrument Model:', 'name': 'model', 'type': 'list',
         'limits': ['AQ6370C', 'AQ6370D', 'AQ6373', 'AQ6373B', 'AQ6375', 'AQ6375B'],
         'value': 'AQ6370C'},
        {'title': 'VISA Address:', 'name': 'visa_address', 'type': 'str',
         'value': 'TCPIP::192.168.1.112::10001::SOCKET'},
        {'title': 'Sweep Settings:', 'name': 'sweep_settings', 'type': 'group', 'children': [
            {'title': 'Center (nm):', 'name': 'center_wl', 'type': 'float',
             'value': 1549.365, 'step': 0.001, 'suffix': ' nm', 'decimals': 7},
            {'title': 'Span (nm):', 'name': 'span_wl', 'type': 'float',
             'value': 10, 'suffix': 'nm', 'decimals': 3},
            {'title': 'Resolution (nm):', 'name': 'resolution', 'type': 'list',
             'limits': [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0], 'value': 0.02},
            {'title': 'Sensitivity:', 'name': 'sensitivity', 'type': 'list',
             'limits': ['NHLD', 'NAUT', 'NORM', 'MID', 'HIGH1', 'HIGH2', 'HIGH3'],
             'value': 'NORM'},
            {'title': 'Sample Points:', 'name': 'sample_points', 'type': 'int',
             'value': 5001, 'min': 101, 'max': 50001},
        ]},
        {'title': 'Active Trace:', 'name': 'active_trace', 'type': 'list',
         'limits': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
         'value': 'A'},
        {'title': 'Auto Sweep:', 'name': 'auto_sweep', 'type': 'bool', 'value': True,
         'tip': 'Automatically trigger sweep on grab'},
        {'title': 'Power Threshold (dBm):', 'name': 'power_threshold', 'type': 'float',
         'value': -65.0, 'suffix': ' dBm', 'tip': 'Set values below threshold to threshold (noise floor)'},
        {'title': 'ID:', 'name': 'instrument_id', 'type': 'str', 'value': '', 'readonly': True},
    ]

    # Resolution mapping: display value (nm) -> pymeasure value (m)
    RESOLUTION_MAP = {
        0.02: 0.02e-9,
        0.05: 0.05e-9,
        0.1: 0.1e-9,
        0.2: 0.2e-9,
        0.5: 0.5e-9,
        1.0: 1e-9,
        2.0: 2e-9,
    }

    def ini_attributes(self):
        """Initialize attributes"""
        self.controller: AQ6370Series = None
        self.x_axis = None

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter whose value has been changed by the user
        """
        if self.controller is None:
            return

        try:
            if param.name() == 'center_wl':
                self.controller.wavelength_center = param.value() * 1e-9  # Convert nm to m
            elif param.name() == 'span_wl':
                self.controller.wavelength_span = param.value() * 1e-9
            elif param.name() == 'resolution':
                self.controller.resolution_bandwidth = self.RESOLUTION_MAP[param.value()]
            elif param.name() == 'sensitivity':
                self.controller.sensitivity = param.value()
            elif param.name() == 'sample_points':
                self.controller.sample_number = int(param.value())
            elif param.name() == 'active_trace':
                # Convert trace letter to index (A=0, B=1, etc.)
                trace_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6}
                self.controller.active_trace = trace_map[param.value()]
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error setting parameter: {str(e)}', 'log']))

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        self.ini_detector_init(slave_controller=controller)

        if self.is_master:
            # Get instrument model and VISA address from settings
            model = self.settings['model']
            visa_address = self.settings['visa_address']

            # Map model name to class
            model_map = {
                'AQ6370C': AQ6370C,
                'AQ6370D': AQ6370D,
                'AQ6373': AQ6373,
                'AQ6373B': AQ6373B,
                'AQ6375': AQ6375,
                'AQ6375B': AQ6375B,
            }

            try:
                # Create VISAAdapter with proper termination settings
                adapter = VISAAdapter(visa_address,
                                      read_termination='\r\n',
                                      write_termination='\r\n',
                                      timeout=10000)

                # Instantiate the appropriate instrument class
                instrument_class = model_map.get(model, AQ6370D)
                self.controller = instrument_class(adapter)

                # Authenticate if using Ethernet (TCPIP connection)
                if 'TCPIP' in visa_address:
                    try:
                        self.controller.authenticate_ethernet("anonymous", "")
                    except Exception:
                        pass  # Authentication may not be required for all devices

                # Set transfer format to ASCII to avoid binary decoding issues
                self.controller.transfer_format = "ASCII"

                # Apply initial settings
                self.controller.wavelength_center = self.settings['sweep_settings', 'center_wl'] * 1e-9
                self.controller.wavelength_span = self.settings['sweep_settings', 'span_wl'] * 1e-9
                self.controller.resolution_bandwidth = self.RESOLUTION_MAP[self.settings['sweep_settings', 'resolution']]
                self.controller.sensitivity = self.settings['sweep_settings', 'sensitivity']
                self.controller.sample_number = self.settings['sweep_settings', 'sample_points']
                # Convert trace letter to index (A=0, B=1, etc.)
                trace_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6}
                self.controller.active_trace = trace_map[self.settings['active_trace']]

                # Get identity
                info = self.controller.id
                self.settings.child('instrument_id').setValue(info)
                initialized = True

            except Exception as e:
                initialized = False
                info = f"Failed to initialize: {str(e)}"
                self.emit_status(ThreadCommand('Update_Status', [info, 'log']))
                return info, initialized
        else:
            self.controller = controller
            info = "Slave mode"
            initialized = True

        # Initialize x_axis (wavelength axis in nm)
        # We'll update this on first grab with actual data
        start_wl = self.settings['sweep_settings', 'center_wl'] - self.settings['sweep_settings', 'span_wl'] / 2
        stop_wl = self.settings['sweep_settings', 'center_wl'] + self.settings['sweep_settings', 'span_wl'] / 2
        n_points = self.settings['sweep_settings', 'sample_points']
        wavelengths = np.linspace(start_wl, stop_wl, n_points)
        self.x_axis = Axis(data=wavelengths, label='Wavelength (nm)', units='', index=0)

        # Initialize data structure
        self.dte_signal_temp.emit(DataToExport(name='AQ6370',
                                               data=[DataFromPlugins(name='Spectrum',
                                                                     data=[np.zeros(n_points)],
                                                                     dim='Data1D',
                                                                     labels=['Power'],
                                                                     axes=[self.x_axis])]))

        return info, initialized

    def close(self):
        """Terminate the communication protocol"""
        if self.is_master and self.controller is not None:
            try:
                self.controller.shutdown()
            except Exception as e:
                self.emit_status(ThreadCommand('Update_Status', [f'Error closing connection: {str(e)}', 'log']))

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible)
        kwargs: dict
            others optional arguments
        """
        try:
            trace = self.settings['active_trace']

            # Trigger sweep if auto_sweep is enabled
            if self.settings['auto_sweep']:
                self.controller.initiate_sweep()
                # Wait for sweep to complete (with 60s timeout)
                self.controller.wait_for_sweep_complete(timeout=60)

            # Get wavelength and power data
            wavelengths = self.controller.get_xdata(trace=trace)  # in meters
            powers = self.controller.get_ydata(trace=trace)  # in dBm

            # Convert wavelengths from meters to nanometers
            wavelengths_nm = np.array(wavelengths) * 1e9
            powers_dbm = np.array(powers)

            # Apply power threshold to filter noise
            threshold = self.settings['power_threshold']
            powers_dbm = np.where(powers_dbm < threshold, threshold, powers_dbm)

            # Update x-axis with actual data
            self.x_axis = Axis(data=wavelengths_nm, label='Wavelength (nm)', units='', index=0)

            # Emit data
            self.dte_signal.emit(DataToExport('AQ6370',
                                              data=[DataFromPlugins(name='Spectrum',
                                                                    data=[powers_dbm],
                                                                    dim='Data1D',
                                                                    labels=['Power (dBm)'],
                                                                    axes=[self.x_axis])]))

        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error grabbing data: {str(e)}', 'log']))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        try:
            if self.controller is not None:
                self.controller.abort()
            self.emit_status(ThreadCommand('Update_Status', ['Acquisition stopped']))
        except Exception as e:
            self.emit_status(ThreadCommand('Update_Status', [f'Error stopping: {str(e)}', 'log']))
        return ''


if __name__ == '__main__':
    main(__file__)