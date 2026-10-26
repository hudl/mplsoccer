""" Python module containing a helper function to save Matplotlib animations as video."""

from pathlib import Path

import matplotlib as mpl
from matplotlib import animation

__all__ = ['save_animation']

_PILLOW_SUFFIXES = {'.gif', '.webp'}
_FFMPEG_SUFFIXES = {'.mp4', '.m4v', '.mov', '.mkv', '.webm'}
_FASTSTART_SUFFIXES = {'.mp4', '.m4v', '.mov'}
# newer ffmpeg versions reject the default RGBA input pixel format for VP9
_WEBM_ARGS = ['-pix_fmt', 'yuv420p', '-row-mt', '1']
# without a bitrate, libvpx-vp9 needs a constant quality setting to avoid a very low default
_WEBM_QUALITY_ARGS = ['-b:v', '0', '-crf', '33']


def _find_ffmpeg():
    """ Return the path to an ffmpeg executable or None if it is not found.

    Uses the ffmpeg set in rcParams['animation.ffmpeg_path'] (by default ffmpeg on the PATH)
    and falls back to the ffmpeg executable bundled with the optional imageio-ffmpeg package.
    """
    if animation.FFMpegWriter.isAvailable():
        return animation.FFMpegWriter.bin_path()
    try:
        import imageio_ffmpeg  # pylint: disable=import-outside-toplevel
    except ImportError:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except RuntimeError:
        return None


def save_animation(anim, filename, fps=25, dpi=100, *, bitrate=None, metadata=None,
                   extra_args=None, **kwargs):
    """ Save a Matplotlib animation to a video (.mp4, .m4v, .mov, .mkv, .webm)
    or an animated image (.gif, .webp).

    Videos are encoded with ffmpeg. The ffmpeg in ``rcParams['animation.ffmpeg_path']``
    (by default ffmpeg on the PATH) is used if it is available. Otherwise, the ffmpeg
    bundled with the optional ``imageio-ffmpeg`` package is used, which you can install
    with ``pip install "mplsoccer[video]"``. The output uses settings that play in
    browsers and QuickTime: H.264 with yuv420p for .mp4/.m4v/.mov/.mkv and VP9 with
    yuv420p for .webm. Animated images (.gif, .webp) are saved with Pillow, so they
    do not need ffmpeg.

    Parameters
    ----------
    anim : matplotlib.animation.Animation
        The animation to save, e.g. a matplotlib.animation.FuncAnimation.
    filename : str or path-like
        The output filename. The suffix sets the format.
    fps : int, default 25
        The frame rate of the output in frames per second.
        Most tracking data is at 25 frames per second.
    dpi : float, default 100
        The resolution of the output in dots per inch.
        The output size in pixels is the figure size in inches multiplied by the dpi.
    bitrate : int, default None
        The bitrate of the video in kilobits per second. The default, None,
        uses rcParams['animation.bitrate']. If no bitrate is set, .webm videos use
        constant quality encoding. Not used for .gif and .webp.
    metadata : dict, default None
        Metadata to include in the video, e.g. {'title': 'Match clip'}.
        Not used for .gif and .webp.
    extra_args : list of str, default None
        Extra command-line arguments passed to ffmpeg, e.g. ['-crf', '18'] for a higher
        quality .mp4. These are added after the default arguments, so they can override them,
        e.g. ['-vcodec', 'libx265'] to change the codec. The default, None,
        uses rcParams['animation.ffmpeg_args']. Not used for .gif and .webp.
    **kwargs : The keyword arguments savefig_kwargs, extra_anim, and progress_callback
        are passed on to matplotlib.animation.Animation.save.

    Raises
    ------
    ValueError
        If the filename suffix is not a supported format.
    RuntimeError
        If the format needs ffmpeg and ffmpeg is not found.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from matplotlib.animation import FuncAnimation
    >>> from mplsoccer import Pitch, save_animation
    >>> pitch = Pitch()
    >>> fig, ax = pitch.draw()
    >>> ball, = ax.plot([], [], 'o')
    >>> def animate(i):
    ...     ball.set_data([i], [40])
    ...     return ball,
    >>> anim = FuncAnimation(fig, animate, frames=120)
    >>> save_animation(anim, 'ball.mp4')  # doctest: +SKIP
    """
    suffix = Path(filename).suffix.lower()
    if suffix in _PILLOW_SUFFIXES:
        anim.save(filename, writer=animation.PillowWriter(fps=fps), dpi=dpi, **kwargs)
        return

    if suffix not in _FFMPEG_SUFFIXES:
        supported = ', '.join(sorted(_FFMPEG_SUFFIXES | _PILLOW_SUFFIXES))
        raise ValueError(f'Unsupported file format "{suffix}". Use one of: {supported}.')

    ffmpeg_path = _find_ffmpeg()
    if ffmpeg_path is None:
        raise RuntimeError('ffmpeg is required to save animations as video, but it was not '
                           'found. Install it with \'pip install "mplsoccer[video]"\', or '
                           'install ffmpeg and add it to the PATH. Alternatively, save as a '
                           '.gif or .webp file, which does not need ffmpeg.')

    if suffix == '.webm':
        # set the codec explicitly as older Matplotlib versions (and uppercase suffixes)
        # otherwise use the default h264 codec, which WebM does not support
        codec = 'libvpx-vp9'
        args = list(_WEBM_ARGS)
        if bitrate is None and mpl.rcParams['animation.bitrate'] == -1:
            args.extend(_WEBM_QUALITY_ARGS)
    else:
        # the default h264 codec makes Matplotlib round the frame size to even pixels
        # and add the yuv420p pixel format, which libx264 needs for browser playback
        codec = 'h264'
        # move the index to the start of the file so browsers can play it while it downloads
        args = ['-movflags', '+faststart'] if suffix in _FASTSTART_SUFFIXES else []
    if extra_args is None:
        extra_args = mpl.rcParams['animation.ffmpeg_args']
    args.extend(extra_args)

    with mpl.rc_context({'animation.ffmpeg_path': ffmpeg_path}):
        writer = animation.FFMpegWriter(fps=fps, codec=codec, bitrate=bitrate,
                                        metadata=metadata, extra_args=args)
        anim.save(filename, writer=writer, dpi=dpi, **kwargs)
