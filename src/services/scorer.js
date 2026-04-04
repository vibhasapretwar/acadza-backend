import pool from '../db/index.js';
import { analyzeStudent } from './analyzer.js';

export async function buildLeaderboard() {
  const { rows: students } = await pool.query(`SELECT student_id FROM students`);

  const ranked = [];

  for (const { student_id } of students) {
    const a = await analyzeStudent(student_id);
    if (!a) continue;

    // ── Scoring formula ───────────────────────────────────
    // 40% accuracy  + 25% speed  + 20% completion  + 15% consistency
    const withPct = a.subject_breakdown.filter(s => s.avg_pct !== null);
    const accuracyScore = withPct.length
      ? withPct.reduce((s, x) => s + x.avg_pct, 0) / withPct.length
      : 0;

    // Speed score: ideal ~60s/q. Penalise slow (>120) and reward fast (<80)
    const rawSpeed = a.avg_time_per_question_sec;
    const speedScore = Math.max(0, Math.min(100, 100 - (rawSpeed - 60) * 0.5));

    const completionScore = a.completion_rate_pct;

    // Consistency: low variance across attempts = high score
    const pcts = a.score_trend.map(t => t.marks_pct).filter(p => p !== null);
    let consistencyScore = 50;
    if (pcts.length > 1) {
      const mean = pcts.reduce((s, v) => s + v, 0) / pcts.length;
      const variance = pcts.reduce((s, v) => s + (v - mean) ** 2, 0) / pcts.length;
      consistencyScore = Math.max(0, 100 - Math.sqrt(variance));
    }

    const finalScore = +(
      accuracyScore    * 0.40 +
      speedScore       * 0.25 +
      completionScore  * 0.20 +
      consistencyScore * 0.15
    ).toFixed(2);

    const strength  = a.strong_chapters[0]?.chapter ?? a.subject_breakdown.sort((x,y) => (y.avg_pct??0)-(x.avg_pct??0))[0]?.subject ?? '—';
    const weakness  = a.weak_chapters[0]?.chapter   ?? a.subject_breakdown.sort((x,y) => (x.avg_pct??0)-(y.avg_pct??0))[0]?.subject ?? '—';
    const focusArea = a.weak_chapters[0]?.chapter   ?? weakness;

    ranked.push({ student_id, score: finalScore, strength, weakness, focus_area: focusArea });
  }

  return ranked
    .sort((a, b) => b.score - a.score)
    .map((s, i) => ({ rank: i + 1, ...s }));
}