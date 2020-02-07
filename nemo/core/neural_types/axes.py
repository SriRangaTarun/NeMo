# ! /usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2019, NVIDIA CORPORATION. All rights reserved.
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

__all__ = ['AxisKindAbstract', 'AxisKind', 'AxisType']

from enum import Enum
from typing import Optional


class AxisKindAbstract(Enum):
    """This is an abstract Enum to represents what does varying axis dimension mean.
    In practice, you will almost always use AxisKind Enum. This Enum should be inherited by
    your OWN Enum if you aren't satisfied with AxisKind. Then your own Enum can be used
    instead of AxisKind."""

    pass


class AxisKind(AxisKindAbstract):
    """This Enum represents what does varying axis dimension mean.
    For example, does this dimension correspond to width, batch, time, etc."""

    Batch = 0
    Time = 1
    Dimension = 2
    Width = 3
    Height = 4

    def __str__(self):
        return str(self.name).lower()

    @staticmethod
    def from_str(label):
        """Returns AxisKind instance based on short string representation"""
        _label = label.lower().strip()
        if _label == "b" or _label == "n" or _label == "batch":
            return AxisKind.Batch
        elif _label == "t" or _label == "time":
            return AxisKind.Time
        elif _label == "d" or _label == "c" or _label == "channel":
            return AxisKind.Dimension
        elif _label == "w" or _label == "width":
            return AxisKind.Width
        elif _label == "h" or _label == "height":
            return AxisKind.Height
        else:
            raise ValueError(f"Can't create AxisKind from {label}")


class AxisType(object):
    """This class represents axis semantics and (optionally) it's dimensionality
       Args:
           kind (AxisKindAbstract):
           size (int, optional):
           is_list (bool, default=False):
    """

    def __init__(self, kind: AxisKindAbstract, size: Optional[int] = None, is_list=False):
        if size is not None and is_list:
            raise ValueError("The axis can't be list and have a fixed size")
        self.kind = kind
        self.size = size
        self.is_list = is_list