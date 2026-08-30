#!/bin/bash
# PROTOTYPE — temporary hook logger for the wayfinder signal experiment.
# Appends every hook payload to /tmp/claude-display-exp/hooks.jsonl with a timestamp.
mkdir -p /tmp/claude-display-exp
jq -c '. + {logged_at: (now)}' >> /tmp/claude-display-exp/hooks.jsonl
