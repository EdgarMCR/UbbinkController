import serial


import minimalmodbus


# Configuration
PORT = '/dev/ttyUSB0'  # Your Waveshare adapter port
SLAVE_ID = 20          # Confirmed ID for Ubiflux Vigor
BAUD_RATE = 19200      # Default for Vigor


def get_controller(port: str = PORT, slave_id: int = SLAVE_ID, baud_rate: int = BAUD_RATE):
    # Initialize the instrument
    controller = minimalmodbus.Instrument(PORT, SLAVE_ID)
    controller.serial.baudrate = BAUD_RATE
    controller.serial.bytesize = 8
    controller.serial.parity   = serial.PARITY_EVEN
    controller.serial.stopbits = 1
    controller.serial.timeout  = 0.5  # Crucial: Give the Vigor time to respond

    # Set the mode to RTU
    controller.mode = minimalmodbus.MODE_RTU
    return controller
