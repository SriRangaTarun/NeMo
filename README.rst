.. image:: http://www.repostatus.org/badges/latest/active.svg
  :target: http://www.repostatus.org/#active
  :alt: Project Status: Active – The project has reached a stable, usable state and is being actively developed.

.. image:: https://img.shields.io/badge/documentation-github.io-blue.svg
  :target: https://nvidia.github.io/NeMo/
  :alt: NeMo documentation on GitHub pages

.. image:: https://img.shields.io/badge/License-Apache%202.0-brightgreen.svg
  :target: https://github.com/NVIDIA/NeMo/blob/master/LICENSE
  :alt: NeMo core license and license for collections in this repo

.. image:: https://img.shields.io/lgtm/grade/python/g/NVIDIA/NeMo.svg?logo=lgtm&logoWidth=18
  :target: https://lgtm.com/projects/g/NVIDIA/NeMo/context:python
  :alt: Language grade: Python

.. image:: https://img.shields.io/lgtm/alerts/g/NVIDIA/NeMo.svg?logo=lgtm&logoWidth=18
  :target: https://lgtm.com/projects/g/NVIDIA/NeMo/alerts/
  :alt: Total alerts

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
  :target: https://github.com/psf/black
  :alt: Code style: black



NVIDIA Neural Modules: NeMo
===========================

NeMo (Neural Modules) is a toolkit for creating AI applications using **neural modules** - conceptual blocks of neural networks that take *typed* inputs and produce *typed* outputs. Such modules typically represent data layers, encoders, decoders, language models, loss functions, or methods of combining activations.

NeMo makes it easy to combine and re-use these building blocks while providing a level of semantic correctness checking via its neural type system. As long as two modules have compatible inputs and outputs, it is legal to chain them together.

NeMo's API is designed to be **framework-agnostic**, but currently only PyTorch is supported.

The toolkit comes with extendable collections of pre-built modules for automatic speech recognition (ASR), natural language processing (NLP) and text synthesis (TTS). Furthermore, NeMo provides built-in support for **distributed training** and **mixed precision** on the latest NVIDIA GPUs.

NeMo consists of: 

* **NeMo Core**: fundamental building blocks for all neural models and type system.
* **NeMo collections**: pre-built neural modules for particular domains such as automatic speech recognition (nemo_asr), natural language processing (nemo_nlp) and text synthesis (nemo_tts).


**Introduction**

See `this video <https://nvidia.github.io/NeMo/>`_ for a quick walk-through.

**Requirements**

1) Python 3.6 or 3.7
2) PyTorch 1.2.* or 1.3.* with GPU support
3) (optional for best performance) NVIDIA APEX. Install from here: https://github.com/NVIDIA/apex

**Getting started**

THE LATEST STABLE VERSION OF NeMo is **0.9.0** (which is available via PIP).

**Docker Container**
 NVIDIA `NGC NeMo Toolkit container <https://ngc.nvidia.com/catalog/containers/nvidia:nemo>`_ is now available.

* Pull the docker: ``docker pull nvcr.io/nvidia/nemo:v0.9``
* Run: ``docker run --runtime=nvidia -it --rm -v <nemo_github_folder>:/NeMo --shm-size=8g -p 8888:8888 -p 6006:6006 --ulimit memlock=-1 --ulimit stack=67108864 nvcr.io/nvidia/nemo:v0.9``

If you are using the NVIDIA `NGC PyTorch container <https://ngc.nvidia.com/catalog/containers/nvidia:pytorch>`_ follow these instructions

* Pull the docker: ``docker pull nvcr.io/nvidia/pytorch:19.11-py3``
* Run: ``docker run --runtime=nvidia -it --rm -v <nemo_github_folder>:/NeMo --shm-size=8g -p 8888:8888 -p 6006:6006 --ulimit memlock=-1 --ulimit stack=67108864 nvcr.io/nvidia/pytorch:19.11-py3``

.. code-block:: bash

    pip install nemo-toolkit  # installs NeMo Core
    pip install nemo-asr # installs NeMo ASR collection
    pip install nemo-nlp # installs NeMo NLP collection
    pip install nemo-tts # installs NeMo TTS collection

* DEVELOPMENT: If you'd like to use master branch and/or develop NeMo you can run "reinstall.sh" script.

**Documentation**

`NeMo documentation <https://nvidia.github.io/NeMo/>`_

See `examples/start_here` to get started with the simplest example. The folder `examples` contains several examples to get you started with various tasks in NLP and ASR.


**Tutorials**

* `Speech recognition <https://nvidia.github.io/NeMo/asr/intro.html>`_
* `Natural language processing <https://nvidia.github.io/NeMo/nlp/intro.html>`_
* `Speech Synthesis <https://nvidia.github.io/NeMo/tts/intro.html>`_

**Installing From Github**

If you prefer to use NeMo's latest development version (from GitHub) follow the steps below:

*Note*: For step 2 and 3, if you want to use NeMo in development mode, use: ``pip install -e .`` instead of ``pip install .``

1) Clone the repository ``git clone https://github.com/NVIDIA/NeMo.git``
2) Go to NeMo folder and re-install the toolkit with collections:

.. code-block:: bash
	
    ./reinstall.sh

**Style tests**

.. code-block:: bash

    python setup.py style  # Checks overall project code style and output issues with diff.
    python setup.py style --fix  # Tries to fix error in-place.
    python setup.py style --scope=tests  # Operates within certain scope (dir of file).

**Unittests**

This command runs unittests:

.. code-block:: bash

    ./reinstall.sh
    python -m unittest tests/*.py


Citation
~~~~~~~~

If you are using NeMo please cite the following publication

@misc{nemo2019,
    title={NeMo: a toolkit for building AI applications using Neural Modules},
    author={Oleksii Kuchaiev and Jason Li and Huyen Nguyen and Oleksii Hrinchuk and Ryan Leary and Boris Ginsburg and Samuel Kriman and Stanislav Beliaev and Vitaly Lavrukhin and Jack Cook and Patrice Castonguay and Mariya Popova and Jocelyn Huang and Jonathan M. Cohen},
    year={2019},
    eprint={1909.09577},
    archivePrefix={arXiv},
    primaryClass={cs.LG}
}
