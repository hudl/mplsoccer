"""
===============
Tracking frames
===============
This example shows how to plot a frame of tracking data loaded with
`kloppy <https://kloppy.pysport.org>`_. It uses the
`Metrica Sports open data <https://github.com/metrica-sports/sample-data>`_.

First we plot the player positions in a single frame, then add a trace of the
players' movement over the previous two seconds, and finally add an event
from the Metrica event data to the frame.

"""

import matplotlib.pyplot as plt
import pandas as pd
from kloppy import metrica

from mplsoccer import Pitch

##############################################################################
# Load the data
# -------------
# Sample game 3 from Metrica provides both tracking and event data.

BASE_URL = (
    "https://raw.githubusercontent.com/metrica-sports/sample-data/"
    "master/data/Sample_Game_3/"
)
tracking = metrica.load_open_data(match_id=3, coordinates="metrica")
events = metrica.load_event(
    event_data=BASE_URL + "Sample_Game_3_events.json",
    meta_data=BASE_URL + "Sample_Game_3_metadata.xml",
    coordinates="metrica",
)

home, away = tracking.metadata.teams
home_ids = [player.player_id for player in home.players]
away_ids = [player.player_id for player in away.players]
frame_rate = tracking.metadata.frame_rate
print(home.name, "vs", away.name, "|", frame_rate, "frames per second")

##############################################################################
# Get frames as DataFrames
# ------------------------
# We filter the kloppy dataset down to the frames we need
# and then convert to a DataFrame.
# Each row is a frame with the columns ``<player_id>_x``, ``<player_id>_y``,
# ``ball_x`` and ``ball_y``.


def get_frames(period_id, start, end):
    """Return the frames between two timestamps (in seconds) as a DataFrame."""
    start, end = pd.Timedelta(seconds=start), pd.Timedelta(seconds=end)
    subset = tracking.filter(
        lambda frame: frame.period.id == period_id and start <= frame.timestamp <= end
    )
    return subset.to_df()


# 1 minute into the first half
frames = get_frames(period_id=1, start=60, end=60)
print(len(frames), "frame converted to a DataFrame")
frames[["period_id", "timestamp", "frame_id", "ball_x", "ball_y"]]

##############################################################################
# Reshape to one row per player
# -----------------------------
# The wide frames are easier to plot with one row per player per frame.
# We make a small table of ``frame_id``, ``x``, ``y`` and ``id`` for each player,
# join the tables together and drop the missing positions
# (players who are not on the pitch).


def get_players(frames, ids):
    """Return the players' positions with one row per player per frame."""
    players = [
        frames[["frame_id", f"{i}_x", f"{i}_y"]]
        .rename(columns={f"{i}_x": "x", f"{i}_y": "y"})
        .assign(id=i)
        for i in ids
    ]
    return pd.concat(players, ignore_index=True).dropna()


home_players = get_players(frames, home_ids)
away_players = get_players(frames, away_ids)
home_players.head()

##############################################################################
# Plot the positions
# ------------------
# The Metrica pitch dimensions are 105 x 68 meters for this game.

pitch = Pitch(
    pitch_type="metricasports",
    pitch_length=105,
    pitch_width=68,
    line_color="#c7d5cc",
    pitch_color="#22312b",
    line_zorder=1,
)

HOME_COLOR, AWAY_COLOR = "#e63946", "#4895ef"
PLAYER_KWARGS = {"s": 150, "ec": "white", "zorder": 3}
BALL_KWARGS = {"s": 70, "color": "white", "ec": "black", "zorder": 4}

fig, ax = pitch.draw(figsize=(12, 8))
pitch.scatter(
    home_players.x,
    home_players.y,
    color=HOME_COLOR,
    label=home.name,
    ax=ax,
    **PLAYER_KWARGS,
)
pitch.scatter(
    away_players.x,
    away_players.y,
    color=AWAY_COLOR,
    label=away.name,
    ax=ax,
    **PLAYER_KWARGS,
)
pitch.scatter(frames.ball_x, frames.ball_y, ax=ax, **BALL_KWARGS)
ax.legend(loc="upper center", ncol=2, frameon=False, labelcolor="white")
plt.show()

##############################################################################
# Add a trace of the last two seconds
# -----------------------------------
# We get the previous two seconds (50 frames at 25 frames per second) as a small
# DataFrame and group by player id to draw each player's path with ``pitch.lines``.
# ``comet=True`` makes the line thicker towards the end and
# ``transparent=True`` fades the older part of the trace.

TRACE_SECONDS = 2
TRACE_KWARGS = {
    "comet": True,
    "transparent": True,
    "alpha_start": 0.05,
    "alpha_end": 0.8,
    "lw": 6,
    "zorder": 2,
}


def plot_trace(players, color, ax):
    """Plot a comet trace for each player id."""
    for _, player in players.groupby("id"):
        x, y = player.x.to_numpy(), player.y.to_numpy()
        pitch.lines(x[:-1], y[:-1], x[1:], y[1:], color=color, ax=ax, **TRACE_KWARGS)


end = frames.timestamp.iloc[0].total_seconds()
trace_frames = get_frames(period_id=1, start=end - TRACE_SECONDS, end=end)

home_trace = get_players(trace_frames, home_ids)
away_trace = get_players(trace_frames, away_ids)

fig, ax = pitch.draw(figsize=(12, 8))
plot_trace(home_trace, HOME_COLOR, ax)
plot_trace(away_trace, AWAY_COLOR, ax)
pitch.scatter(home_players.x, home_players.y, color=HOME_COLOR, ax=ax, **PLAYER_KWARGS)
pitch.scatter(away_players.x, away_players.y, color=AWAY_COLOR, ax=ax, **PLAYER_KWARGS)
pitch.scatter(frames.ball_x, frames.ball_y, ax=ax, **BALL_KWARGS)
plt.show()

##############################################################################
# Add an event to the frame
# -------------------------
# We choose the goal scored by Team B in the first half.
# The event and tracking timestamps are both relative to the start of the period,
# so we use the event timestamp to filter the tracking frames.

goal = next(
    event
    for event in events.events
    if event.event_type.name == "SHOT"
    and event.result.name == "GOAL"
    and event.period.id == 1
)
goal_time = goal.timestamp.total_seconds()

goal_frames = get_frames(period_id=1, start=goal_time - TRACE_SECONDS, end=goal_time)
goal_frame = goal_frames.iloc[-1]
home_trace = get_players(goal_frames, home_ids)
away_trace = get_players(goal_frames, away_ids)
# the players in the goal frame are the last row of each player's trace
home_goal = home_trace[home_trace.frame_id == goal_frame.frame_id]
away_goal = away_trace[away_trace.frame_id == goal_frame.frame_id]
shooter = pd.concat([home_goal, away_goal]).query("id == @goal.player.player_id")

fig, ax = pitch.draw(figsize=(12, 8))
plot_trace(home_trace, HOME_COLOR, ax)
plot_trace(away_trace, AWAY_COLOR, ax)
pitch.scatter(home_goal.x, home_goal.y, color=HOME_COLOR, ax=ax, **PLAYER_KWARGS)
pitch.scatter(away_goal.x, away_goal.y, color=AWAY_COLOR, ax=ax, **PLAYER_KWARGS)
pitch.scatter(goal_frame.ball_x, goal_frame.ball_y, ax=ax, **BALL_KWARGS)

# highlight the shooter and mark the shot location
pitch.scatter(
    shooter.x,
    shooter.y,
    s=450,
    facecolor="none",
    edgecolor="gold",
    lw=3,
    zorder=5,
    ax=ax,
)
pitch.scatter(
    goal.coordinates.x,
    goal.coordinates.y,
    marker="*",
    s=300,
    color="gold",
    ec="black",
    zorder=6,
    ax=ax,
)
minutes, seconds = divmod(int(goal_time), 60)
ax.set_title(
    f"Goal: {goal.player.name} ({goal.team.name}) at {minutes}:{seconds:02d}",
    color="white",
    fontsize=16,
)
fig.set_facecolor("#22312b")
plt.show()
