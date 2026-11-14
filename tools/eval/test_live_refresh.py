"""Session-refresh boundaries and GUI stop races; no audio devices or GPU used."""
import json
from pathlib import Path
import queue
import sys
import unittest
import weakref
from unittest.mock import Mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gui.__main__ import create_app, cleanup_qt_styles
APP = create_app([])
from gui.app import Config, MainWindow
from gui.live import LiveError, LiveMonitor
from gui.audio import MicStream, SpeakerStream


class Mic:
    rate, level, dropped, name = 22050, 0, 0, 'test microphone'

    def __init__(self):
        self.active, self.closed = True, 0
        self.blocks = queue.Queue()
        for _ in range(8):
            self.blocks.put(np.zeros(2646, np.float32))

    def close(self):
        self.closed += 1
        self.active = False


class Speaker:
    rate, name, buffered_seconds, latency = 22050, 'discard output', 0, 0

    def __init__(self):
        self.active, self.closed, self.writes = True, 0, []

    def write(self, samples):
        self.writes.append(samples.copy())

    def close(self):
        self.closed += 1
        self.active = False


class WebSocket:
    def __init__(self, fail_finish=False):
        self.replies = [json.dumps({'format':'s16le', 'sample_rate':22050,
                                    'frame_samples':2646, 'lookahead_samples':2304})]
        self.payloads, self.closed, self.fail_finish = [], 0, fail_finish

    def send(self, data):
        if data == 'finish':
            if self.fail_finish:
                raise LiveError('tail could not be returned')
            self.replies.extend((bytes(2304*2), ''))
        else:
            self.payloads.append(data)
            self.replies.append(data[:-2304*2] if len(self.payloads)==1 else data)

    def recv(self, timeout):
        return self.replies.pop(0)

    def close(self):
        self.closed += 1


class RefreshTests(unittest.TestCase):
    def run_monitor(self, limit, stop_at=None, abort=False, fail_finish=False, prime=0):
        mic, speaker, ws = Mic(), Speaker(), WebSocket(fail_finish)
        stops, ticks = [], []

        def tick(stats):
            ticks.append(stats)
            if stats['frames'] == stop_at:
                monitor.request_stop(abort=abort)

        monitor = LiveMonitor('unused', mic, speaker, lambda _: None, tick,
                              lambda *args: stops.append(args), restart_after_packets=limit)
        monitor.frames_sent = prime
        monitor._connect = lambda: ws
        monitor.run()
        self.assertEqual((mic.closed, speaker.closed, ws.closed), (1,1,1))
        return monitor, ws, stops, ticks

    def test_exact_boundary_and_complete_tail(self):
        m, ws, stops, _ = self.run_monitor(3)
        self.assertEqual(len(ws.payloads), 3)
        self.assertEqual(stops, [('refresh','')])
        self.assertEqual(sum(m.packet_samples), 3*2646)

    def test_production_thresholds(self):
        self.assertEqual(Config().live_restart_packets, 3000)
        for limit in (3000,5000):
            m, ws, stops, _ = self.run_monitor(limit, prime=limit-2)
            self.assertEqual(len(ws.payloads), 2)
            self.assertEqual(m.frames_sent, limit)
            self.assertEqual(stops, [('refresh','')])

    def test_finished_monitor_has_no_callback_reference_cycle(self):
        monitor, _, _, _ = self.run_monitor(3)
        ref = weakref.ref(monitor)
        del monitor
        self.assertIsNone(ref())

    def test_closed_device_wrappers_release_callback_cycles(self):
        class NativeStream:
            active = True
        for cls in (MicStream,SpeakerStream):
            owner = cls.__new__(cls)
            native = NativeStream()
            native.callback = owner._callback
            owner._stream = native
            ref = weakref.ref(native)
            del native
            from unittest.mock import patch
            with patch('gui.audio._close_stream', lambda _: None):
                owner.close()
            self.assertIsNone(ref())
            self.assertFalse(owner.active)

    def test_manual_stop_at_boundary_cancels_restart(self):
        for abort in (False,True):
            _, _, stops, _ = self.run_monitor(3, stop_at=3, abort=abort)
            self.assertEqual(stops, [('user','')])

    def test_error_during_finish_does_not_restart_forever(self):
        _, _, stops, _ = self.run_monitor(3, fail_finish=True)
        self.assertEqual(stops[0][0], 'error')

    def test_disabled_refresh_keeps_normal_stop(self):
        _, ws, stops, _ = self.run_monitor(0, stop_at=6)
        self.assertEqual(len(ws.payloads), 6)
        self.assertEqual(stops, [('user','')])

    def window(self):
        w = Mock()
        w.live, w._live_restart, w._live_auto_refreshes, w._closing = object(), False, 0, False
        w.live_switch.isChecked.return_value = True
        return w

    def test_gui_refresh_preserves_running_switch(self):
        w = self.window()
        MainWindow._on_live_stopped(w, w.live, 'refresh', '')
        w._start_live.assert_called_once_with()
        w.live_switch.setChecked.assert_not_called()
        self.assertEqual(w._live_auto_refreshes, 1)

    def test_gui_stop_or_exit_prevents_restart(self):
        for stopped, closing in ((True,False),(False,True)):
            w = self.window()
            w.live_switch.isChecked.return_value = not stopped
            w._closing = closing
            MainWindow._on_live_stopped(w, w.live, 'refresh', '')
            w._start_live.assert_not_called()
            self.assertEqual(w._live_auto_refreshes, 0)

    def test_gui_stale_callback_cannot_restart_new_session(self):
        w = self.window()
        current = w.live
        MainWindow._on_live_stopped(w, object(), 'refresh', '')
        self.assertIs(w.live, current)
        w._start_live.assert_not_called()

    def test_gui_manual_voice_change_still_restarts(self):
        w = self.window()
        w._live_restart = True
        MainWindow._on_live_stopped(w, w.live, 'user', '')
        w._start_live.assert_called_once_with()
        self.assertEqual(w._live_auto_refreshes, 0)


if __name__ == '__main__':
    try:
        unittest.main(verbosity=2)
    finally:
        cleanup_qt_styles()
