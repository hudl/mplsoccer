""" Test the save_animation function, which saves Matplotlib animations as video."""

import builtins
import subprocess

import matplotlib.pyplot as plt
import pytest
from matplotlib import animation
from PIL import Image

from mplsoccer import Pitch, save_animation
from mplsoccer.animation import _find_ffmpeg

N_FRAMES = 5
FFMPEG = _find_ffmpeg()
needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason='ffmpeg is not available')


@pytest.fixture
def anim():
    pitch = Pitch()
    fig, ax = pitch.draw(figsize=(4, 2.7))
    ball, = ax.plot([], [], 'o')

    def animate(i):
        ball.set_data([i * 10], [40])
        return ball,

    yield animation.FuncAnimation(fig, animate, frames=N_FRAMES, blit=True)
    plt.close(fig)


def probe(path):
    """ Return the codec, pixel format, width, height, and number of frames of a video."""
    result = subprocess.run([FFMPEG, '-i', str(path), '-map', '0:v:0', '-f', 'null', '-'],
                            capture_output=True, text=True, check=True)
    stream = next(line for line in result.stderr.splitlines() if 'Video:' in line)
    frames = int(result.stderr.rsplit('frame=', 1)[1].split()[0])
    return stream, frames


@pytest.mark.parametrize('suffix', ['.gif', '.webp'])
def test_pillow_formats(anim, tmp_path, suffix):
    path = tmp_path / f'clip{suffix}'
    save_animation(anim, path, fps=10, dpi=50)
    with Image.open(path) as img:
        assert img.n_frames == N_FRAMES
        assert img.size == (200, 135)


@needs_ffmpeg
@pytest.mark.parametrize('suffix', ['.mp4', '.mov', '.mkv'])
def test_h264_formats(anim, tmp_path, suffix):
    path = tmp_path / f'clip{suffix}'
    save_animation(anim, path, fps=10, dpi=50)
    stream, frames = probe(path)
    assert 'h264' in stream
    assert 'yuv420p' in stream
    assert frames == N_FRAMES


@needs_ffmpeg
@pytest.mark.parametrize('filename', ['clip.webm', 'clip.WEBM'])
@pytest.mark.parametrize('dpi', [50, 63])
def test_webm(anim, tmp_path, filename, dpi):
    path = tmp_path / filename
    save_animation(anim, path, fps=10, dpi=dpi)
    stream, frames = probe(path)
    assert 'vp9' in stream
    assert 'yuv420p' in stream
    assert frames == N_FRAMES


@needs_ffmpeg
def test_webm_bitrate(anim, tmp_path, monkeypatch):
    calls = []
    real_run = animation.FFMpegWriter._run  # pylint: disable=protected-access

    def spy_run(self):
        calls.append(self._args())  # pylint: disable=protected-access
        real_run(self)

    monkeypatch.setattr(animation.FFMpegWriter, '_run', spy_run)
    save_animation(anim, tmp_path / 'quality.webm', dpi=50)
    save_animation(anim, tmp_path / 'bitrate.webm', dpi=50, bitrate=2000)
    assert '-crf' in calls[0]
    assert '-crf' not in calls[1]
    assert '2000k' in calls[1]


@needs_ffmpeg
def test_rcparams_ffmpeg_args(anim, tmp_path):
    path = tmp_path / 'clip.mkv'
    with plt.rc_context({'animation.ffmpeg_args': ['-metadata', 'comment=from rcParams']}):
        save_animation(anim, path, dpi=50)
    result = subprocess.run([FFMPEG, '-i', str(path)], capture_output=True, text=True,
                            check=False)
    assert 'from rcParams' in result.stderr


@needs_ffmpeg
def test_odd_pixel_size(anim, tmp_path):
    # 4 x 2.7 inches at 50 dpi is 200 x 135 pixels, which libx264 rejects unless rounded
    path = tmp_path / 'clip.mp4'
    save_animation(anim, path, dpi=50)
    stream, frames = probe(path)
    assert 'yuv420p' in stream
    assert ' 200x134' in stream
    assert frames == N_FRAMES


@needs_ffmpeg
def test_extra_args_and_metadata(anim, tmp_path):
    path = tmp_path / 'clip.mp4'
    save_animation(anim, path, dpi=50, bitrate=500, metadata={'title': 'Match clip'},
                   extra_args=['-crf', '18'], savefig_kwargs={'facecolor': 'black'})
    result = subprocess.run([FFMPEG, '-i', str(path)], capture_output=True, text=True,
                            check=False)
    assert 'Match clip' in result.stderr


def test_unsupported_suffix(anim, tmp_path):
    with pytest.raises(ValueError, match='Unsupported file format ".avi"'):
        save_animation(anim, tmp_path / 'clip.avi')


def test_missing_ffmpeg(anim, tmp_path, monkeypatch):
    monkeypatch.setattr(animation.FFMpegWriter, 'isAvailable', classmethod(lambda cls: False))
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == 'imageio_ffmpeg':
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', fake_import)
    with pytest.raises(RuntimeError, match=r'mplsoccer\[video\]'):
        save_animation(anim, tmp_path / 'clip.mp4')
    assert not (tmp_path / 'clip.mp4').exists()
