import tkinter as tk
import can
import struct
import hashlib
from tkinter import filedialog


class FirmwareFlasherGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("RP2040 Firmware Flasher")

        # Create PCAN bus dropdown
        self.pcan_label = tk.Label(self.window, text="PCAN device:")
        self.pcan_var = tk.StringVar(value="PCAN_USBBUS1")
        self.pcan_dropdown = tk.OptionMenu(self.window, self.pcan_var, "PCAN_USBBUS1", "PCAN_USBBUS2")

        # Create connect/disconnect buttons
        self.connect_button = tk.Button(self.window, text="Connect", command=self.connect_bus)
        self.disconnect_button = tk.Button(self.window, text="Disconnect", command=self.disconnect_bus)
        self.disconnect_button.config(state=tk.DISABLED)

        # Create firmware file widgets
        self.file_path_label = tk.Label(self.window, text="Firmware file path:")
        self.file_path_entry = tk.Entry(self.window, width=50)
        self.select_file_button = tk.Button(self.window, text="Select file", command=self.select_file)

        # Create firmware flash widgets
        self.flash_button = tk.Button(self.window, text="Flash firmware", command=self.flash_firmware)
        self.status_label = tk.Label(self.window, text="")

        # Layout widgets
        self.pcan_label.grid(row=0, column=0)
        self.pcan_dropdown.grid(row=0, column=1)
        self.connect_button.grid(row=0, column=2)
        self.disconnect_button.grid(row=0, column=3)
        self.file_path_label.grid(row=1, column=0)
        self.file_path_entry.grid(row=1, column=1)
        self.select_file_button.grid(row=1, column=2)
        self.flash_button.grid(row=2, column=1)
        self.status_label.grid(row=3, column=0, columnspan=4)

    def connect_bus(self):
        self.bus = can.interface.Bus(bustype='pcan', channel=self.pcan_var.get(), bitrate=500000)
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.NORMAL)

    def disconnect_bus(self):
        self.bus.shutdown()
        self.disconnect_button.config(state=tk.DISABLED)
        self.connect_button.config(state=tk.NORMAL)

    def select_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)

    def flash_firmware(self):
        file_path = self.file_path_entry.get()
        if not hasattr(self, 'bus'):
            self.status_label.config(text="Please connect to a PCAN device")
            return
        if not file_path:
            self.status_label.config(text="Please select a firmware file")
            return

        try:
            firmware_file = open(file_path, 'rb')
            firmware_data = firmware_file.read()
            firmware_size = len(firmware_data)
            firmware_sha256 = hashlib.sha256(firmware_data).digest()

            # Send firmware download request
            request = can.Message(arbitration_id=0x7DF,
                                  data=[0x34, 0x00] + list(struct.pack('>I', firmware_size)) + list(firmware_sha256))
            self.bus.send(request)

            # Wait for response
            response = self.bus.recv(timeout=1.0)
            if response is None:
                self.status_label.config(text="No response from bootloader")
                return
            elif response.data[0] != 0x74 or response.data[1] != 0x00:
                self.status_label.config(text="Firmware download request rejected")
                return

            # Send firmware data blocks
            block_size = 0x7E
            for i in range(0, firmware_size, block_size):
                block_data = firmware_data[i:i + block_size]
                block_number = int(i / block_size) + 1
                request = can.Message(arbitration_id=0x7DF, data=[0x36, block_number] + list(block_data))
                self.bus.send(request)

            # Send firmware download complete request
            request = can.Message(arbitration_id=0x7DF, data=[0x34, 0x01])
            self.bus.send(request)

            # Wait for response
            response = self.bus.recv(timeout=1.0)
            if response is None:
                self.status_label.config(text="No response from bootloader")
                return
            elif response.data[0] != 0x74 or response.data[1] != 0x01:
                self.status_label.config(text="Firmware update failed")
                return

            self.status_label.config(text="Firmware update successful")
        except:
            self.status_label.config(text="Error reading firmware file")

    def run(self):
        self.window.mainloop()

if __name__ == '__main__':
    firmware_flasher_gui = FirmwareFlasherGUI()
    firmware_flasher_gui.run()
