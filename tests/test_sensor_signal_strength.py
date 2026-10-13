import unittest
from unittest import mock

from homeassistant.helpers.entity import Entity
from homeassistant.const import Platform
from eltakobus import *
from enocean.protocol.packet import RadioPacket
from enocean.protocol.constants import RORG

from custom_components.eltako.sensor import SignalStrengthSensor
from custom_components.eltako.vendor.esp3_serial_com import ESP3SerialCommunicator
from tests.mocks import *

Entity.schedule_update_ha_state = mock.Mock(return_value=None)


class TestSignalStrengthSensor(unittest.TestCase):

    def create_sensor(self) -> SignalStrengthSensor:
        gateway = GatewayMock()
        dev_id = AddressExpression.parse("05-90-D3-1B")
        return SignalStrengthSensor(Platform.SENSOR, gateway, dev_id, "device name", EEP.find("G5-3F-7F"))

    def test_takes_dbm_of_received_telegram(self):
        s = self.create_sensor()
        msg = RPSMessage(address=b'\x05\x90\xD3\x1B', status=0x30, data=b'\x02', outgoing=False)
        msg.dBm = -84

        s.value_changed(msg)

        self.assertEqual(s.native_value, -84)

    def test_keeps_value_when_telegram_carries_no_dbm(self):
        s = self.create_sensor()
        first = RPSMessage(address=b'\x05\x90\xD3\x1B', status=0x30, data=b'\x02', outgoing=False)
        first.dBm = -80
        s.value_changed(first)
        second = RPSMessage(address=b'\x05\x90\xD3\x1B', status=0x30, data=b'\x01', outgoing=False)

        s.value_changed(second)

        self.assertEqual(s.native_value, -80)

    def test_unique_id_and_unit(self):
        s = self.create_sensor()

        self.assertEqual(s.native_unit_of_measurement, "dBm")
        self.assertTrue(s.unique_id.endswith("_signal_strength"))


class TestEsp2TranslationCarriesDbm(unittest.TestCase):

    def test_translated_message_carries_dbm_of_packet(self):
        packet = RadioPacket.create(rorg=RORG.RPS, rorg_func=0x02, rorg_type=0x02,
                                    sender=[0x05, 0x90, 0xD3, 0x1B], R1=0, EB=0, R2=0, SA=0, T21=1, NU=0)
        packet.dBm = -86

        esp2 = ESP3SerialCommunicator.convert_esp3_to_esp2_message(packet)

        self.assertEqual(esp2.dBm, -86)


class TestPerDeviceInfoEntities(unittest.TestCase):

    def test_device_on_two_platforms_gets_one_signal_sensor_and_one_id_field(self):
        from custom_components.eltako.sensor import create_per_device_info_entities, StaticInfoField
        from homeassistant.const import CONF_ID, CONF_NAME
        from custom_components.eltako.const import CONF_EEP
        dev = {CONF_ID: "05-90-D3-1B", CONF_EEP: "G5-3F-7F", CONF_NAME: "Treppenhaus"}
        config = {Platform.COVER: [dev], Platform.SENSOR: [dict(dev)]}

        entities = create_per_device_info_entities(Platform.SENSOR, GatewayMock(), config)

        self.assertEqual(len([e for e in entities if isinstance(e, SignalStrengthSensor)]), 1)
        self.assertEqual(len([e for e in entities if isinstance(e, StaticInfoField)]), 1)
