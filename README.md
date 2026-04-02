---
title: Ticket Triage Env
emoji: 🎫
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: apache-2.0
tags:
  - openenv
  - reinforcement-learning
  - customer-support
---

# Ticket Triage Env — OpenEnv Environment

A customer support ticket triage environment where an LLM agent classifies,
prioritizes, and drafts responses to real-world support tickets.

## Tasks

| Task | Difficulty | What agent must do |
|------|-----------|-------------------|
| `classify` | Easy | Identify ticket category (billing/technical/shipping/general) |
| `triage` | Medium | Category + priority + department |
| `resolve` | Hard | Write empathetic draft response covering required key points |

## Reward Function

- **classify**: 1.0 correct / 0.0 wrong
- **triage**: 0.4×category + 0.4×priority + 0.2×department
- **resolve**: fraction of required response key-points covered

## Running Baseline
```bash
export IMAGE_NAME=registry.hf.space/EnoDev88-ticket-triage-env:latest
export HF_TOKEN=hf_xxxx
export TICKET_TRIAGE_TASK=classify
python inference.py
```
