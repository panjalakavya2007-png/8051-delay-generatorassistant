# 8051 Delay Generator Assistant

A Python web application for generating 8051 timer calculations,
assembly code and illustrative timing diagrams.

## Features
- Natural-language delay input
- Timer 0 and Timer 1
- Modes 0, 1 and 2
- TMOD, TH and TL calculations
- Assembly code generation
- Timing diagram visualization

## Run locally
Install dependencies:

pip install -r requirements.txt

Run the app:

streamlit run app.py

## Assumptions
Calculations assume a classic 12-clock 8051.
Timer overflow intervals exclude software execution overhead.
