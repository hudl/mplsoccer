"""
===================
Tracking formations
===================
This example shows how to plot each team's average formation as a network from tracking
data loaded with `kloppy <https://kloppy.pysport.org>`_. It uses the
`Metrica Sports open data <https://github.com/metrica-sports/sample-data>`_.

We average the players' positions over the first half and join the average positions
with a Delaunay triangulation using ``pitch.triplot``.

"""

import matplotlib.pyplot as plt
import pandas as pd
from kloppy import metrica

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
# before converting to a DataFrame.
# Each row is a frame with the columns ``<player_id>_x`` and ``<player_id>_y``.

step = round(frame_rate)
sampled = tracking.filter(
    lambda frame: frame.period.id == 1 and frame.frame_id % step == 0
)
frames = sampled.to_df()
print(len(frames), "frames converted to a DataFrame")

##############################################################################
# Average the player positions
# ----------------------------
# The average position of each player is the mean of their ``x`` and ``y`` columns.
# This doesn't handle substitutions or red cards, but it does remove empty rows.


def get_average_positions(frames, team):
    """Return the average position of each player on the pitch for every frame."""
    ids = [
        player.player_id
        for player in team.players
        if frames[f"{player.player_id}_x"].notna().all()
    ]
    return pd.DataFrame(
        {
            "id": ids,
            "x": [frames[f"{i}_x"].mean() for i in ids],
            "y": [frames[f"{i}_y"].mean() for i in ids],
        }
    )


home_positions = get_average_positions(frames, home)
away_positions = get_average_positions(frames, away)
print(len(home_positions), "home players,", len(away_positions), "away players")
home_positions.head()

##############################################################################
# Plot the formations
# -------------------
# ``pitch.triplot`` draws the Delaunay triangulation of the average positions,
# which links each player to their neighbours.
# We plot each team on its own pitch using ``pitch.grid``.
# The Metrica pitch dimensions are 105 x 68 meters for this game.
# The teams attack in opposite directions in the first half,
# so Team A attacks towards the left and Team B towards the right.

pitch = Pitch(
    pitch_type="metricasports",
    pitch_length=105,
    pitch_width=68,
    line_color="#c7d5cc",
    pitch_color="#22312b",
    line_zorder=1,
)

HOME_COLOR, AWAY_COLOR = "#e63946", "#4895ef"

fig, axs = pitch.grid(
    ncols=2,
    figheight=6,
    grid_width=0.95,
    grid_height=0.8,
    title_height=0.1,
    endnote_height=0,
    endnote_space=0,
    axis=False,
)
fig.set_facecolor("#22312b")

for ax, team, positions, color in zip(
    axs["pitch"],
    (home, away),
    (home_positions, away_positions),
    (HOME_COLOR, AWAY_COLOR),
):
    pitch.triplot(positions.x, positions.y, ax=ax, color="#c7d5cc", lw=1.5, zorder=2)
    pitch.scatter(
        positions.x, positions.y, s=400, color=color, ec="white", zorder=3, ax=ax
    )
    ax.set_title(team.name, color="white", fontsize=16)

axs["title"].text(
    0.5,
    0.5,
    "Average formations, first half",
    color="white",
    fontsize=20,
    ha="center",
    va="center",
)
plt.show()
