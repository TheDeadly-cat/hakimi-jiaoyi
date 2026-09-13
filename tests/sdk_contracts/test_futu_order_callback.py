"""Real pinned SDK decoder, synthetic protobuf only; all socket connects denied."""
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import unittest


def deny_network(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo'):
        raise RuntimeError('SDK contract tests prohibit network access')


sys.addaudithook(deny_network)
from futu import RET_OK, RET_ERROR, TrdEnv, TrdMarket, TrdSide, OrderType, OrderStatus, TimeInForce
from futu.common.pb import Trd_UpdateOrder_pb2, Trd_Common_pb2, Trd_ModifyOrder_pb2
from futu.trade.trade_query import ModifyOrder

SPEC = importlib.util.spec_from_file_location('transport_fixture',
    Path(__file__).resolve().parents[1] / 'repository_only/test_futu_simulation_adapter.py')
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)
adapter_module = fixture.futu


def enum_number(enum, value):
    ok, number = enum.to_number(value)
    if not ok:raise AssertionError('invalid SDK fixture enum')
    return number


class ActualSdkCallbackContracts(unittest.TestCase):
    def setUp(self):
        self.assertEqual(importlib.metadata.version('futu-api'), adapter_module.SDK_VERSION)
        self.case = fixture.FutuSimulationContracts()
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.handler = adapter_module.make_order_handler(self.case.adapter)

    def response(self):
        response = Trd_UpdateOrder_pb2.Response(retType=RET_OK)
        header = response.s2c.header
        header.accID = 123
        header.trdEnv = enum_number(TrdEnv, TrdEnv.SIMULATE)
        header.trdMarket = enum_number(TrdMarket, TrdMarket.US)
        order = response.s2c.order
        order.trdSide = enum_number(TrdSide, TrdSide.BUY)
        order.orderType = enum_number(OrderType, OrderType.NORMAL)
        order.orderStatus = enum_number(OrderStatus, OrderStatus.SUBMITTED)
        order.orderID, order.orderIDEx = 987, '987'
        order.code, order.name, order.qty, order.price = 'AMD', 'AMD FIXTURE', 1, 10
        order.createTime = order.updateTime = '2026-09-13 12:00:00'
        order.fillQty, order.fillAvgPrice = 0, 0
        order.secMarket = Trd_Common_pb2.TrdSecMarket_US
        order.trdMarket = enum_number(TrdMarket, TrdMarket.US)
        order.timeInForce = enum_number(TimeInForce, TimeInForce.DAY)
        order.remark = self.case.store._row('one')['client_id']
        self.assertTrue(response.IsInitialized())
        # Exercise actual protobuf serialization as well as SDK DataFrame decoding.
        return Trd_UpdateOrder_pb2.Response.FromString(response.SerializeToString())

    def test_real_decoder_has_no_account_column_and_preserves_header(self):
        ret, data = self.handler.on_recv_rsp(self.response())
        self.assertEqual(ret, RET_OK)
        self.assertNotIn('acc_id', data.columns)
        envelope = self.case.adapter.callbacks.get_nowait()
        self.assertEqual(envelope['header'], dict(acc_id='123', trd_env='SIMULATE', trd_market='US'))
        self.assertEqual(envelope['protocol_header']['accID'], '123')
        self.assertEqual(envelope['order']['code'], 'US.AMD')
        self.assertNotIn('acc_id', envelope['order'])

    def test_real_decoded_callback_before_sync_response_reaches_durable_store(self):
        def callback(_fixture):
            ret, _ = self.handler.on_recv_rsp(self.response())
            self.assertEqual(ret, RET_OK)
        self.case.ctx.callback = callback
        self.case.submit()
        events = [(r[0], json.loads(r[1])) for r in self.case.store.db.execute('SELECT kind,payload FROM events ORDER BY sequence')]
        kinds = [kind for kind, _ in events]
        self.assertLess(kinds.index('FUTU_ORDER_CALLBACK_ENVELOPE'), kinds.index('FUTU_SYNC_RESPONSE'))
        self.assertEqual(self.case.store._row('one')['broker_id'], '987')
        self.assertEqual(self.case.store.accounting_pending(), ['987'])
        self.assertEqual(len(self.case.ctx.sent), 1)

    def test_missing_header_account_fails_closed_without_profile_fallback(self):
        response = self.response()
        response.s2c.header.ClearField('accID')
        self.assertEqual(self.handler.on_recv_rsp(response)[0], RET_ERROR)
        with self.assertRaisesRegex(adapter_module.Error, 'callback_decode_or_header_invalid'):
            self.case.adapter.drain_callbacks(self.case.store)
        self.assertEqual(self.case.ctx.sent, [])

    def test_wrong_header_account_environment_or_market_stops(self):
        changes = [('accID', 124), ('trdEnv', enum_number(TrdEnv, TrdEnv.REAL)),
                   ('trdMarket', enum_number(TrdMarket, TrdMarket.HK))]
        for field, value in changes:
            with self.subTest(field=field):
                response = self.response()
                setattr(response.s2c.header, field, value)
                self.handler.on_recv_rsp(response)
                with self.assertRaisesRegex(adapter_module.Error, 'callback_account_or_environment_mismatch'):
                    self.case.adapter.drain_callbacks(self.case.store)
        self.assertEqual(self.case.ctx.sent, [])

    def test_sdk_decode_failure_is_not_silently_dropped(self):
        response = self.response()
        response.retType = RET_ERROR
        response.retMsg = 'synthetic failure'
        self.assertEqual(self.handler.on_recv_rsp(response)[0], RET_ERROR)
        with self.assertRaisesRegex(adapter_module.Error, 'callback_decode_or_header_invalid'):
            self.case.adapter.drain_callbacks(self.case.store)

    def test_row_market_cannot_contradict_the_header(self):
        response = self.response()
        response.s2c.order.trdMarket = enum_number(TrdMarket, TrdMarket.HK)
        self.handler.on_recv_rsp(response)
        with self.assertRaisesRegex(adapter_module.Error, 'callback_account_or_environment_mismatch'):
            self.case.adapter.drain_callbacks(self.case.store)

    def test_actual_cancel_decoder_retains_environment_and_exact_order_id(self):
        response = Trd_ModifyOrder_pb2.Response(retType=RET_OK)
        response.s2c.header.CopyFrom(self.response().s2c.header)
        response.s2c.orderID = 987
        response.s2c.orderIDEx = '987'
        self.assertTrue(response.IsInitialized())
        decoded = ModifyOrder.unpack_rsp(Trd_ModifyOrder_pb2.Response.FromString(response.SerializeToString()))
        self.assertEqual(decoded, (RET_OK, '', [dict(trd_env='SIMULATE', order_id='987')]))


if __name__ == '__main__':
    unittest.main()
