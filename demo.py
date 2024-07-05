from pydoc import cli
from wsgiref.util import request_uri
from pymodbus.client import ModbusTcpClient
from pymodbus.transaction import ModbusSocketFramer
from rouchu import get_pressure, set_pressure,launch_pressure,is_pressure_launched


if __name__ == "__main__":
    # 连接夹爪
    client = ModbusTcpClient('192.168.1.200', port=502, timeout=10)
    client.connect()

    pressure = get_pressure(client)
    print(f"当前压力为 {pressure} kPa") 

    positive_pressure = set_pressure(client=client,pressure_value=100,style='Positive')
    print(f"设置正压为 {positive_pressure} kPa") 
    
    negative_pressure = set_pressure(client=client,pressure_value=-30,style='Negative')
    print(f"设置负压为 {negative_pressure} kPa") 

    launch_pressure(client=client,state='OFF',style='Negative')

    result = is_pressure_launched(client,style='Positive')
    print(f"正压状态为 {"ON" if result else "OFF"}")

    client.close()