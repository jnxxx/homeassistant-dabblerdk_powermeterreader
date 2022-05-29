import asyncio
import socket
from typing import Text, Tuple, Union, cast

import dns.message
import dns.name

MDNS_ADDRESS = "224.0.0.251"
MDNS_PORT = 5353


class MDnsProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.queries = {}

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, data: Union[bytes, Text], addr: Tuple) -> None:
        message = dns.message.from_wire(data)
        for answer in message.answer:
            for item in answer.items:
                if len(item.data) == 4:
                    future = self.queries.pop(answer.name, None)
                    if future is not None:
                        future.set_result(socket.inet_ntoa(item.data))

    async def resolve(self, hostname: str) -> str:
        name = dns.name.from_text(hostname)
        message = dns.message.make_query(name, "A")
        message.id = 0
        message.flags = 0

        future = asyncio.Future()
        self.queries[name] = future
        self.transport.sendto(message.to_wire(), (MDNS_ADDRESS, MDNS_PORT))
        return await future


async def create_mdns_resolver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_ADD_MEMBERSHIP,
        socket.inet_aton(MDNS_ADDRESS) + b"\x00\x00\x00\x00",
    )
    sock.bind((MDNS_ADDRESS, MDNS_PORT))

    loop = asyncio.get_event_loop()
    _, protocol = await loop.create_datagram_endpoint(
        lambda: MDnsProtocol(),
        sock=sock,
    )
    return protocol