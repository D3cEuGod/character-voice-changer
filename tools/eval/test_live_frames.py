"""Exercise packets shorter than lookahead without loading neural models."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.live import LiveVoice


class Identity:
    context_samples, strength = 22050, 0

    def __init__(self,*args):
        pass

    def render(self,window,count):
        return window.copy()


class FrameTests(unittest.TestCase):
    @patch('backend.live.CharacterModel',Identity)
    def test_no_audio_lost_or_duplicated_at_any_startup_length(self):
        rng=np.random.default_rng(71)
        for frame in (1764,2205,2646,4410,8192):
            for lookahead in (1024,2304):
                for count in (0,1,2,3,12):
                    with self.subTest(frame=frame,lookahead=lookahead,count=count):
                        x=rng.uniform(-.2,.2,size=count*frame).astype(np.float32)
                        voice=LiveVoice('unused',0,lookahead)
                        parts=[voice.process(x[i:i+frame]) for i in range(0,len(x),frame)]
                        parts.append(voice.flush())
                        y=np.concatenate(parts)
                        self.assertEqual(len(x),len(y))
                        np.testing.assert_allclose(y,x,atol=1e-7)
                        self.assertEqual(len(voice.flush()),0)


if __name__=='__main__':
    unittest.main(verbosity=2)
