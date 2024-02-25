import crcmod
import serial

VERBOSE = True

SERIAL_BAUDRATE = 612500
SERIAL_TIMEOUT = 1

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
    # print(hex(crc8_func(bytearray([0x01, 0x61]))))
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

def reset_slave(*, ser, id):
    rx_data = write_bq76(ser, id, RESET_REG_ADDR, RESET_MAGIC_CODE)
    _print(f"Reset slave {id}.\n")

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
    else:
        _print(f"ID update NOK: {old_id}-/->{new_id}.\n")