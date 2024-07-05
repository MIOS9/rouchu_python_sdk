from pymodbus.factory import ClientDecoder
from pymodbus.client import ModbusTcpClient

# 常量定义
TRANSACTION_ID = 0x0000
PROTOCOL_ID = 0x0000
UNIT_ID = 0x01
LENGTH = 0x0006

def unsigned_to_signed_16bit(value: int) -> int:
    """
    将16位无符号整数转换为有符号整数
    :param value: 16位无符号整数
    :return: 有符号整数
    """
    if value > 0xFFFF:
        raise ValueError("Value exceeds 16-bit unsigned integer range")
    return value - 0x10000 if value > 0x7FFF else value

def build_mbap_header(transaction_id: int, protocol_id: int, length: int, unit_id: int) -> bytes:
    """
    构造MBAP header
    :param transaction_id: 事务标识符
    :param protocol_id: 协议标识符
    :param length: 后续字节长度
    :param unit_id: 从站地址
    :return: MBAP header
    """
    return bytes([
        (transaction_id >> 8) & 0xFF, transaction_id & 0xFF,
        (protocol_id >> 8) & 0xFF, protocol_id & 0xFF,
        (length >> 8) & 0xFF, length & 0xFF,
        unit_id
    ])

def send_request(client: ModbusTcpClient, request: bytes) -> bytes:
    """
    发送请求并接收响应
    :param client: Modbus客户端
    :param request: 请求报文
    :return: 响应报文
    """
    # 发送报文并接收响应
    client.socket.send(request)
    response = client.socket.recv(1024)
    
    # 解析响应
    response_pdu = response[7:] # 跳过前7个字节的 MBAP header
    decoder = ClientDecoder()   
    response_message = decoder.decode(response_pdu)

    return response_message

def get_pressure(client: ModbusTcpClient) -> int:
    """
    获取压力值
    :param client: Modbus客户端
    :return: 压力值
    """
    function_code = 0x03            # 功能码
    starting_address = 0x0302       # 寄存器起始地址
    quantity_of_registers = 0x0002  # 寄存器数量
    
    # 获取压力状态的报文内容
    request_mbap = build_mbap_header(TRANSACTION_ID, PROTOCOL_ID, LENGTH, UNIT_ID)
    
    # 获取压力状态的报文内容
    request_pdu = bytes([
        function_code,
        (starting_address >> 8) & 0xFF, starting_address & 0xFF,
        (quantity_of_registers >> 8) & 0xFF, quantity_of_registers & 0xFF
    ])
    request = request_mbap + request_pdu

    response_message = send_request(client, request)

    if hasattr(response_message, 'registers'):
        pressure = response_message.registers[0]
        return unsigned_to_signed_16bit(pressure)
    else:
        raise ValueError("Invalid response message")

def set_pressure(client: ModbusTcpClient, pressure_value: int, style: str = 'Positive') -> int:
    """
    设置压力值
    :param client: Modbus客户端
    :param pressure_value: 压力值
    :param style: 压力类型（'Positive' 或 'Negative'）
    :return: 设置后的压力值
    """
    function_code = 0x06  # 功能码
    address = 0x0306 if style == 'Positive' else 0x0307   # 寄存器起始地址

    # 保证压力在合法范围: [-80,-10] or [10,300]
    pressure_value = max(10, min(300, pressure_value)) if style == 'Positive' else max(-80, min(-10, pressure_value))

    # 将压力值转换为两个字节
    pressure_high_byte = (pressure_value >> 8) & 0xFF
    pressure_low_byte = pressure_value & 0xFF

    # 构造MBAP header和设定压力报文内容
    request_mbap = build_mbap_header(TRANSACTION_ID, PROTOCOL_ID, LENGTH, UNIT_ID)
    request_pdu = bytes([
        function_code,
        (address >> 8) & 0xFF, address & 0xFF,
        pressure_high_byte, pressure_low_byte
    ])
    request = request_mbap + request_pdu

    response_message = send_request(client, request)

    return unsigned_to_signed_16bit(response_message.value)

def is_pressure_launched(client: ModbusTcpClient, style: str = 'Positive') -> bool:
    """
    查询正压是否触发
    :param client: Modbus客户端
    :param style: 压力类型（'Positive' 或 'Negative'）
    :return: (True / False)
    """
    function_code = 0x02  # 功能码
    address = 0x0200 if style == 'Positive' else 0x0201  # 压力反馈地址
    quantity_of_inputs = 0x0001  # 读取一个输入

    # 构造MBAP header和压力反馈报文内容
    request_mbap = build_mbap_header(TRANSACTION_ID, PROTOCOL_ID, LENGTH, UNIT_ID)
    request_pdu = bytes([
        function_code,
        (address >> 8) & 0xFF, address & 0xFF,
        (quantity_of_inputs >> 8) & 0xFF, quantity_of_inputs & 0xFF
    ])
    request = request_mbap + request_pdu

    response_message = send_request(client, request)

    if hasattr(response_message, 'bits'):
        return response_message.bits[0]
    else:
        raise ValueError("Invalid response message")

def launch_pressure(client: ModbusTcpClient, state: str = 'ON', style: str = 'Positive') -> bool:
    """
    触发正负压
    :param client: Modbus客户端
    :param state: 压力状态（'ON' 或 'OFF'）
    :param style: 压力类型（'Positive' 或 'Negative'）
    :return: (True/False)
    """
    function_code = 0x05
    address = 0x0100 if style == 'Positive' else 0x0101
    value = 0xFF00 if state == 'ON' else 0x0000

    request_mbap = build_mbap_header(TRANSACTION_ID, PROTOCOL_ID, LENGTH, UNIT_ID)
    request_pdu = bytes([
        function_code,
        (address >> 8) & 0xFF, address & 0xFF,
        (value >> 8) & 0xFF, value & 0xFF
    ])
    request = request_mbap + request_pdu

    response_message = send_request(client, request)

    return response_message.value
