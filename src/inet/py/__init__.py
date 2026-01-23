# Hand-written inet module for Python
# Contains native implementations for networking types

# Import patches when module is loaded
from . import SocketConfig
from . import IpAddr
from . import TcpSocket
