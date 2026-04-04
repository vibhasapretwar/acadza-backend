import pool from '../db/index.js';
import { parseMarks } from './parseMarks.js';
import { stripHtml } from './stripHtml.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const load = f => JSON.parse(fs.readFileSync(path.join(__dirname, '../../data', f), 'utf8'));

function resolveId(id) {
  if (!id) return null;
  if (typeof id === 'string') return id;
  if (id.$oid) return id.$oid;
  return String(id);
}

const perf  = load('student_performance.json');
const qbank = load('question_bank.json');
const dosts = load('dost_config.json');

// ── Students ──────────────────────────────────────────────
const studentIds = [...new Set(perf.map(a => a.student_id))];
for (const id of studentIds) {
  await pool.query(
    `INSERT INTO students VALUES ($1,$2) ON CONFLICT DO NOTHING`,
    [id, `Student ${id}`]
  );
}
console.log(`✅ ${studentIds.length} students`);

// ── Attempts ──────────────────────────────────────────────
let aCount = 0;
for (const a of perf) {
  const { score, total, pct } = parseMarks(a.marks);
  await pool.query(
    `INSERT INTO attempts VALUES
     ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
     ON CONFLICT DO NOTHING`,
    [
      a.attempt_id, a.student_id, a.date, a.mode, a.exam_pattern,
      a.subject, a.chapters,
      a.duration_minutes ?? null, a.time_taken_minutes,
      a.completed,
      a.total_questions, a.attempted, a.skipped,
      String(a.marks), score, total, pct,
      a.avg_time_per_question_seconds,
      a.slowest_question_id ?? null,
      a.fastest_question_id ?? null
    ]
  );
  aCount++;
}
console.log(`✅ ${aCount} attempts`);

// ── Questions ─────────────────────────────────────────────
const seen = new Set();
let qCount = 0, qSkip = 0;
for (const q of qbank) {
  const id = resolveId(q._id);
  if (!id || seen.has(id)) { qSkip++; continue; }
  seen.add(id);

  const content = q.scq || q.mcq || q.integerQuestion || {};
  const qHtml   = content.question || null;
  const answer  = content.answer   ?? null;
  const hasIssues = !answer || q.difficulty == null;

  await pool.query(
    `INSERT INTO questions VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
     ON CONFLICT DO NOTHING`,
    [
      id, q.questionType, q.subject, q.topic, q.subtopic,
      q.difficulty ?? null,
      qHtml, qHtml ? stripHtml(qHtml) : null,
      content.solution || null,
      answer, hasIssues
    ]
  );
  qCount++;
}
console.log(`✅ ${qCount} questions (skipped ${qSkip} duplicates)`);

// ── DOST Configs ──────────────────────────────────────────
for (const [type, config] of Object.entries(dosts)) {
  await pool.query(
    `INSERT INTO dost_configs VALUES ($1,$2)
     ON CONFLICT (dost_type) DO UPDATE SET config = $2`,
    [type, JSON.stringify(config)]
  );
}
console.log(`✅ DOST configs`);

await pool.end();
console.log('🎉 Seed complete');