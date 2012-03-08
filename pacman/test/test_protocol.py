from mock import Mock
from pacman.fields import Magic, SBInt64, DispatchField, UBInt8, DispatchTarget, \
    LengthField
from pacman.message import BaseMessage
from pacman.protocol import StreamProtocolHandler
from pacman.test.examples.test_network_stack import UDPFrame
import unittest


class MagicSchema(BaseMessage):
    magic = Magic('\xAA\xAA')
    value = SBInt64()


class ErrorCaseSchema(BaseMessage):
    type = DispatchField(UBInt8())
    length = LengthField(UBInt8())
    body = DispatchTarget(length, type, {
        0x00: MagicSchema
    })


class TestStreamProtocol(unittest.TestCase):

    def test_protocol_basic(self):
        packets_received = []

        def callback(packet):
            packets_received.append(packet)

        f = UDPFrame()
        f.data = "Hello, world"
        f.checksum = 0x01
        f.destination_port = 9000
        f.source_port = 8000

        phandler = StreamProtocolHandler(UDPFrame, callback)
        packet_bytes = f.pack()
        rem_bytes = packet_bytes
        while len(rem_bytes) > 0:
            chunk = rem_bytes[:5]
            rem_bytes = rem_bytes[5:]
            phandler.feed(chunk)

        assert(len(packets_received) == 1)
        rx = packets_received[0]
        assert rx.data == "Hello, world"
        assert rx.checksum == 0x01
        assert rx.destination_port == 9000
        assert rx.source_port == 8000

    def test_protocol_violation(self):
        # verify that when there is a protocol violation, that state gets
        # cleaned up properly.  For this, we have a dispatch field that
        # has an unmapped type byte

        rx = []

        def bad_cb(packet):
            self.fail("Callback should not have been executed")

        def good_cb(packet):
            rx.append(packet)
            self.assertEqual(packet.body.value, -31415926)

        good_msg = ErrorCaseSchema()
        good_msg.body = MagicSchema()
        good_msg.body.value = -31415926
        good_packet = good_msg.pack()

        bad_packet = '\x01\x02\xAA\xAA' + good_packet
        phandler = StreamProtocolHandler(ErrorCaseSchema, bad_cb)
        phandler.feed(bad_packet)

        phandler.packet_callback = good_cb
        phandler.feed(good_packet)

        self.assertEqual(len(rx), 1)

    def test_protocol_magic_scan_full_buffer(self):
        rx = []

        def cb(packet):
            rx.append(packet)

        protocol_handler = StreamProtocolHandler(MagicSchema, cb)
        test_sequence = MagicSchema()
        test_sequence.value = -29939
        pack = test_sequence.pack()

        # garbage with our bytes in the middle
        test_bytes = '\x1A\x3fadbsfkasdf;aslkfjasd;f' + pack + '\x00\x00asdfn234r'
        protocol_handler.feed(test_bytes)
        self.assertEqual(len(rx), 1)
        self.assertEqual(rx[0].value, -29939)

    def test_protocol_magic_scan_single_byte(self):
        rx = []

        def cb(packet):
            rx.append(packet)

        protocol_handler = StreamProtocolHandler(MagicSchema, cb)
        test_sequence = MagicSchema()
        test_sequence.value = -29939
        pack = test_sequence.pack()

        # garbage with our bytes in the middle
        test_bytes = '\x1A\x3fadbsfkasdf;aslkfjasd;f' + pack + '\x00\x00asdfn234r'
        for b in test_bytes:
            protocol_handler.feed(b)
        self.assertEqual(len(rx), 1)
        self.assertEqual(rx[0].value, -29939)

if __name__ == '__main__':
    unittest.main()
