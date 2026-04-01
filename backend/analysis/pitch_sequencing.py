"""
Pitch Sequencing Analysis — v2 stub.

This module will implement count-to-count pitch transition analysis,
pitch-to-pitch chain modeling, and sequencing tendencies by game situation.

Planned v2 features:
- count_transition_matrix(df): Returns a matrix of pitch type probabilities
  conditioned on the current count (e.g., 0-0 -> FF 45%, SL 30%, CH 25%).
- pitch_chain_analysis(df): Identifies common 2- and 3-pitch sequences
  (e.g., FF -> SL setup patterns, FF -> FF -> CH strikeout sequences).
- situational_sequencing(df, situation): Pitch type probabilities conditioned
  on game situation (RISP, two outs, first pitch of AB, etc.).
- sequencing_deviation(df_live, df_blended_norm): Flags in-game deviations
  from a pitcher's typical sequencing patterns.

Not implemented in v1. Do not add logic here until v2 is scoped.
"""
