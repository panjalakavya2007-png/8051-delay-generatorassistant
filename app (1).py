
import re
import math
import os
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="8051 Delay Generator Assistant",
    page_icon="⏱️",
    layout="wide"
)

st.title("⏱️ 8051 Delay Generator Assistant")
st.write(
    "Generate 8051 timer calculations, assembly code, "
    "and timing diagrams automatically."
)

# -------------------------------------------------
# AGENT 1: Interpret the user's natural-language request
# -------------------------------------------------

def interpret_request(text):
    result = {
        "delay_us": None,
        "timer": 0,
        "clock_mhz": 11.0592,
        "mode": 1
    }

    text = text.lower()

    # Extract delay and unit
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(microseconds?|microsecs?|us|µs|milliseconds?|ms|seconds?|secs?|s)\b",
        text
    )

    if match:
        value = float(match.group(1))
        unit = match.group(2)

        if unit in ("ms", "millisecond", "milliseconds"):
            value *= 1000
        elif unit in ("s", "sec", "secs", "second", "seconds"):
            value *= 1_000_000

        result["delay_us"] = value

    # Extract timer number
    timer_match = re.search(r"timer\s*([01])\b", text)
    if timer_match:
        result["timer"] = int(timer_match.group(1))

    # Extract clock frequency
    clock_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(mhz|khz)\b", text
    )
    if clock_match:
        value = float(clock_match.group(1))
        result["clock_mhz"] = (
            value if clock_match.group(2) == "mhz"
            else value / 1000
        )

    # Extract timer mode
    mode_match = re.search(r"mode\s*([012])\b", text)
    if mode_match:
        result["mode"] = int(mode_match.group(1))

    return result


# -------------------------------------------------
# AGENT 2: Calculate timer register values
# -------------------------------------------------

def calculate_timer(delay_us, clock_mhz, timer, mode):

    if delay_us <= 0 or clock_mhz <= 0:
        raise ValueError("Delay and clock must be positive.")

    if timer not in (0, 1) or mode not in (0, 1, 2):
        raise ValueError("Invalid timer or mode.")

    # Classic 12-clock 8051 assumption
    tick_us = 12 / clock_mhz
    counts = math.floor(delay_us / tick_us + 0.5)

    bits = {0: 13, 1: 16, 2: 8}[mode]
    capacity = 1 << bits

    if counts < 1 or counts > capacity:
        raise ValueError(
            f"This delay needs {counts} counts. "
            f"Mode {mode} supports 1 to {capacity} counts "
            "per overflow. Use multiple overflows or another mode."
        )

    preload = capacity - counts

    if mode == 0:
        th = (preload >> 5) & 0xFF
        tl = preload & 0x1F
    else:
        th = (preload >> 8) & 0xFF if mode == 1 else preload
        tl = preload & 0xFF

    # Timer 0 uses lower TMOD nibble; Timer 1 uses upper nibble
    tmod = mode << (4 if timer == 1 else 0)

    actual = counts * tick_us

    return {
        "delay": delay_us,
        "clock": clock_mhz,
        "timer": timer,
        "mode": mode,
        "tick": tick_us,
        "counts": counts,
        "preload": preload,
        "th": th,
        "tl": tl,
        "tmod": tmod,
        "actual": actual,
        "error": actual - delay_us
    }


# -------------------------------------------------
# AGENT 3: Generate assembly code
# -------------------------------------------------

def generate_code(r):

    t = r["timer"]
    mode = r["mode"]

    code = [
        "; 8051 Delay Generator Assistant",
        f"; Requested delay: {r['delay']} us",
        f"; Timer {t}, Mode {mode}",
        f"; Timer overflow interval: {r['actual']:.6f} us",
        "; Classic 12-clock 8051 assumption",
        "",
        "ORG 0000H",
        "START:",
        f"    MOV TMOD, #{r['tmod']:02X}H",
        f"    MOV TH{t}, #{r['th']:02X}H",
        f"    MOV TL{t}, #{r['tl']:02X}H",
        f"    CLR TF{t}",
        f"    SETB TR{t}",
        "",
        "WAIT_OVERFLOW:",
        f"    JNB TF{t}, WAIT_OVERFLOW",
        f"    CLR TR{t}",
        f"    CLR TF{t}",
        "",
        "STOP:",
        "    SJMP STOP",
        "END"
    ]

    return "\n".join(code)


# -------------------------------------------------
# USER INTERFACE
# -------------------------------------------------

request = st.text_input(
    "Describe your required delay",
    "Generate a 20 microsecond delay using Timer 0 "
    "at 11.0592 MHz in Mode 1"
)

if st.button("Analyze and Generate", type="primary"):

    try:
        parsed = interpret_request(request)

        if parsed["delay_us"] is None:
            st.error(
                "Please enter a delay with a unit, "
                "such as 20 microseconds or 2 milliseconds."
            )
            st.stop()

        # User can override the values parsed by the agent
        with st.expander("Review timer settings"):
            clock = st.number_input(
                "Crystal frequency (MHz)",
                min_value=0.001,
                value=float(parsed["clock_mhz"]),
                format="%.4f"
            )

            timer = st.selectbox(
                "Timer",
                [0, 1],
                index=parsed["timer"],
                format_func=lambda x: f"Timer {x}"
            )

            mode = st.selectbox(
                "Timer mode",
                [0, 1, 2],
                index=parsed["mode"],
                format_func=lambda x: {
                    0: "Mode 0 - 13-bit",
                    1: "Mode 1 - 16-bit",
                    2: "Mode 2 - 8-bit auto-reload"
                }[x]
            )

        r = calculate_timer(
            parsed["delay_us"], clock, timer, mode
        )

        # Agent validation
        st.subheader("1. Calculation Results")

        c1, c2, c3 = st.columns(3)
        c1.metric("Timer counts", r["counts"])
        c2.metric("Actual interval", f"{r['actual']:.6f} µs")
        c3.metric("Timing error", f"{r['error']:+.6f} µs")

        st.write(f"Timer tick: **{r['tick']:.6f} µs**")
        st.write(f"TMOD: **0x{r['tmod']:02X}**")
        st.write(f"TH{timer}: **0x{r['th']:02X}**")
        st.write(f"TL{timer}: **0x{r['tl']:02X}**")

        st.info(
            "These values describe one timer overflow. "
            "The total program delay also depends on instruction "
            "execution time and polling overhead."
        )

        st.subheader("2. Generated Assembly Code")
        assembly = generate_code(r)
        st.code(assembly, language="asm")

        st.download_button(
            "Download Assembly Code",
            data=assembly,
            file_name="delay_program.a51",
            mime="text/plain"
        )

        st.subheader("3. Timing Diagram")

        fig, ax = plt.subplots(figsize=(9, 2.5))
        ax.hlines(1, 0, r["actual"], linewidth=3)
        ax.vlines([0, r["actual"]], 0.5, 1.5)
        ax.axvline(
            r["delay"],
            linestyle="--",
            label="Requested delay"
        )
        ax.set_xlim(0, max(r["actual"], r["delay"]) * 1.2)
        ax.set_ylim(0, 2)
        ax.set_yticks([1])
        ax.set_yticklabels(["Timer interval"])
        ax.set_xlabel("Time (microseconds)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)

        st.subheader("4. Agent Explanation")
        st.write(
            f"The request was interpreted as a {r['delay']} µs delay "
            f"using Timer {timer}, Mode {mode}. The calculator "
            f"selected {r['counts']} timer counts. The nearest "
            f"timer overflow interval is {r['actual']:.6f} µs. "
            "The generated code starts the timer, waits for overflow, "
            "and then stops it."
        )

    except ValueError as e:
        st.error(str(e))
