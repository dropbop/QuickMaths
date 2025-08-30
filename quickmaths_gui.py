#!/usr/bin/env python3
"""
QuickMaths GUI

A lightweight Tkinter GUI for the QuickMaths CLI game.
Reuses problem generation and scoring logic from quickmaths.py.

Run: python quickmaths_gui.py

Dependencies: Python standard library only (tkinter, time).
"""

import math
import time
import tkinter as tk
from tkinter import ttk, messagebox

# Import core logic from the CLI module
from quickmaths import (
    make_problem,
    score_question,
    fmt_hhmm,
)


class QuickMathsGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("QuickMaths — Mental Math (GUI)")
        self.geometry("760x520")
        self.minsize(640, 420)

        # Global/session state
        self.mode_var = tk.StringVar(value="arithmetic")
        self.level_var = tk.StringVar(value="medium")  # used for arithmetic and mixed
        self.rounds_var = tk.StringVar(value="10")

        self.current_round = 0
        self.total_rounds = 10
        self.total_score = 0
        self.current_problem = None  # type: ignore
        self.start_time = 0.0
        self.timer_after_id = None
        self.results = []

        # Views
        self.container = ttk.Frame(self, padding=12)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.view_start = ttk.Frame(self.container)
        self.view_game = ttk.Frame(self.container)
        self.view_end = ttk.Frame(self.container)

        self._build_start_view()
        self._build_game_view()
        self._build_end_view()

        self._show_view(self.view_start)

    # ---------- UI builders ----------
    def _build_start_view(self) -> None:
        f = self.view_start

        title = ttk.Label(
            f,
            text="QuickMaths",
            font=("Segoe UI", 20, "bold"),
        )
        subtitle = ttk.Label(
            f,
            text="Practice arithmetic, unit conversions, and timezone math.",
        )

        # Mode selection
        mode_frame = ttk.LabelFrame(f, text="Mode")
        for i, (key, label) in enumerate(
            (
                ("arithmetic", "Arithmetic"),
                ("unit", "Unit Conversion"),
                ("timezone", "Timezones"),
                ("mixed", "Mixed"),
            )
        ):
            rb = ttk.Radiobutton(
                mode_frame,
                text=label,
                value=key,
                variable=self.mode_var,
                command=self._on_mode_change,
            )
            rb.grid(row=0, column=i, padx=6, pady=6, sticky="w")

        # Difficulty (for arithmetic and mixed)
        diff_frame = ttk.LabelFrame(f, text="Difficulty (Arithmetic/Mixed)")
        for i, (key, label) in enumerate(
            (
                ("easy", "Easy"),
                ("medium", "Medium"),
                ("hard", "Hard"),
            )
        ):
            rb = ttk.Radiobutton(
                diff_frame,
                text=label,
                value=key,
                variable=self.level_var,
            )
            rb.grid(row=0, column=i, padx=6, pady=6, sticky="w")

        # Rounds
        cfg_frame = ttk.LabelFrame(f, text="Session")
        ttk.Label(cfg_frame, text="Questions:").grid(row=0, column=0, padx=(6, 2), pady=6)
        rounds_entry = ttk.Entry(cfg_frame, textvariable=self.rounds_var, width=6)
        rounds_entry.grid(row=0, column=1, padx=2, pady=6)
        rounds_entry.insert(0, "10")
        ttk.Label(cfg_frame, text="(1–100)").grid(row=0, column=2, padx=(2, 6), pady=6)

        start_btn = ttk.Button(f, text="Start", command=self._start_game)

        # Layout
        title.pack(anchor="w")
        subtitle.pack(anchor="w", pady=(0, 10))
        mode_frame.pack(fill=tk.X, pady=6)
        diff_frame.pack(fill=tk.X, pady=6)
        cfg_frame.pack(fill=tk.X, pady=6)
        start_btn.pack(pady=(10, 0))

        self._diff_frame = diff_frame
        self._on_mode_change()  # initial toggle

    def _build_game_view(self) -> None:
        f = self.view_game

        # Header: progress, score, timer
        header = ttk.Frame(f)
        self.lbl_progress = ttk.Label(header, text="[0/0]", font=("Segoe UI", 10, "bold"))
        self.lbl_score = ttk.Label(header, text="Score: 0", font=("Segoe UI", 10))
        self.lbl_timer = ttk.Label(header, text="0.00s", font=("Segoe UI", 10))
        self.lbl_progress.pack(side=tk.LEFT)
        self.lbl_score.pack(side=tk.LEFT, padx=(12, 0))
        self.lbl_timer.pack(side=tk.RIGHT)
        header.pack(fill=tk.X)

        # Prompt and hint
        self.lbl_prompt = ttk.Label(
            f,
            text="",
            font=("Segoe UI", 14, "bold"),
            wraplength=700,
            justify=tk.LEFT,
        )
        self.lbl_prompt.pack(fill=tk.X, pady=(10, 2))

        self.lbl_hint = ttk.Label(f, text="", foreground="#555")
        self.lbl_hint.pack(fill=tk.X, pady=(0, 6))

        # Answer entry
        ans_frame = ttk.Frame(f)
        ttk.Label(ans_frame, text="Your answer:").pack(side=tk.LEFT)
        self.answer_var = tk.StringVar(value="")
        self.entry_answer = ttk.Entry(ans_frame, textvariable=self.answer_var, width=24)
        self.entry_answer.pack(side=tk.LEFT, padx=(6, 0))
        self.entry_answer.bind("<Return>", lambda _e: self._submit_answer())

        self.btn_submit = ttk.Button(ans_frame, text="Submit", command=self._submit_answer)
        self.btn_submit.pack(side=tk.LEFT, padx=(8, 0))

        self.btn_skip = ttk.Button(ans_frame, text="Skip", command=self._skip_question)
        self.btn_skip.pack(side=tk.LEFT, padx=(6, 0))

        ans_frame.pack(fill=tk.X, pady=(6, 4))

        # Feedback
        self.lbl_feedback = ttk.Label(f, text="", foreground="#004085")
        self.lbl_feedback.pack(fill=tk.X, pady=(4, 8))

        # Next/Finish controls
        nav = ttk.Frame(f)
        self.btn_next = ttk.Button(nav, text="Next", command=self._next_question, state=tk.DISABLED)
        self.btn_end = ttk.Button(nav, text="End", command=self._end_game)
        self.btn_next.pack(side=tk.LEFT)
        self.btn_end.pack(side=tk.LEFT, padx=(6, 0))
        nav.pack(fill=tk.X, pady=(8, 0))

    def _build_end_view(self) -> None:
        f = self.view_end
        self.lbl_summary = ttk.Label(
            f,
            text="",
            font=("Segoe UI", 14, "bold"),
            justify=tk.LEFT,
        )
        self.lbl_summary.pack(fill=tk.X, pady=(10, 10))

        btns = ttk.Frame(f)
        ttk.Button(btns, text="Play Again", command=lambda: self._show_view(self.view_start)).pack(
            side=tk.LEFT
        )
        ttk.Button(btns, text="Quit", command=self.destroy).pack(side=tk.LEFT, padx=(8, 0))
        btns.pack()

    # ---------- View helpers ----------
    def _show_view(self, frame: ttk.Frame) -> None:
        for child in (self.view_start, self.view_game, self.view_end):
            child.pack_forget()
        frame.pack(fill=tk.BOTH, expand=True)
        if frame is self.view_start:
            self._reset_session()

    def _on_mode_change(self) -> None:
        # Difficulty selector is relevant for arithmetic and mixed
        mode = self.mode_var.get()
        show = mode in ("arithmetic", "mixed")
        if show:
            self._diff_frame.pack_configure(fill=tk.X, pady=6)
        else:
            self._diff_frame.pack_forget()

    # ---------- Session control ----------
    def _reset_session(self) -> None:
        self.current_round = 0
        self.total_rounds = 10
        self.total_score = 0
        self.current_problem = None
        self.start_time = 0.0
        self.results = []
        self._cancel_timer()
        self.lbl_feedback.configure(text="")
        self.answer_var.set("")

    def _start_game(self) -> None:
        # Validate rounds
        try:
            n = int(self.rounds_var.get() or "10")
        except Exception:
            messagebox.showerror("Invalid input", "Questions must be an integer between 1 and 100.")
            return
        if not (1 <= n <= 100):
            messagebox.showerror("Invalid input", "Questions must be between 1 and 100.")
            return
        self.total_rounds = n
        self.total_score = 0
        self.current_round = 0
        self.results = []
        self._show_view(self.view_game)
        self._next_question()

    def _end_game(self) -> None:
        self._cancel_timer()
        # Build summary text
        total = self.total_score
        max_total = self.total_rounds * 100
        lines = [
            f"Final Results",
            f"Total score: {total} out of {max_total}",
            "",
            "Thanks for playing QuickMaths!",
        ]
        self.lbl_summary.configure(text="\n".join(lines))
        self._show_view(self.view_end)

    # ---------- Timer helpers ----------
    def _cancel_timer(self) -> None:
        if self.timer_after_id is not None:
            try:
                self.after_cancel(self.timer_after_id)
            except Exception:
                pass
            self.timer_after_id = None
        self.lbl_timer.configure(text="0.00s")

    def _start_timer(self) -> None:
        self.start_time = time.time()
        self._tick_timer()

    def _tick_timer(self) -> None:
        dt = max(0.0, time.time() - self.start_time)
        self.lbl_timer.configure(text=f"{dt:.2f}s")
        self.timer_after_id = self.after(100, self._tick_timer)

    # ---------- Game mechanics ----------
    def _next_question(self) -> None:
        # If finished, show summary
        if self.current_round >= self.total_rounds:
            self._end_game()
            return

        self.current_round += 1
        mode = self.mode_var.get()
        level = self.level_var.get()

        self.current_problem = make_problem(mode, level)

        # Update UI
        self.lbl_progress.configure(text=f"[{self.current_round}/{self.total_rounds}]")
        self.lbl_score.configure(text=f"Score: {self.total_score}")
        self.lbl_prompt.configure(text=self.current_problem.prompt)

        if self.current_problem.mode == "unit" and getattr(self.current_problem, "unit_hint", None):
            self.lbl_hint.configure(text=f"Answer in {self.current_problem.unit_hint}")
        elif self.current_problem.mode == "timezone":
            self.lbl_hint.configure(text="Answer format: 24h HH:MM (e.g. 09:05)")
        else:
            self.lbl_hint.configure(text="")

        self.answer_var.set("")
        self.entry_answer.configure(state=tk.NORMAL)
        self.btn_submit.configure(state=tk.NORMAL)
        self.btn_skip.configure(state=tk.NORMAL)
        self.btn_next.configure(state=tk.DISABLED)
        self.lbl_feedback.configure(text="")
        self.entry_answer.focus_set()
        self._cancel_timer()
        self._start_timer()

    def _finalize_question(self, ans_str: str, time_s: float) -> None:
        prob = self.current_problem
        if prob is None:
            return

        parsed = prob.answer_parser(ans_str)
        if parsed is None:
            abs_err = float("inf")
        else:
            abs_err = prob.error_metric(parsed, prob.correct_value)

        score, bd = score_question(
            abs_error=abs_err,
            tolerance=prob.tolerance,
            difficulty=prob.difficulty,
            time_s=time_s,
            mode=prob.mode,
        )
        self.total_score += score
        self.lbl_score.configure(text=f"Score: {self.total_score}")

        # Build feedback
        if prob.mode == "timezone":
            corr_display = fmt_hhmm(prob.correct_value)
        else:
            try:
                corr_display = f"{float(prob.correct_value):.6g}"
            except Exception:
                corr_display = str(prob.correct_value)

        if math.isfinite(abs_err):
            err_display = f"{abs_err:.3g}"
        else:
            err_display = "n/a"

        fb = (
            f"Correct: {corr_display} | Your error: {err_display}\n"
            f"Score +{score} (acc x{bd['accuracy_factor']:.2f}, spd x{bd['speed_factor']:.2f}, "
            f"tol {bd['tolerance']:.3g}, {time_s:.2f}s)"
        )
        self.lbl_feedback.configure(text=fb)

        self.results.append(
            {
                "prompt": prob.prompt,
                "answer": ans_str,
                "correct": prob.correct_value,
                "abs_error": abs_err,
                "score": score,
                "time_s": time_s,
                "difficulty": prob.difficulty,
                "tolerance": prob.tolerance,
            }
        )

        # Controls for next
        self.entry_answer.configure(state=tk.DISABLED)
        self.btn_submit.configure(state=tk.DISABLED)
        self.btn_skip.configure(state=tk.DISABLED)
        self.btn_next.configure(text=("Finish" if self.current_round >= self.total_rounds else "Next"))
        self.btn_next.configure(state=tk.NORMAL)

    def _submit_answer(self) -> None:
        if self.current_problem is None:
            return
        self._cancel_timer()
        time_s = max(0.0, time.time() - self.start_time)
        ans_str = self.answer_var.get().strip()
        self._finalize_question(ans_str, time_s)

    def _skip_question(self) -> None:
        if self.current_problem is None:
            return
        self._cancel_timer()
        time_s = max(0.0, time.time() - self.start_time)
        self._finalize_question("", time_s)


def main() -> None:
    app = QuickMathsGUI()
    app.mainloop()


if __name__ == "__main__":
    main()

