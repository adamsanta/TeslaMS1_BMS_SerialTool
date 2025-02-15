# TeslaMS1_BMS_SerialTool

This tool is a *Python* GUI for communicating with the **Tesla Model S** mk1 (2012-2016) slave **BMS** via a FTDI module.<br>
**Features:** Slave reset ; ID and thresholds config ; cells voltages, temperatures, alerts and faults readings.<br>
**Goal:** Enhance BMS reparability and extend usability for diverse applications.

# Hardware setup

The picture below show the **Tesla Model S** mk1 (2012-2016) slave **BMS** for which the present tool is made for.
We will communicate with it through a connector available on its PCB:
![PCB serial com entry point](img/slave_bms_pcb_back.png "Com entry point")

The female connector highlighted on the picture is compatible with the male connector **Molex 0015975101**:<br>
https://www.molex.com/en-us/products/part-detail/15975101

To setup the cable connecting your laptop to the slave BMS, we will use this male connector (**Molex 0015975101**) and follow the following schematic:

**Warning:** 
- If your BMS board is disconnected from any other BMS, you can set up the FT232 USB UART board to either 3.3V or 5V. This is because the Si8642 Isolator used on the BMS can accept both voltages on its bus interface. If your BMS board is already receiving an external voltage on its Molex connector, use the same voltage as already present.
- Note that the Molex connector is seen from the side where you insert the wires (not the side going into the PCB female connector).

![PC-BMS cable schematic](img/teslams_bms_serial_cable.drawio.png "PC-BMS cable schematic")

Once you have setup such a cable, you can plug the USB side to your PC and the Molex side to the slave BMS before following the "**SW Getting Started**" section to start interacting with your target.

**TODO**<br>
If you don't have a Molex 0015975101 connector at end, you can also directly solder wires to the PCB to get something looking like this:<br>
**TODO**

# SW Getting Started

Run the commands below in a shell to get the application running in a Python virtual environment.

```bash
# Create a venv named 'tms_bms_venv' (or whatever you prefer)
python -m venv tms_bms_venv

# Activate this venv
# On Linux/macOS:
source tms_bms_venv/bin/activate
# On Windows:
tms_bms_venv\Scripts\activate

# Install requirements.txt
pip install -r requirements.txt

# Run the application
python src/main.py

# At any moment, you can deactivate the venv and get back to your global Python environment with
deactivate
```


# TODO

- Add warning on responsibility if any issue
- Add a list of features in README
- Write doc on logging
- Add a full update button
- Add reading and displaying of DEVICE_STATUS register
- Add setting of voltage and temperature threshold comparison timings
- Display the information when security thresholds are disabled
- Refactor for Python uv
- Mention sources
- Add a markdown file for extra information
- Add things to clarify (toggling UV OV alerts)