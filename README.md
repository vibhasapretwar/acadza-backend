# Acadza AI Recommender — README

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+ (for the frontend)

### Backend Setup

```bash
cd acadza-backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API is now live at `http://localhost:8000`. Swagger docs at `/docs`.

### Frontend Setup

```bash
cd acadza-frontend
# Set backend URL
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
npm install
npm run dev
```

### Connecting Frontend to Backend

The frontend reads `VITE_API_BASE_URL` from `.env`. The `src/api/index.js` file should use:

```js
const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const analyzeStudent  = (id) => fetch(`${BASE}/analyze/${id}`,   { method: "POST" }).then(r => r.json());
export const recommendStudent= (id) => fetch(`${BASE}/recommend/${id}`,  { method: "POST" }).then(r => r.json());
export const getLeaderboard  = ()   => fetch(`${BASE}/leaderboard`).then(r => r.json());
export const getQuestion     = (id) => fetch(`${BASE}/question/${id}`).then(r => r.json());
export const listStudents    = ()   => fetch(`${BASE}/students`).then(r => r.json());
```

### Deployment (Render / Railway / Fly.io)

1. Push `acadza-backend/` to a GitHub repo
2. Create a new Web Service on Render pointing to that repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Update frontend `.env` with the deployed URL:
   ```
   VITE_API_BASE_URL=https://your-service.onrender.com
   ```
6. Deploy frontend to Vercel/Netlify — set the same env var there.

---

## Approach to the Build Task

### How I Analyzed Student Data

The first thing I noticed about this dataset is that it has two distinct sources of truth: the `marks` field (messy, inconsistent) and the structural fields (`attempted`, `skipped`, `completed`). I decided to build a two-layer analysis: normalize the marks into a consistent percentage first, then layer on behavioral signals like completion rate, attempt rate, and integer-question avoidance.

For marks normalization, I handled five formats: `"39/100"`, `"+48 -8"` (JEE-style positive/negative), `"49/120 (40.8%)"`, plain numbers like `72`, and the percentage-in-brackets variant. The tricky one is the `+pos -neg` format — I convert it to a net score and divide by `total_questions × 4` (the standard JEE marking scheme: 4 marks per correct, -1 per wrong). This gives a rough but consistent percentage.

One assumption I made: for plain numeric marks (like `"22"` or `72`), I assumed they're raw scores out of `total_questions × 4`. This isn't always right — some could be out of 100 — but without a consistent max score, this is the most defensible heuristic.

### How I Decided Which DOSTs to Recommend

The recommendation pipeline has a priority order designed around a specific learning loop:

1. **Identify the weakest chapter** using per-chapter average scores
2. **Start with `concept`** — there's no point practising questions if the theory isn't there
3. **Follow with `formula`** — commit the key formulas right after the concept review
4. **`practiceAssignment` (untimed)** — build accuracy before speed
5. **`clickingPower`** if the student is slow — speed drill on familiar topics
6. **`revision`** for the second weakest chapter — multi-day, prevents cramming
7. **`pickingPower`** for MCQ elimination skills — a skill that transfers across topics
8. **Full `practiceTest`** — measure real improvement under exam conditions
9. **`speedRace`** only if the student shows promise (score ≥ 50% or improving trend)

I specifically didn't recommend `speedRace` to students who are struggling (like STU_002 at 17%) because competitive pressure on a student who doesn't understand the concepts yet is counterproductive. The DOST selection is conditional on the student's performance tier.

For chapter-to-question matching, I used the `topic` field in the question bank and matched it loosely against the chapter name (lowercased, spaces to underscores). It's not perfect — the question bank has some topic mismatches (e.g., a Carnot engine question under `optics`) — but it produces good enough matches for a recommender prototype.

### How I Handled the Messy Marks Field

The marks field was intentionally inconsistent across five formats. My approach was to try each regex pattern in order of specificity — more specific patterns first (the slash + parentheses format), falling through to the plain number case at the end. I never raise an exception; I return 0.0 as a fallback.

The main assumption I made is for the `+pos -neg` format: I use `total_questions × 4` as the max score. This approximates JEE Mains marking (4 per correct question) but could be wrong for custom tests. I flagged this assumption in the code comments.

The other assumption: a plain number like `"22"` or `49` is treated as a raw score out of `total_questions × 4`. This means a student who scored 49 out of a 100-point test (49%) gets computed as 49/(25×4) = 49% anyway in this case, but a test with 30 questions would give 49/120 = 40.8% — which might or might not match the intended scale. Given the ambiguity, this is the best I can do without more metadata.

### Leaderboard Scoring Formula

I designed a 100-point composite score:
- **40 pts** — Average score % (most weight, it's the primary signal)
- **20 pts** — Completion rate (finishing tests shows discipline and builds stamina)
- **15 pts** — Attempt rate (not skipping questions, even hard ones)
- **15 pts** — Trend score (improving students get rewarded even if their absolute score is still low)
- **10 pts** — Speed score (efficiency, not just accuracy)

The trend component was important to include so that a student going from 20% → 40% gets recognized even though they're still below a student who's stable at 45%.

---

## Debug Process

### What the Bug Was

I found three bugs in `recommender_buggy.py`, all of which run without errors but silently produce wrong results:

**Bug 1 (get_weak_chapters):** The sort was `reverse=True`, which returns the strongest chapters instead of the weakest. The function name and docstring both say "weakest chapters" but the sort direction was wrong. This is the core bug — the entire recommendation is built on the wrong chapters.

**Bug 2 (get_questions_for_chapter):** The function was extracting `q.get("_id")` — the MongoDB ObjectID hex string — instead of `q.get("qid")`. So it returned things like `"3e3e04d42f8ac2acaf127972"` instead of `"Q_PHY_0031"`. The returned IDs look like valid identifiers but fail at the question lookup endpoint.

**Bug 3 (get_chapter_scores):** Each chapter in an attempt was credited the full session score. If an attempt covers two chapters and the student scores 60%, both chapters get +60 added to their total. This inflates scores for chapters that co-appear often in tests, making the averages unreliable.

### How I Found It

I ran the buggy version first and checked the output. The `weak_chapters` list contained chapters that clearly weren't weak (Laws of Motion and Electrostatics for STU_001, who had decent scores in those). That was the first flag.

I then traced through `get_weak_chapters` manually and immediately saw `reverse=True`. Classic off-by-one in sort direction — easy to miss because the rest of the function is correct.

For Bug 2, I compared the `question_ids` in the buggy output to the question bank and noticed they were hex strings, not `Q_PHY_XXXX` format. Traced it back to the `_id` vs `qid` confusion.

Bug 3 was subtler — I only caught it by computing the chapter averages by hand for STU_001 and noticing the numbers didn't match what I expected. The inflation made weak chapters look stronger than they were.

### What AI Suggested

I used Claude to help me reason through the bugs. It spotted Bug 1 immediately from the sort direction. For Bug 2, it suggested checking the return type of the IDs against the question bank schema — which led me to the `_id` vs `qid` distinction. Bug 3 was the one AI initially missed; it needed me to point out that the chapter score distribution math was wrong before it caught it. This is noted in the fixed file's comment block.

---

## What I'd Improve Given More Time

1. **Per-question accuracy tracking** — right now we only have which questions were slowest/fastest, not which were right or wrong. If we had correct/incorrect per question, the recommendations would be dramatically more precise.

2. **Topic-to-chapter mapping** — the question bank's `topic` field doesn't perfectly align with the attempt's `chapters` field. A proper mapping dictionary (e.g., `"kinematics"` → `["Kinematics", "1D Motion", "Projectile Motion"]`) would improve question selection significantly.

3. **Temporal decay** — recent attempts should weight more than old ones. A student who struggled in February but improved in March should see that reflected in the weakness detection.

4. **Adaptive difficulty within a session** — instead of assigning one difficulty label to an entire recommendation, the system should serve easier questions first and escalate difficulty based on responses.

5. **Persistent user state** — tracking which DOSTs have already been completed and not re-recommending them.

6. **Auth** — the current API has no authentication. For a real product, each student should only be able to query their own data.

---

## Project Structure

```
acadza-backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, router registration
│   ├── routers/
│   │   ├── analyze.py           # POST /analyze/{student_id}
│   │   ├── recommend.py         # POST /recommend/{student_id}
│   │   ├── question.py          # GET  /question/{question_id}
│   │   └── leaderboard.py       # GET  /leaderboard
│   ├── services/
│   │   ├── data_loader.py       # JSON loading, caching, ID normalization
│   │   ├── analyzer.py          # Performance analysis logic
│   │   ├── recommender.py       # DOST recommendation engine
│   │   ├── leaderboard.py       # Scoring + ranking
│   │   └── question_service.py  # Question lookup + HTML stripping
│   └── utils/
│       └── marks_normalizer.py  # 5-format marks normalization
├── data/
│   ├── student_performance.json
│   ├── question_bank.json
│   └── dost_config.json
├── debug/
│   ├── recommender_buggy.py     # Original buggy file
│   └── recommender_fixed.py     # Fixed file with full explanation
├── sample_outputs/              # STU_001.json through STU_010.json
└── requirements.txt
```
