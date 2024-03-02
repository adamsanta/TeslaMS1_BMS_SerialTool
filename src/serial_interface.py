import crcmod
import math
import serial

VERBOSE = True

SERIAL_BAUDRATE = 612500
SERIAL_TIMEOUT = 0.05

BROADCAST_ADDR = 0x3F
RESET_REG_ADDR = 0x3C
RESET_MAGIC_CODE = 0xA5
OV_REG_ADDR = 0x42
UV_REG_ADDR = 0x44
SHDW_REG_ADDR = 0x3A
SHDW_UNLOCK_MAGIC_CODE = 0x35
IO_CONFIG_ADDR = 0x31
ADC_START_ADDR = 0x34
ADC_CONFIG_ADDR = 0x30
ADC_RES_ADDR = 0x01
ADC_NB_MEAS = 9*2 # 9 * 2 bytes measurements
ADDR_RANGE_FULL_SIZE = 0x4C

def _print(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)

def con_serial_port(port_name):
    serial_con = None
    try:
        serial_con = serial.Serial(port=port_name, baudrate=SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
        _print(f"Connection has been set to {port_name}.")
    except IOError:
        try:
            serial_con.close()
            serial_con.open()
            _print(f"{port_name} was already open, it has been closed and opened again.")
        except:
            _print(f"ERROR: can't open {port_name}. Check its config (serial_interface.con_serial_port).")
    return serial_con

def disco_serial_port(serial_con):
    try:
        serial_con.close()
        _print(f"Disconnected from {serial_con.port}.")
        return True
    except:
        _print(f"ERROR: can't open {serial_con.port}. Check its config (serial_interface.con_serial_port).")
        return False

def crc8_func(byte_array):
    return crcmod.mkCrcFun(0x107, initCrc=0, rev=False)(byte_array)

def print_packet(tx_rx, bytes):
    _print(f"{tx_rx.upper()}: ", end='')
    for byte in bytes:
        _print(hex(byte), end=' ')
    _print("")

def read_bq76(ser, id, reg_addr, length):
    _print(f"-> Reading {length} bytes at @{hex(reg_addr)} from BQ76 #{id}")
    packet = [id<<1, reg_addr, length]
    # crc = crc8_func(bytearray(packet))
    # packet.append(crc)

    print_packet("tx", packet)
    ser.write(bytearray(packet))
    ans = ser.read(255)
    print_packet("rx", ans)

    crc_data = [ans[0]&0x7F]+[b for b in ans[1:-1]]
    crc_res = crc8_func(bytearray(crc_data))
    if ans[-1]==crc_res:
        _print(f"CRC OK: expected:{hex(crc_res)}==received:{hex(ans[-1])}")
    else:
        _print(f"CRC NOK: expected{hex(crc_res)}!=received:{hex(ans[-1])}")
    
    _print("")

    return ans

def write_bq76(ser, id, reg_addr, val):
    _print(f"-> Writing {hex(val)} at @{hex(reg_addr)} of BQ76 #{id}")
    packet = [(id<<1)|0x1, reg_addr, val]
    crc = crc8_func(bytearray(packet))
    packet.append(crc)

    print_packet("tx", packet)
    ser.write(bytearray(packet))
    ans = ser.read(255)
    print_packet("rx", ans)
    _print("")

    return ans

def full_dump(*, ser, id):
    rx_data = read_bq76(ser, id, 0x00, ADDR_RANGE_FULL_SIZE)
    _print(f"Full dump done for slave {id}.\n")
    return rx_data

def reset_slave(*, ser, id):
    rx_data = write_bq76(ser, id, RESET_REG_ADDR, RESET_MAGIC_CODE)
    _print(f"Reset slave {id}.\n")
    return rx_data

def get_slave_id(*, ser, id):
    rx_data = read_bq76(ser, id, 0x3b, 0x1)
    if len(rx_data)<4:
        _print(f"ERROR: get_slave_id({id}) failed.\n")
        return -1
    slave_id = rx_data[3]&0x3F
    if rx_data[3]&0x80:
        _print(f"Slave ID: {slave_id} (set)\n")
    else:
        _print(f"Slave ID: {slave_id} (unset)\n")
    return slave_id

def set_slave_id(*, ser, old_id, new_id):
    rx_data = write_bq76(ser, old_id, 0x3b, 0x80|new_id)
    if len(rx_data)<3:
        _print(f"ERROR: set_slave_id {old_id}->{new_id} failed.\n")
        return -1
    if rx_data[2]==(0x80|new_id):
        _print(f"ID update OK: {old_id}->{new_id}.\n")
        return 0
    else:
        _print(f"ID update NOK: {old_id}-/->{new_id}.\n")
        return -1

def start_adc_meas(*, ser, id):
    rx_data = write_bq76(ser, id, ADC_START_ADDR, 0x1)
    rx_data = read_bq76(ser, id, ADC_START_ADDR, 0x1)
    meas_ongoing = rx_data[3]
    # Wait for end of measurement
    while meas_ongoing==0x1:
        rx_data = read_bq76(ser, id, ADC_START_ADDR, 0x1)
        meas_ongoing = rx_data[3]
    _print(f"ADC meas started for slave {id}.\n")

def read_adc_meas(*, ser, id):
    # Store actual registers content to set it back after readings
    rx_data = read_bq76(ser, id, ADC_CONFIG_ADDR, 0x1)
    adc_config_reg_backup = rx_data[3]
    rx_data = read_bq76(ser, id, IO_CONFIG_ADDR, 0x1)
    io_config_reg_backup = rx_data[3]

    # Configure ADC for full measurement
    write_bq76(ser, id, ADC_CONFIG_ADDR, adc_config_reg_backup|0x3D)
    # Configure TS1 and TS2 pins for temperature measurement
    write_bq76(ser, id, IO_CONFIG_ADDR, io_config_reg_backup|0x03)
    _print(f"Full ADC meas (GPAI, TS1, TS2, C1-2-3-4-5-6) configured for slave {id}.\n")

    start_adc_meas(ser=ser, id=id)

    # Voltages returned are in mV. See sections 7.3.1.3 to 7.3.1.5 from the TI BQ76 datasheet.
    rx_data = read_bq76(ser, id, ADC_RES_ADDR, ADC_NB_MEAS)
    gpai = rx_data[3]<<8 | rx_data[4]
    gpai = round(gpai * 33333 /16383, 2)
    vcell1 = rx_data[5]<<8 | rx_data[6]
    vcell1 = round(vcell1 *6250 / 16383, 2)
    vcell2 = rx_data[7]<<8 | rx_data[8]
    vcell2 = round(vcell2 *6250 / 16383, 2)
    vcell3 = rx_data[9]<<8 | rx_data[10]
    vcell3 = round(vcell3 *6250 / 16383, 2)
    vcell4 = rx_data[11]<<8 | rx_data[12]
    vcell4 = round(vcell4 *6250 / 16383, 2)
    vcell5 = rx_data[13]<<8 | rx_data[14]
    vcell5 = round(vcell5 *6250 / 16383, 2)
    vcell6 = rx_data[15]<<8 | rx_data[16]
    vcell6 = round(vcell6 *6250 / 16383, 2)
    # Temperatures are operated using the steinhart/hart equation
    # See the readModuleValues function at https://github.com/collin80/TeslaBMS/blob/master/BMSModule.cpp#L88
    temp1 = rx_data[17]<<8 | rx_data[18]
    temp1 = (temp1 + 2) / 33046
    temp1 = ((1.78 / temp1) - 3.57) * 1000
    temp1 = 1.0 / (0.0007610373573 + (0.0002728524832 * math.log(temp1)) + (pow(math.log(temp1), 3) * 0.0000001022822735))
    temp1 = round(temp1 - 273.15, 3)
    temp2 = rx_data[19]<<8 | rx_data[20]
    temp2 = (temp2 + 9) / 33068
    temp2 = ((1.78 / temp2) - 3.57) * 1000
    temp2 = 1.0 / (0.0007610373573 + (0.0002728524832 * math.log(temp2)) + (pow(math.log(temp2), 3) * 0.0000001022822735))
    temp2 = round(temp2 - 273.15, 3)
    _print(gpai, vcell1, vcell2, vcell3, vcell4, vcell5, vcell6, temp1, temp2, "\n")

    # Setting back registers' content before returning
    write_bq76(ser, 0, ADC_CONFIG_ADDR, adc_config_reg_backup)
    write_bq76(ser, 0, IO_CONFIG_ADDR, io_config_reg_backup)

    return gpai, vcell1, vcell2, vcell3, vcell4, vcell5, vcell6, temp1, temp2