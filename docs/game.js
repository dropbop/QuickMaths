/**
 * QuickMaths - Mental Math Challenge
 * Web interface for the QuickMaths game
 */

// ============================================
// UTILITY FUNCTIONS
// ============================================

function clamp(x, lo, hi) {
    return Math.max(lo, Math.min(hi, x));
}

function parseFloat_(s) {
    if (!s || typeof s !== 'string') return null;
    const cleaned = s.trim().replace(/,/g, '');
    const val = parseFloat(cleaned);
    return isNaN(val) ? null : val;
}

function parseHHMM(s) {
    if (!s || typeof s !== 'string') return null;
    s = s.trim();
    // Accept either : or . as separator (. is easier on mobile keyboards)
    let hh, mm;
    if (s.includes(':')) {
        [hh, mm] = s.split(':');
    } else if (s.includes('.')) {
        [hh, mm] = s.split('.');
    } else {
        return null;
    }
    if (!/^\d+$/.test(hh) || !/^\d+$/.test(mm)) return null;
    const h = parseInt(hh, 10);
    const m = parseInt(mm, 10);
    if (h < 0 || h > 23 || m < 0 || m > 59) return null;
    return h * 60 + m;
}

function fmtHHMM(minutes) {
    minutes = ((minutes % (24 * 60)) + 24 * 60) % (24 * 60);
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}

function randInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randFloat(min, max) {
    return Math.random() * (max - min) + min;
}

function randChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function randSample(arr, n) {
    const shuffled = [...arr].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, n);
}

function roundTo(num, decimals) {
    const factor = Math.pow(10, decimals);
    return Math.round(num * factor) / factor;
}

// ============================================
// TIMEZONES
// ============================================

const TIMEZONES = {
    'UTC': 0,
    'PST': -8 * 60,
    'EST': -5 * 60,
    'CET': 1 * 60,
    'IST': 5 * 60 + 30,
    'JST': 9 * 60,
    'AEST': 10 * 60,
    'NPT': 5 * 60 + 45,
};

function convertTimezone(hhmmSrc, src, dst) {
    const offsetSrc = TIMEZONES[src];
    const offsetDst = TIMEZONES[dst];
    const delta = offsetDst - offsetSrc;
    return ((hhmmSrc + delta) % (24 * 60) + 24 * 60) % (24 * 60);
}

// ============================================
// UNIT CONVERSIONS
// ============================================

const LENGTH_FACTORS = {
    'mm': 0.001,
    'cm': 0.01,
    'm': 1.0,
    'km': 1000.0,
    'in': 0.0254,
    'ft': 0.3048,
    'yd': 0.9144,
    'mi': 1609.344,
};

const MASS_FACTORS = {
    'g': 0.001,
    'kg': 1.0,
    'lb': 0.45359237,
    'oz': 0.028349523125,
};

const VOLUME_FACTORS = {
    'ml': 0.001,
    'L': 1.0,
    'gal': 3.785411784,
    'cup': 0.2365882365,
};

const TEMP_UNITS = ['C', 'F', 'K'];

const NUMBER_FACTORS = {
    'thousand': 1000.0,
    'lakh': 100000.0,
    'million': 1000000.0,
    'crore': 10000000.0,
    'billion': 1000000000.0,
};

function convertLength(value, src, dst) {
    return value * LENGTH_FACTORS[src] / LENGTH_FACTORS[dst];
}

function convertMass(value, src, dst) {
    return value * MASS_FACTORS[src] / MASS_FACTORS[dst];
}

function convertVolume(value, src, dst) {
    return value * VOLUME_FACTORS[src] / VOLUME_FACTORS[dst];
}

function convertTemp(value, src, dst) {
    if (src === dst) return value;
    // Normalize to Celsius
    let c;
    if (src === 'C') c = value;
    else if (src === 'F') c = (value - 32) * 5 / 9;
    else if (src === 'K') c = value - 273.15;
    else throw new Error('Unknown temp unit');

    // From Celsius to dst
    if (dst === 'C') return c;
    if (dst === 'F') return c * 9 / 5 + 32;
    if (dst === 'K') return c + 273.15;
    throw new Error('Unknown temp unit');
}

function convertNumber(value, src, dst) {
    return value * NUMBER_FACTORS[src] / NUMBER_FACTORS[dst];
}

// Helper to get units for a category with optional filtering
function getUnitsForCategory(category, unitConfig) {
    const allUnits = {
        'length': Object.keys(LENGTH_FACTORS),
        'mass': Object.keys(MASS_FACTORS),
        'volume': Object.keys(VOLUME_FACTORS),
        'temp': TEMP_UNITS,
        'number': Object.keys(NUMBER_FACTORS),
    };
    const available = allUnits[category] || [];
    if (unitConfig && unitConfig.allowedUnits && unitConfig.allowedUnits[category]) {
        const allowed = unitConfig.allowedUnits[category];
        return available.filter(u => allowed.has(u));
    }
    return available;
}

// ============================================
// DIFFICULTY CALCULATIONS
// ============================================

function arithmeticDifficulty(op, a, b) {
    const digits = (x) => Math.max(1, Math.floor(Math.log10(Math.abs(x) + 1)) + 1);

    let decs = 0;
    [a, b].forEach(x => {
        const s = x.toString();
        if (s.includes('.')) {
            decs += s.split('.')[1].length;
        }
    });

    const d = Math.max(digits(a), digits(b));
    const opW = {'+': 0.0, '-': 0.1, '*': 1.0, '/': 1.2}[op] || 0.5;
    const decW = 0.25 * decs;
    const sizeW = 0.2 * Math.max(0, d - 1);
    return clamp(1.0 + opW + decW + sizeW, 1.0, 6.0);
}

function arithmeticTolerance(target, difficulty) {
    return 0.5 + Math.abs(target) * 0.001 * Math.pow(difficulty, 1.3);
}

function unitDifficulty(category, src, dst, value) {
    let base = {'length': 1.6, 'mass': 1.6, 'volume': 1.7, 'temp': 2.4, 'number': 1.8}[category] || 1.8;

    let spread = 0.0;
    if (['length', 'mass', 'volume'].includes(category)) {
        if (['mm', 'g', 'ml'].includes(src) || ['mi', 'lb', 'gal'].includes(dst)) {
            spread = 0.2;
        }
    }

    if (category === 'temp') {
        const pair = new Set([src, dst]);
        if (pair.has('C') && pair.has('F')) base += 0.2;
        else if (pair.has('C') && pair.has('K')) base += 0.1;
        else base += 0.3;
    }

    if (category === 'number') {
        const large = new Set(['billion', 'crore']);
        const small = new Set(['thousand', 'lakh']);
        if ((large.has(src) && small.has(dst)) || (small.has(src) && large.has(dst))) {
            spread = 0.3;
        } else if (large.has(src) || large.has(dst)) {
            spread = 0.2;
        }
    }

    const mag = Math.log10(Math.max(1.0, Math.abs(value))) * 0.15;
    return clamp(base + spread + mag, 1.2, 5.0);
}

function unitTolerance(target, difficulty, category) {
    if (category === 'temp') {
        return 0.5 + 0.01 * Math.abs(target) * Math.pow(difficulty, 1.1);
    }
    return 0.5 + 0.005 * Math.abs(target) * Math.pow(difficulty, 1.1);
}

function timezoneDifficulty(src, dst) {
    const offs = Math.abs(TIMEZONES[src] - TIMEZONES[dst]);
    const frac = offs % 60;
    let base = 1.0 + (frac ? 0.6 : 0.0) + (frac === 45 ? 0.3 : 0.0);
    const dist = 0.2 * Math.floor(offs / 120);
    return clamp(base + dist, 1.0, 3.0);
}

function timezoneToleranceMinutes(difficulty) {
    return Math.round(0.5 + 1.5 * Math.pow(difficulty, 1.1));
}

// ============================================
// SCORING
// ============================================

function scoreQuestion({ absError, tolerance, difficulty, timeS, mode }) {
    // Difficulty-aware nonlinear accuracy
    const eff = tolerance > 0 ? absError / tolerance : Infinity;
    const gamma = 1.0 + (difficulty - 1.0) / 4.0;
    let acc = 1.0 - Math.pow(eff, gamma);
    acc = clamp(acc, 0.0, 1.0);

    // Speed factor
    const baseDenom = 6.0;
    const denom = baseDenom * Math.pow(difficulty, 0.8);
    const spd = 1.0 / (1.0 + (timeS / denom));

    // Weighting
    const wSpeed = clamp(0.5 / Math.sqrt(difficulty), 0.25, 0.5);
    const wAcc = 1.0 - wSpeed;

    // Speed-accuracy coupling
    const alpha = 0.2 * ((difficulty - 1.0) / 4.0);
    const spdAccWeight = 0.1 + 0.9 * (alpha + (1.0 - alpha) * acc);

    const composite = wAcc * acc + wSpeed * spd * spdAccWeight;
    const score = Math.round(100 * composite);

    return {
        score,
        breakdown: {
            accuracyFactor: acc,
            speedFactor: spd,
            wAcc,
            wSpeed,
            spdAccWeight,
            tolerance,
            timeS,
        }
    };
}

// ============================================
// PROBLEM GENERATORS
// ============================================

function genArithmetic(level) {
    let ops, a, b;

    if (level === 'easy') {
        ops = ['+', '-'];
        a = randInt(10, 99);
        b = randInt(10, 99);
    } else if (level === 'medium') {
        ops = ['+', '-', '*'];
        a = randInt(20, 350);
        b = randInt(20, 350);
        if (Math.random() < 0.2) {
            a += randChoice([0.5, 0.25, 0.75]);
            b += randChoice([0.5, 0.25, 0.75]);
        }
    } else { // hard
        ops = ['+', '-', '*', '/'];
        a = roundTo(randFloat(5, 200), randChoice([1, 1, 2]));
        b = roundTo(randFloat(5, 200), randChoice([1, 1, 2]));
    }

    const op = randChoice(ops);
    let val;
    if (op === '+') val = a + b;
    else if (op === '-') val = a - b;
    else if (op === '*') val = a * b;
    else {
        if (Math.abs(b) < 1e-9) b = 3.0;
        val = a / b;
    }

    const diff = arithmeticDifficulty(op, a, b);
    let tol = arithmeticTolerance(val, diff);

    // Tighten tolerance for simple integer +/−
    if (['+', '-'].includes(op) && Number.isInteger(a) && Number.isInteger(b)) {
        tol = Math.min(tol, 1.5);
    }

    const sA = Number.isInteger(a) ? a.toString() : a.toString();
    const sB = Number.isInteger(b) ? b.toString() : b.toString();
    const prompt = `${sA} ${op} ${sB}`;

    return {
        mode: 'arithmetic',
        prompt,
        correctValue: val,
        difficulty: diff,
        tolerance: tol,
        answerParser: parseFloat_,
        errorMetric: (u, t) => Math.abs(u - t),
        unitHint: null,
    };
}

function genUnitConversion(unitConfig = null) {
    const allCategories = ['length', 'mass', 'temp', 'volume', 'number'];

    // Filter to enabled categories
    let categories = allCategories;
    if (unitConfig && unitConfig.enabledCategories) {
        categories = allCategories.filter(c => unitConfig.enabledCategories.has(c));
    }
    if (categories.length === 0) {
        categories = allCategories;
    }

    const cat = randChoice(categories);

    let units, value, target, src, dst;

    if (cat === 'length') {
        let allUnits = Object.keys(LENGTH_FACTORS);
        units = getUnitsForCategory(cat, unitConfig);
        if (units.length < 2) units = allUnits;
        [src, dst] = randSample(units, 2);
        value = roundTo(randFloat(0.5, 5000), randChoice([0, 1, 2]));
        target = convertLength(value, src, dst);
    } else if (cat === 'mass') {
        let allUnits = Object.keys(MASS_FACTORS);
        units = getUnitsForCategory(cat, unitConfig);
        if (units.length < 2) units = allUnits;
        [src, dst] = randSample(units, 2);
        value = roundTo(randFloat(0.5, 500), randChoice([0, 1, 2]));
        target = convertMass(value, src, dst);
    } else if (cat === 'volume') {
        let allUnits = Object.keys(VOLUME_FACTORS);
        units = getUnitsForCategory(cat, unitConfig);
        if (units.length < 2) units = allUnits;
        [src, dst] = randSample(units, 2);
        value = roundTo(randFloat(0.5, 200), randChoice([0, 1, 2]));
        target = convertVolume(value, src, dst);
    } else if (cat === 'temp') {
        let allUnits = TEMP_UNITS;
        units = getUnitsForCategory(cat, unitConfig);
        if (units.length < 2) units = allUnits;
        [src, dst] = randSample(units, 2);
        value = roundTo(randFloat(-40, 150), randChoice([0, 0, 1]));
        target = convertTemp(value, src, dst);
    } else { // number
        let allUnits = Object.keys(NUMBER_FACTORS);
        units = getUnitsForCategory(cat, unitConfig);
        if (units.length < 2) units = allUnits;
        [src, dst] = randSample(units, 2);
        value = roundTo(randFloat(0.5, 500), randChoice([0, 1, 2]));
        target = convertNumber(value, src, dst);
    }

    const diff = unitDifficulty(cat, src, dst, value);
    const tol = unitTolerance(target, diff, cat);
    const prompt = `Convert: ${value} ${src} → ${dst}`;

    return {
        mode: 'unit',
        prompt,
        correctValue: target,
        difficulty: diff,
        tolerance: tol,
        answerParser: parseFloat_,
        errorMetric: (u, t) => Math.abs(u - t),
        unitHint: dst,
        category: cat,
    };
}

function genTimezone() {
    const zones = Object.keys(TIMEZONES);
    const [src, dst] = randSample(zones, 2);
    const hh = randInt(1, 22);
    const mm = randChoice([0, 5, 10, 15, 20, 30, 35, 40, 45, 50]);
    const srcMin = hh * 60 + mm;
    const targetMin = convertTimezone(srcMin, src, dst);
    const diff = timezoneDifficulty(src, dst);
    const tol = timezoneToleranceMinutes(diff);
    const prompt = `If it's ${fmtHHMM(srcMin)} in ${src}, what time is it in ${dst}?`;

    return {
        mode: 'timezone',
        prompt,
        correctValue: targetMin,
        difficulty: diff,
        tolerance: tol,
        answerParser: parseHHMM,
        errorMetric: (u, t) => Math.min(Math.abs(u - t), 1440 - Math.abs(u - t)),
        unitHint: '24h HH:MM',
    };
}

function genMixed(level, unitConfig = null) {
    const pick = Math.random();
    if (pick < 0.5) return genArithmetic(level);
    if (pick < 0.75) return genUnitConversion(unitConfig);
    return genTimezone();
}

function makeProblem(mode, level, unitConfig = null) {
    if (mode === 'arithmetic') return genArithmetic(level);
    if (mode === 'unit') return genUnitConversion(unitConfig);
    if (mode === 'timezone') return genTimezone();
    return genMixed(level, unitConfig);
}

// ============================================
// GAME STATE
// ============================================

const GameState = {
    mode: 'arithmetic',
    level: 'medium',
    totalRounds: 10,
    currentRound: 0,
    totalScore: 0,
    currentProblem: null,
    startTime: 0,
    timerInterval: null,
    unitConfig: {
        enabledCategories: new Set(['length', 'mass', 'volume', 'temp', 'number']),
        allowedUnits: {},
    },
    results: [],
};

// ============================================
// DOM ELEMENTS
// ============================================

const elements = {
    // Screens
    startScreen: document.getElementById('start-screen'),
    gameScreen: document.getElementById('game-screen'),
    resultsScreen: document.getElementById('results-screen'),

    // Start screen
    modeButtons: document.querySelectorAll('.mode-btn'),
    difficultyGroup: document.getElementById('difficulty-group'),
    diffButtons: document.querySelectorAll('.diff-btn'),
    diffDescription: document.getElementById('diff-description'),
    questionButtons: document.querySelectorAll('.q-btn'),
    startBtn: document.getElementById('start-btn'),
    unitSettingsGroup: document.getElementById('unit-settings-group'),

    // Game screen
    progressText: document.getElementById('progress-text'),
    progressFill: document.getElementById('progress-fill'),
    currentScore: document.getElementById('current-score'),
    timer: document.getElementById('timer'),
    problemPrompt: document.getElementById('problem-prompt'),
    problemHint: document.getElementById('problem-hint'),
    answerInput: document.getElementById('answer-input'),
    submitBtn: document.getElementById('submit-btn'),
    feedbackContainer: document.getElementById('feedback-container'),
    feedbackResult: document.getElementById('feedback-result'),
    feedbackDetails: document.getElementById('feedback-details'),
    nextBtn: document.getElementById('next-btn'),
    quitBtn: document.getElementById('quit-btn'),

    // Results screen
    finalScore: document.getElementById('final-score'),
    maxScore: document.getElementById('max-score'),
    scoreRating: document.getElementById('score-rating'),
    avgTime: document.getElementById('avg-time'),
    accuracyRate: document.getElementById('accuracy-rate'),
    bestScore: document.getElementById('best-score'),
    breakdownList: document.getElementById('breakdown-list'),
    playAgainBtn: document.getElementById('play-again-btn'),
    changeSettingsBtn: document.getElementById('change-settings-btn'),
};

// ============================================
// UI FUNCTIONS
// ============================================

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

function updateDifficultyDescription() {
    const descriptions = {
        easy: '2-digit addition & subtraction',
        medium: 'Mix of operators with some 3-digit numbers',
        hard: 'Division, decimals, and larger numbers',
    };
    elements.diffDescription.textContent = descriptions[GameState.level];
}

function updateUnitSettingsVisibility() {
    if (elements.unitSettingsGroup) {
        if (GameState.mode === 'unit' || GameState.mode === 'mixed') {
            elements.unitSettingsGroup.style.display = 'block';
        } else {
            elements.unitSettingsGroup.style.display = 'none';
        }
    }
}

function collectUnitConfig() {
    const config = {
        enabledCategories: new Set(),
        allowedUnits: {},
    };

    // Collect enabled categories
    document.querySelectorAll('.category-checkbox').forEach(cb => {
        const category = cb.dataset.category;
        if (cb.checked) {
            config.enabledCategories.add(category);

            // Collect allowed units for this category
            const unitCheckboxes = document.querySelectorAll(`#units-${category} input[type="checkbox"]:checked`);
            if (unitCheckboxes.length > 0) {
                config.allowedUnits[category] = new Set(
                    Array.from(unitCheckboxes).map(u => u.value)
                );
            }
        }
    });

    // Fallback to all if none selected
    if (config.enabledCategories.size === 0) {
        config.enabledCategories = new Set(['length', 'mass', 'volume', 'temp', 'number']);
    }

    return config;
}

function initUnitSettings() {
    // Category checkbox toggles
    document.querySelectorAll('.category-checkbox').forEach(cb => {
        cb.addEventListener('change', () => {
            const category = cb.dataset.category;
            const unitCategory = cb.closest('.unit-category');
            if (unitCategory) {
                unitCategory.classList.toggle('disabled', !cb.checked);
            }
        });
    });

    // Expand buttons
    document.querySelectorAll('.expand-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const category = btn.dataset.category;
            const unitOptions = document.getElementById(`units-${category}`);
            if (unitOptions) {
                const isExpanded = unitOptions.style.display !== 'none';
                unitOptions.style.display = isExpanded ? 'none' : 'grid';
                btn.classList.toggle('expanded', !isExpanded);
                btn.textContent = isExpanded ? 'Customize' : 'Hide';
            }
        });
    });
}

function startTimer() {
    GameState.startTime = Date.now();
    elements.timer.textContent = '0.0s';

    if (GameState.timerInterval) {
        clearInterval(GameState.timerInterval);
    }

    GameState.timerInterval = setInterval(() => {
        const elapsed = (Date.now() - GameState.startTime) / 1000;
        elements.timer.textContent = `${elapsed.toFixed(1)}s`;
    }, 100);
}

function stopTimer() {
    if (GameState.timerInterval) {
        clearInterval(GameState.timerInterval);
        GameState.timerInterval = null;
    }
    return (Date.now() - GameState.startTime) / 1000;
}

function resetGame() {
    GameState.currentRound = 0;
    GameState.totalScore = 0;
    GameState.results = [];
    GameState.currentProblem = null;
}

function nextQuestion() {
    if (GameState.currentRound >= GameState.totalRounds) {
        showResults();
        return;
    }

    GameState.currentRound++;
    GameState.currentProblem = makeProblem(GameState.mode, GameState.level, GameState.unitConfig);

    // Update UI
    elements.progressText.textContent = `${GameState.currentRound} / ${GameState.totalRounds}`;
    elements.progressFill.style.width = `${(GameState.currentRound / GameState.totalRounds) * 100}%`;
    elements.currentScore.textContent = GameState.totalScore;
    elements.problemPrompt.textContent = GameState.currentProblem.prompt;

    // Set hint
    if (GameState.currentProblem.mode === 'unit' && GameState.currentProblem.unitHint) {
        elements.problemHint.textContent = `Answer in ${GameState.currentProblem.unitHint}`;
    } else if (GameState.currentProblem.mode === 'timezone') {
        elements.problemHint.textContent = 'Format: HH:MM or HH.MM (24-hour)';
    } else {
        elements.problemHint.textContent = '';
    }

    // Reset input and feedback
    elements.answerInput.value = '';
    elements.answerInput.disabled = false;
    elements.submitBtn.disabled = false;
    elements.feedbackContainer.classList.add('hidden');
    elements.answerInput.focus();

    startTimer();
}

function submitAnswer() {
    if (!GameState.currentProblem || elements.answerInput.disabled) return;

    const timeS = stopTimer();
    const answerStr = elements.answerInput.value.trim();

    // Parse and calculate error
    const parsed = GameState.currentProblem.answerParser(answerStr);
    let absError;
    if (parsed === null) {
        absError = Infinity;
    } else {
        absError = GameState.currentProblem.errorMetric(parsed, GameState.currentProblem.correctValue);
    }

    // Calculate score
    const { score, breakdown } = scoreQuestion({
        absError,
        tolerance: GameState.currentProblem.tolerance,
        difficulty: GameState.currentProblem.difficulty,
        timeS,
        mode: GameState.currentProblem.mode,
    });

    GameState.totalScore += score;
    elements.currentScore.textContent = GameState.totalScore;
    elements.currentScore.classList.add('updating');
    setTimeout(() => elements.currentScore.classList.remove('updating'), 300);

    // Store result
    GameState.results.push({
        prompt: GameState.currentProblem.prompt,
        answer: answerStr,
        correct: GameState.currentProblem.correctValue,
        absError,
        score,
        timeS,
        difficulty: GameState.currentProblem.difficulty,
        tolerance: GameState.currentProblem.tolerance,
        mode: GameState.currentProblem.mode,
    });

    // Show feedback
    const correctDisplay = GameState.currentProblem.mode === 'timezone'
        ? fmtHHMM(GameState.currentProblem.correctValue)
        : GameState.currentProblem.correctValue.toPrecision(6).replace(/\.?0+$/, '');

    const errorDisplay = isFinite(absError) ? absError.toPrecision(3) : 'n/a';

    // Determine feedback class
    let feedbackClass, feedbackText;
    if (score >= 80) {
        feedbackClass = 'correct';
        feedbackText = `+${score} points`;
    } else if (score >= 40) {
        feedbackClass = 'partial';
        feedbackText = `+${score} points (partial credit)`;
    } else {
        feedbackClass = 'incorrect';
        feedbackText = score > 0 ? `+${score} points` : 'No points';
    }

    elements.feedbackResult.className = `feedback-result ${feedbackClass}`;
    elements.feedbackResult.textContent = feedbackText;
    elements.feedbackDetails.innerHTML = `
        Correct: <strong>${correctDisplay}</strong> | Your error: ${errorDisplay}<br>
        acc ×${breakdown.accuracyFactor.toFixed(2)} | spd ×${breakdown.speedFactor.toFixed(2)} | ${timeS.toFixed(2)}s
    `;

    // Update button text
    elements.nextBtn.textContent = GameState.currentRound >= GameState.totalRounds ? 'See Results' : 'Next Question';

    // Show feedback, disable input
    elements.feedbackContainer.classList.remove('hidden');
    elements.answerInput.disabled = true;
    elements.submitBtn.disabled = true;
    elements.nextBtn.focus();
}

function showResults() {
    showScreen('results-screen');

    const maxPossible = GameState.totalRounds * 100;
    elements.finalScore.textContent = GameState.totalScore;
    elements.maxScore.textContent = maxPossible;

    // Calculate rating
    const percentage = (GameState.totalScore / maxPossible) * 100;
    let rating;
    if (percentage >= 90) rating = 'Outstanding!';
    else if (percentage >= 75) rating = 'Excellent!';
    else if (percentage >= 60) rating = 'Good job!';
    else if (percentage >= 40) rating = 'Keep practicing!';
    else rating = 'Room to grow!';
    elements.scoreRating.textContent = rating;

    // Calculate stats
    if (GameState.results.length > 0) {
        const avgTime = GameState.results.reduce((sum, r) => sum + r.timeS, 0) / GameState.results.length;
        elements.avgTime.textContent = `${avgTime.toFixed(1)}s`;

        const accurateCount = GameState.results.filter(r => r.score >= 70).length;
        const accuracyRate = (accurateCount / GameState.results.length) * 100;
        elements.accuracyRate.textContent = `${Math.round(accuracyRate)}%`;

        const bestScore = Math.max(...GameState.results.map(r => r.score));
        elements.bestScore.textContent = bestScore;
    }

    // Build breakdown list
    elements.breakdownList.innerHTML = GameState.results.map((r, i) => {
        const scoreClass = r.score >= 70 ? 'high' : r.score >= 40 ? 'medium' : 'low';
        return `
            <div class="breakdown-item">
                <span class="breakdown-prompt">${i + 1}. ${r.prompt}</span>
                <span class="breakdown-score ${scoreClass}">${r.score}</span>
            </div>
        `;
    }).join('');
}

// ============================================
// EVENT LISTENERS
// ============================================

// Mode selection
elements.modeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        elements.modeButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        GameState.mode = btn.dataset.mode;

        // Show/hide difficulty selector
        if (GameState.mode === 'arithmetic' || GameState.mode === 'mixed') {
            elements.difficultyGroup.style.display = 'block';
        } else {
            elements.difficultyGroup.style.display = 'none';
        }

        // Show/hide unit settings
        updateUnitSettingsVisibility();
    });
});

// Difficulty selection
elements.diffButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        elements.diffButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        GameState.level = btn.dataset.level;
        updateDifficultyDescription();
    });
});

// Question count selection
elements.questionButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        elements.questionButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        GameState.totalRounds = parseInt(btn.dataset.count, 10);
    });
});

// Start game
elements.startBtn.addEventListener('click', () => {
    // Collect unit config before starting
    GameState.unitConfig = collectUnitConfig();
    resetGame();
    showScreen('game-screen');
    nextQuestion();
});

// Submit answer
elements.submitBtn.addEventListener('click', submitAnswer);
elements.answerInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        submitAnswer();
    }
});

// Next question
elements.nextBtn.addEventListener('click', () => {
    if (GameState.currentRound >= GameState.totalRounds) {
        showResults();
    } else {
        nextQuestion();
    }
});

// Quit game
elements.quitBtn.addEventListener('click', () => {
    stopTimer();
    showScreen('start-screen');
});

// Play again (same settings)
elements.playAgainBtn.addEventListener('click', () => {
    resetGame();
    showScreen('game-screen');
    nextQuestion();
});

// Change settings
elements.changeSettingsBtn.addEventListener('click', () => {
    showScreen('start-screen');
});

// Initialize
updateDifficultyDescription();
initUnitSettings();
