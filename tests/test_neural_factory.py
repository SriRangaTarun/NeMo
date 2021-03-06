# ! /usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2020 NVIDIA. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

import nemo
from tests.common_setup import NeMoUnitTest


class TestNeuralFactory(NeMoUnitTest):
    def test_create_single_module(self):
        instance = self.nf.get_module(name="TaylorNet", collection="toys", params={"dim": 4})
        self.assertTrue(isinstance(instance, nemo.backends.pytorch.tutorials.TaylorNet))

    def test_create_simple_graph(self):
        dl = self.nf.get_module(
            name="RealFunctionDataLayer", collection="toys", params={"n": 10000, "batch_size": 128},
        )
        fx = self.nf.get_module(name="TaylorNet", collection="toys", params={"dim": 4})
        loss = self.nf.get_module(name="MSELoss", collection="toys", params={})

        x, y = dl()
        y_pred = fx(x=x)
        _ = loss(predictions=y_pred, target=y)
