import pool from '../db/index.js';

export async function analyzeStudent(studentId) {
  // All attempts
  const { rows: attempts } = await pool.query(
    `SELECT * FROM attempts WHERE student_id = $1 ORDER BY date ASC`,
    [studentId]
  );
  if (!attempts.length) return null;

  // ── Score trend ───────────────────────────────────────
  const scoreTrend = attempts.map(a => ({
    attempt_id: a.attempt_id,
    date: a.date,
    subject: a.subject,
    marks_pct: a.marks_pct ? +a.marks_pct : null,
    marks_score: a.marks_score ? +a.marks_score : null,
    completed: a.completed
  }));

  // ── Subject breakdown ─────────────────────────────────
  const subjectMap = {};
  for (const a of attempts) {
    const s = a.subject;
    if (!subjectMap[s]) subjectMap[s] = { attempts: 0, totalPct: 0, withPct: 0, totalTime: 0 };
    subjectMap[s].attempts++;
    subjectMap[s].totalTime += a.avg_time_per_question_sec || 0;
    if (a.marks_pct != null) {
      subjectMap[s].totalPct += +a.marks_pct;
      subjectMap[s].withPct++;
    }
  }
  const subjectBreakdown = Object.entries(subjectMap).map(([subject, d]) => ({
    subject,
    attempts: d.attempts,
    avg_pct: d.withPct ? +(d.totalPct / d.withPct).toFixed(1) : null,
    avg_time_per_q_sec: +(d.totalTime / d.attempts).toFixed(0)
  }));

  // ── Chapter breakdown ─────────────────────────────────
  const chapterMap = {};
  for (const a of attempts) {
    for (const ch of (a.chapters || [])) {
      if (!chapterMap[ch]) chapterMap[ch] = { attempts: 0, totalPct: 0, withPct: 0, subject: a.subject };
      chapterMap[ch].attempts++;
      if (a.marks_pct != null) {
        chapterMap[ch].totalPct += +a.marks_pct;
        chapterMap[ch].withPct++;
      }
    }
  }
  const chapterBreakdown = Object.entries(chapterMap).map(([chapter, d]) => ({
    chapter,
    subject: d.subject,
    attempts: d.attempts,
    avg_pct: d.withPct ? +(d.totalPct / d.withPct).toFixed(1) : null
  })).sort((a, b) => (a.avg_pct ?? 100) - (b.avg_pct ?? 100));

  // ── Strengths / weaknesses ────────────────────────────
  const withPct = chapterBreakdown.filter(c => c.avg_pct !== null);
  const weakChapters    = withPct.filter(c => c.avg_pct < 50);
  const strongChapters  = withPct.filter(c => c.avg_pct >= 70);

  // ── Speed analysis ────────────────────────────────────
  const avgSpeed = attempts.reduce((s, a) => s + (a.avg_time_per_question_sec || 0), 0) / attempts.length;
  const speedFlag = avgSpeed > 120 ? 'slow' : avgSpeed < 40 ? 'very_fast' : 'normal';

  // ── Completion rate ───────────────────────────────────
  const completionRate = +(attempts.filter(a => a.completed).length / attempts.length * 100).toFixed(1);

  // ── Attempt coverage ──────────────────────────────────
  const skippedRate = +(
    attempts.reduce((s, a) => s + (a.skipped || 0), 0) /
    attempts.reduce((s, a) => s + (a.total_questions || 1), 0) * 100
  ).toFixed(1);

  return {
    student_id: studentId,
    total_sessions: attempts.length,
    completion_rate_pct: completionRate,
    skipped_rate_pct: skippedRate,
    avg_time_per_question_sec: +avgSpeed.toFixed(0),
    speed_flag: speedFlag,
    score_trend: scoreTrend,
    subject_breakdown: subjectBreakdown,
    chapter_breakdown: chapterBreakdown,
    weak_chapters: weakChapters,
    strong_chapters: strongChapters
  };
}