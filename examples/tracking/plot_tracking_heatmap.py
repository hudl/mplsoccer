"""
================
Tracking heatmap
================
This example shows how to plot a heatmap of a player's positions from tracking data
loaded with `kloppy <https://kloppy.pysport.org>`_. It uses the
`Metrica Sports open data <https://github.com/metrica-sports/sample-data>`_.

We reduce the data to the first half, sample it to one frame per second,
select a single player, and then plot their positions with
``bin_statistic`` and ``heatmap``, a smoothed heatmap and ``kdeplot``.

"""

import matplotlib.pyplot as plt
from kloppy import metrica
from scipy.ndimage import gaussian_filter

from mplsoccer import Pitch

##############################################################################
# Load the data
# -------------
# Sample game 3 from Metrica provides tracking data for both teams.

tracking = metrica.load_open_data(match_id=3, coordinates="metrica")

home, away = tracking.metadata.teams
frame_rate = tracking.metadata.frame_rate
print(home.name, "vs", away.name, "|", frame_rate, "frames per second")

##############################################################################
# Filter and sample the frames
# ----------------------------
# We filter the kloppy dataset to the first half and keep one frame per second
# (every ``frame_rate`` frames) before converting to a DataFrame. This makes
# the data much easier to work with, without losing too much information for the
# heatmap.

step = round(frame_rate)
sampled = tracking.filter(
    lambda frame: frame.period.id == 1 and frame.frame_id % step == 0
)
frames = sampled.to_df()
print(len(frames), "frames converted to a DataFrame")
frames[["period_id", "timestamp", "frame_id", "ball_x", "ball_y"]].head()

##############################################################################
# Select a player
# ---------------
# We take the positions of one home player and drop any missing positions.

player = next(p for p in home.players if p.name == "Player 6")
positions = (
    frames[[f"{player.player_id}_x", f"{player.player_id}_y"]]
    .rename(columns={f"{player.player_id}_x": "x", f"{player.player_id}_y": "y"})
    .dropna()
)
print(player.name, "|", len(positions), "positions")
positions.head()

##############################################################################
# Plot a heatmap
# --------------
# We count the positions in each bin with ``pitch.bin_statistic``
# and plot the result with ``pitch.heatmap``.

pitch = Pitch(
    pitch_type="metricasports",
    pitch_length=105,
    pitch_width=68,
    line_color="#c7d5cc",
    pitch_color="#22312b",
    line_zorder=3,
)
TITLE = f"{player.name} ({home.name}), first half, 1 frame per second"
TITLE_KWARGS = {"color": "white", "fontsize": 16}


def style_colorbar(cbar):
    """Format the colorbar in off-white to match the pitch lines."""
    cbar.outline.set_edgecolor("#c7d5cc")
    cbar.ax.yaxis.set_tick_params(color="#c7d5cc", labelcolor="#c7d5cc")


fig, ax = pitch.draw(figsize=(12, 8))
fig.set_facecolor("#22312b")
stats = pitch.bin_statistic(positions.x, positions.y, statistic="count", bins=(21, 14))
pcm = pitch.heatmap(stats, ax=ax, cmap="hot", edgecolors="#22312b")
style_colorbar(fig.colorbar(pcm, ax=ax, shrink=0.6))
ax.set_title(TITLE, **TITLE_KWARGS)
plt.show()

##############################################################################
# Plot a smoothed heatmap
# -----------------------
# Using finer bins and a gaussian filter gives a smoother surface.

fig, ax = pitch.draw(figsize=(12, 8))
fig.set_facecolor("#22312b")
stats = pitch.bin_statistic(positions.x, positions.y, statistic="count", bins=(50, 33))
stats["statistic"] = gaussian_filter(stats["statistic"], 2)
pcm = pitch.heatmap(stats, ax=ax, cmap="hot", edgecolors="none")
style_colorbar(fig.colorbar(pcm, ax=ax, shrink=0.6))
ax.set_title(TITLE, **TITLE_KWARGS)
plt.show()

##############################################################################
# Plot a kernel density estimate
# ------------------------------
# ``pitch.kdeplot`` estimates the density directly from the positions.

fig, ax = pitch.draw(figsize=(12, 8))
fig.set_facecolor("#22312b")
pitch.kdeplot(
    positions.x,
    positions.y,
    ax=ax,
    fill=True,
    levels=50,
    thresh=0,
    cut=4,
    cmap="hot",
)
ax.set_title(TITLE, **TITLE_KWARGS)
plt.show()
