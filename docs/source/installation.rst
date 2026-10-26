============
Installation
============

The library uses Python 3.6 onwards.

To install the latest version via ``pip`` ::

    pip install -U mplsoccer

To install the latest version via ``Anaconda`` ::

    conda install -c conda-forge mplsoccer

You may also need to upgrade mplsoccer dependencies such as seaborn.

To save animations as video (e.g. .mp4) with ``save_animation`` you need ffmpeg.
If you do not have ffmpeg installed, you can install it with the optional
``video`` dependencies, which include a bundled ffmpeg ::

    pip install -U "mplsoccer[video]"
