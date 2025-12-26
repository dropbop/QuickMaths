#!/usr/bin/env python3
import math
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple, Dict, Any, Set


@dataclass
class UnitConfig:
    """Configuration for which unit categories and specific units to include."""
    enabled_categories: Set[str] = field(
        default_factory=lambda: {"length", "mass", "volume", "temp", "number"}
    )
    allowed_units: Dict[str, Set[str]] = field(default_factory=dict)

    def get_units_for_category(self, category: str, all_units: list) -> list:
        """Return filtered list of units for a category."""
        if category in self.allowed_units and self.allowed_units[category]:
            return [u for u in all_units if u in self.allowed_units[category]]
        return all_units


# ---------------------------
# Utility helpers
# ---------------------------


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def input_stripped(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def parse_float(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None


def parse_hhmm(s: str) -> Optional[int]:
    # Returns minutes since midnight (0..1439) for 24h HH:MM or HH.MM
    s = s.strip()
    if not s:
        return None
    # Accept either : or . as separator (. is easier on mobile keyboards)
    if ":" in s:
        hh, mm = s.split(":", 1)
    elif "." in s:
        hh, mm = s.split(".", 1)
    else:
        return None
    if not (hh.isdigit() and mm.isdigit()):
        return None
    h = int(hh)
    m = int(mm)
    if h < 0 or h > 23 or m < 0 or m > 59:
        return None
    return h * 60 + m


def fmt_hhmm(minutes: int) -> str:
    minutes = minutes % (24 * 60)
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


# ---------------------------
# Timezones and unit systems
# ---------------------------


TIMEZONES: Dict[str, int] = {
    # Offsets in minutes relative to UTC; simplified, ignores DST
    "UTC": 0,
    "PST": -8 * 60,
    "EST": -5 * 60,
    "CET": 1 * 60,
    "IST": 5 * 60 + 30,
    "JST": 9 * 60,
    "AEST": 10 * 60,
    "NPT": 5 * 60 + 45,  # Nepal Time (UTC+5:45)
}


def convert_timezone(hhmm_src: int, src: str, dst: str) -> int:
    # returns hhmm minutes in destination timezone
    offset_src = TIMEZONES[src]
    offset_dst = TIMEZONES[dst]
    delta = offset_dst - offset_src
    return (hhmm_src + delta) % (24 * 60)


# Unit conversions


class UnitConv:
    # factor-based conversions are done via a canonical base per category
    LENGTH_BASE = "m"  # meters
    MASS_BASE = "kg"   # kilograms
    VOLUME_BASE = "L"  # liters

    LENGTH_FACTORS = {
        # to meters
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
        "km": 1000.0,
        "in": 0.0254,
        "ft": 0.3048,
        "yd": 0.9144,
        "mi": 1609.344,
    }

    MASS_FACTORS = {
        # to kilograms
        "g": 0.001,
        "kg": 1.0,
        "lb": 0.45359237,
        "oz": 0.028349523125,
    }

    VOLUME_FACTORS = {
        # to liters (US)
        "ml": 0.001,
        "L": 1.0,
        "gal": 3.785411784,
        "cup": 0.2365882365,
    }

    TEMP_UNITS = {"C", "F", "K"}

    NUMBER_FACTORS = {
        # to ones (base unit)
        "thousand": 1_000.0,
        "lakh": 100_000.0,
        "million": 1_000_000.0,
        "crore": 10_000_000.0,
        "billion": 1_000_000_000.0,
    }

    @staticmethod
    def convert_length(value: float, src: str, dst: str) -> float:
        return value * UnitConv.LENGTH_FACTORS[src] / UnitConv.LENGTH_FACTORS[dst]

    @staticmethod
    def convert_mass(value: float, src: str, dst: str) -> float:
        return value * UnitConv.MASS_FACTORS[src] / UnitConv.MASS_FACTORS[dst]

    @staticmethod
    def convert_volume(value: float, src: str, dst: str) -> float:
        return value * UnitConv.VOLUME_FACTORS[src] / UnitConv.VOLUME_FACTORS[dst]

    @staticmethod
    def convert_temp(value: float, src: str, dst: str) -> float:
        # Temperature has offsets
        if src == dst:
            return value
        # Normalize to Celsius
        if src == "C":
            c = value
        elif src == "F":
            c = (value - 32) * 5 / 9
        elif src == "K":
            c = value - 273.15
        else:
            raise ValueError("Unknown temp unit")
        # From Celsius to dst
        if dst == "C":
            return c
        if dst == "F":
            return c * 9 / 5 + 32
        if dst == "K":
            return c + 273.15
        raise ValueError("Unknown temp unit")

    @staticmethod
    def convert_number(value: float, src: str, dst: str) -> float:
        return value * UnitConv.NUMBER_FACTORS[src] / UnitConv.NUMBER_FACTORS[dst]


# ---------------------------
# Problem and scoring
# ---------------------------


@dataclass
class Problem:
    mode: str  # 'arithmetic' | 'unit' | 'timezone'
    prompt: str
    correct_value: Any
    difficulty: float
    answer_parser: Callable[[str], Optional[Any]]
    error_metric: Callable[[Any, Any], float]  # returns absolute error in same units
    tolerance: float  # absolute error tolerance scale for full accuracy
    unit_hint: Optional[str] = None


def arithmetic_difficulty(op: str, a: float, b: float) -> float:
    def digits(x: float) -> int:
        x = abs(x)
        i = int(abs(int(x)))
        return max(1, len(str(i)))

    decs = 0
    for x in (a, b):
        s = f"{x}"
        if "." in s:
            decs += len(s.split(".")[1])

    d = max(digits(a), digits(b))
    op_w = {"+": 0.0, "-": 0.1, "*": 1.0, "/": 1.2}.get(op, 0.5)
    dec_w = 0.25 * decs
    size_w = 0.2 * max(0, d - 1)
    return clamp(1.0 + op_w + dec_w + size_w, 1.0, 6.0)


def arithmetic_tolerance(target: float, difficulty: float) -> float:
    # For simple integer problems, ~±1; for hard decimal ones, larger.
    return 0.5 + abs(target) * 0.001 * (difficulty ** 1.3)


def unit_difficulty(category: str, src: str, dst: str, value: float) -> float:
    base = {"length": 1.6, "mass": 1.6, "volume": 1.7, "temp": 2.4, "number": 1.8}.get(category, 1.8)
    # Larger magnitude and unrelated units add a bit
    spread = 0.0
    if category in ("length", "mass", "volume"):
        spread = 0.2 if src in ("mm", "g", "ml") or dst in ("mi", "lb", "gal") else 0.0
    if category == "temp":
        if {src, dst} == {"C", "F"}:
            base += 0.2
        elif {src, dst} == {"C", "K"}:
            base += 0.1
        else:
            base += 0.3
    if category == "number":
        # Large scale differences (billion/crore vs thousand/lakh) are harder
        large = {"billion", "crore"}
        small = {"thousand", "lakh"}
        if (src in large and dst in small) or (src in small and dst in large):
            spread = 0.3
        elif src in large or dst in large:
            spread = 0.2
    mag = math.log10(max(1.0, abs(value))) * 0.15
    return clamp(base + spread + mag, 1.2, 5.0)


def unit_tolerance(target: float, difficulty: float, category: str) -> float:
    if category == "temp":
        # Temperature near zero needs absolute tolerance
        return 0.5 + 0.01 * abs(target) * (difficulty ** 1.1)
    # Factor-only conversions: allow ~0.5 + up to ~1-3% depending on difficulty
    return 0.5 + 0.005 * abs(target) * (difficulty ** 1.1)


def timezone_difficulty(src: str, dst: str) -> float:
    offs = abs(TIMEZONES[src] - TIMEZONES[dst])
    # Whole hours easiest; 30 or 45 minute offsets add difficulty
    frac = offs % 60
    base = 1.0 + (0.6 if frac else 0.0) + (0.3 if frac == 45 else 0.0)
    dist = 0.2 * (offs // 120)  # wider separations slightly harder
    return clamp(base + dist, 1.0, 3.0)


def timezone_tolerance_minutes(difficulty: float) -> float:
    # ~±2 min for easy, growing slowly for trickier offsets
    return round(0.5 + 1.5 * (difficulty ** 1.1))


def score_question(
    *,
    abs_error: float,
    tolerance: float,
    difficulty: float,
    time_s: float,
    mode: str,
) -> Tuple[int, Dict[str, float]]:
    # Difficulty-aware nonlinear accuracy: close answers on hard items get better credit
    eff = (abs_error / tolerance) if tolerance > 0 else float("inf")
    gamma = 1.0 + (difficulty - 1.0) / 4.0  # 1..~2 as difficulty increases
    acc = 1.0 - (eff ** gamma)
    acc = clamp(acc, 0.0, 1.0)

    # Speed factor: decreases with time; denominator scales with difficulty
    base_denom = 6.0
    denom = base_denom * (difficulty ** 0.8)
    spd = 1.0 / (1.0 + (time_s / denom))

    # Weighting: speed counts more when easier; slightly higher floor for speed weight
    w_speed = clamp(0.5 / math.sqrt(difficulty), 0.25, 0.5)
    w_acc = 1.0 - w_speed

    # Preserve some speed credit on hard items even with imperfect accuracy
    alpha = 0.2 * ((difficulty - 1.0) / 4.0)  # 0..0.2 across difficulty range
    spd_acc_weight = 0.1 + 0.9 * (alpha + (1.0 - alpha) * acc)
    composite = w_acc * acc + w_speed * spd * spd_acc_weight
    score = int(round(100 * composite))
    breakdown = {
        "accuracy_factor": acc,
        "speed_factor": spd,
        "w_acc": w_acc,
        "w_speed": w_speed,
        "spd_acc_weight": spd_acc_weight,
        "tolerance": tolerance,
        "time_s": time_s,
    }
    return score, breakdown


# ---------------------------
# Problem generators
# ---------------------------


def gen_arithmetic(level: str) -> Problem:
    # level: 'easy' | 'medium' | 'hard'
    if level == "easy":
        ops = ["+", "-"]
        a = random.randint(10, 99)
        b = random.randint(10, 99)
    elif level == "medium":
        ops = ["+", "-", "*"]
        # Allow some 3-digit and mix
        a = random.randint(20, 350)
        b = random.randint(20, 350)
        if random.random() < 0.2:
            # sprinkle decimals
            a += random.choice([0.5, 0.25, 0.75])
            b += random.choice([0.5, 0.25, 0.75])
    else:  # hard
        ops = ["+", "-", "*", "/"]
        a = random.uniform(5, 200)
        b = random.uniform(5, 200)
        # add decimals
        a = round(a, random.choice([1, 1, 2]))
        b = round(b, random.choice([1, 1, 2]))

    op = random.choice(ops)
    if op == "+":
        val = a + b
    elif op == "-":
        val = a - b
    elif op == "*":
        val = a * b
    else:
        # Keep division results reasonable
        if abs(b) < 1e-9:
            b = 3.0
        val = a / b

    diff = arithmetic_difficulty(op, a, b)
    tol = arithmetic_tolerance(val, diff)
    # Tighten tolerance for simple integer +/− to about ±1
    if op in ["+", "-"] and float(a).is_integer() and float(b).is_integer():
        tol = min(tol, 1.5)
    s_a = f"{a}" if float(a).is_integer() else f"{a}"
    s_b = f"{b}" if float(b).is_integer() else f"{b}"
    prompt = f"Compute: {s_a} {op} {s_b} = ?"

    return Problem(
        mode="arithmetic",
        prompt=prompt,
        correct_value=float(val),
        difficulty=diff,
        answer_parser=parse_float,
        error_metric=lambda u, t: abs(float(u) - float(t)),
        tolerance=tol,
    )


def gen_unit_conversion(unit_config: Optional[UnitConfig] = None) -> Problem:
    if unit_config is None:
        unit_config = UnitConfig()

    # Filter to enabled categories
    all_categories = ["length", "mass", "temp", "volume", "number"]
    categories = [c for c in all_categories if c in unit_config.enabled_categories]
    if not categories:
        categories = all_categories  # Fallback to all

    cat = random.choice(categories)

    if cat == "length":
        all_units = list(UnitConv.LENGTH_FACTORS.keys())
        units = unit_config.get_units_for_category(cat, all_units)
        if len(units) < 2:
            units = all_units
        src, dst = random.sample(units, 2)
        value = round(random.uniform(0.5, 5000), random.choice([0, 1, 2]))
        target = UnitConv.convert_length(value, src, dst)
    elif cat == "mass":
        all_units = list(UnitConv.MASS_FACTORS.keys())
        units = unit_config.get_units_for_category(cat, all_units)
        if len(units) < 2:
            units = all_units
        src, dst = random.sample(units, 2)
        value = round(random.uniform(0.5, 500), random.choice([0, 1, 2]))
        target = UnitConv.convert_mass(value, src, dst)
    elif cat == "volume":
        all_units = list(UnitConv.VOLUME_FACTORS.keys())
        units = unit_config.get_units_for_category(cat, all_units)
        if len(units) < 2:
            units = all_units
        src, dst = random.sample(units, 2)
        value = round(random.uniform(0.5, 200), random.choice([0, 1, 2]))
        target = UnitConv.convert_volume(value, src, dst)
    elif cat == "temp":
        all_units = ["C", "F", "K"]
        units = unit_config.get_units_for_category(cat, all_units)
        if len(units) < 2:
            units = all_units
        src, dst = random.sample(units, 2)
        value = round(random.uniform(-40, 150), random.choice([0, 0, 1]))
        target = UnitConv.convert_temp(value, src, dst)
    else:  # number
        all_units = list(UnitConv.NUMBER_FACTORS.keys())
        units = unit_config.get_units_for_category(cat, all_units)
        if len(units) < 2:
            units = all_units
        src, dst = random.sample(units, 2)
        value = round(random.uniform(0.5, 500), random.choice([0, 1, 2]))
        target = UnitConv.convert_number(value, src, dst)

    diff = unit_difficulty(cat, src, dst, value)
    tol = unit_tolerance(target, diff, cat)
    prompt = f"Convert: {value} {src} -> {dst}"
    return Problem(
        mode="unit",
        prompt=prompt,
        correct_value=float(target),
        difficulty=diff,
        answer_parser=parse_float,
        error_metric=lambda u, t: abs(float(u) - float(t)),
        tolerance=tol,
        unit_hint=dst,
    )


def gen_timezone() -> Problem:
    src, dst = random.sample(list(TIMEZONES.keys()), 2)
    # Avoid edge cases right at midnight
    hh = random.randint(1, 22)
    mm = random.choice([0, 5, 10, 15, 20, 30, 35, 40, 45, 50])
    src_min = hh * 60 + mm
    target_min = convert_timezone(src_min, src, dst)
    diff = timezone_difficulty(src, dst)
    tol = timezone_tolerance_minutes(diff)
    prompt = f"Timezone: If it's {fmt_hhmm(src_min)} in {src}, what time is it in {dst}? (24h HH:MM)"
    return Problem(
        mode="timezone",
        prompt=prompt,
        correct_value=int(target_min),
        difficulty=diff,
        answer_parser=parse_hhmm,
        error_metric=lambda u, t: min(abs(int(u) - int(t)), 1440 - abs(int(u) - int(t))),
        tolerance=float(tol),
    )


def gen_mixed(level: str, unit_config: Optional[UnitConfig] = None) -> Problem:
    pick = random.random()
    if pick < 0.5:
        return gen_arithmetic(level)
    elif pick < 0.75:
        return gen_unit_conversion(unit_config)
    else:
        return gen_timezone()


# ---------------------------
# Game loop
# ---------------------------


def print_header():
    print("=" * 60)
    print("QuickMaths — Mental Math Challenge")
    print("Multiple modes. Accuracy + Speed scoring.")
    print("=" * 60)


def choose_mode() -> Tuple[str, str]:
    print("Pick a mode:")
    print("  1) Arithmetic")
    print("  2) Unit Conversion")
    print("  3) Timezones")
    print("  4) Mixed")
    while True:
        c = input_stripped("Mode [1-4]: ")
        if c in ("1", "2", "3", "4"):
            break
    if c == "1":
        mode = "arithmetic"
    elif c == "2":
        mode = "unit"
    elif c == "3":
        mode = "timezone"
    else:
        mode = "mixed"

    if mode in ("arithmetic", "mixed"):
        print("Difficulty for arithmetic:")
        print("  a) Easy  (2-digit + −)")
        print("  b) Medium(mix ×, some decimals)")
        print("  c) Hard  (÷ and decimals)")
        dmap = {"a": "easy", "b": "medium", "c": "hard"}
        while True:
            d = input_stripped("Choose [a/b/c]: ").lower()
            if d in dmap:
                return mode, dmap[d]
    return mode, "medium"


def choose_rounds() -> int:
    while True:
        s = input_stripped("How many questions? [10]: ")
        if not s:
            return 10
        try:
            n = int(s)
            if 1 <= n <= 100:
                return n
        except Exception:
            pass
        print("Enter an integer between 1 and 100.")


def make_problem(mode: str, level: str, unit_config: Optional[UnitConfig] = None) -> Problem:
    if mode == "arithmetic":
        return gen_arithmetic(level)
    if mode == "unit":
        return gen_unit_conversion(unit_config)
    if mode == "timezone":
        return gen_timezone()
    return gen_mixed(level, unit_config)


def show_unit_hint(prob: Problem):
    if prob.mode == "unit" and prob.unit_hint:
        print(f"Answer in {prob.unit_hint}")
    elif prob.mode == "timezone":
        print("Answer format: 24h HH:MM or HH.MM (e.g. 09:05 or 09.05)")


def run_game():
    print_header()
    mode, level = choose_mode()
    rounds = choose_rounds()
    print()
    if mode == "unit":
        print("Units: length(mm, cm, m, km, in, ft, yd, mi), mass(g, kg, lb, oz), volume(ml, L, gal, cup), temp(C, F, K), number(thousand, lakh, million, crore, billion)")
    if mode == "timezone":
        zones = ", ".join(sorted(TIMEZONES.keys()))
        print(f"Timezones used (no DST): {zones}")
    if mode == "mixed":
        zones = ", ".join(sorted(TIMEZONES.keys()))
        print("Mixed mode combines arithmetic, unit conversion, and timezone questions.")
        print(f"Timezones used (no DST): {zones}")
    
    print()
    print("Scoring note: Simple problems demand higher accuracy; speed matters more when it’s easy. Hard ones allow more tolerance and de-emphasize speed.")
    print()

    total = 0
    results = []
    for i in range(1, rounds + 1):
        prob = make_problem(mode, level)
        print(f"[{i}/{rounds}] {prob.prompt}")
        show_unit_hint(prob)
        t0 = time.time()
        ans = input_stripped("> ")
        t1 = time.time()
        dt = max(0.0, t1 - t0)

        parsed = prob.answer_parser(ans)
        if parsed is None:
            print("Could not parse answer. Counting as incorrect.")
            abs_err = float('inf')
        else:
            abs_err = prob.error_metric(parsed, prob.correct_value)

        score, bd = score_question(
            abs_error=abs_err,
            tolerance=prob.tolerance,
            difficulty=prob.difficulty,
            time_s=dt,
            mode=prob.mode,
        )
        total += score
        results.append({
            "prompt": prob.prompt,
            "answer": ans,
            "correct": prob.correct_value,
            "abs_error": abs_err,
            "score": score,
            "time_s": dt,
            "difficulty": prob.difficulty,
            "tolerance": prob.tolerance,
        })

        corr_display = (
            fmt_hhmm(prob.correct_value) if prob.mode == "timezone" else f"{prob.correct_value:.6g}"
        )
        if math.isfinite(abs_err):
            print(f"Correct: {corr_display} | Your error: {abs_err:.3g}")
        else:
            print(f"Correct: {corr_display} | Your error: n/a")
        print(
            f"Score +{score} (acc x{bd['accuracy_factor']:.2f}, spd x{bd['speed_factor']:.2f}, tol {bd['tolerance']:.3g}, {dt:.2f}s)"
        )
        print("-" * 60)

    print("Final Results")
    print("=" * 60)
    print(f"Total score: {total} out of {rounds * 100}")
    print("Thanks for playing QuickMaths!")


if __name__ == "__main__":
    try:
        run_game()
    except KeyboardInterrupt:
        print("\nExiting. Goodbye!")
        sys.exit(0)
