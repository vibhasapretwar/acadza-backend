import pool from '../db/index.js';
import { analyzeStudent } from './analyzer.js';

// Maps weakness profile → best DOST type
function pickDost(profile) {
  if (profile === 'no_concept')   return 'concept';
  if (profile === 'needs_formula') return 'formula';
  if (profile === 'slow')         return 'clickingPower';
  if (profile === 'inaccurate')   return 'pickingPower';
  if (profile === 'needs_drill')  return 'practiceAssignment';
  if (profile === 'ready')        return 'practiceTest';
  if (profile === 'speed_race')   return 'speedRace';
  return 'practiceAssignment';
}

async function getQuestions(subject, topic, difficulty, limit = 5) {
  const { rows } = await pool.query(
    `SELECT question_id, question_type, topic, subtopic, difficulty, question_text
     FROM questions
     WHERE has_issues = FALSE
       AND LOWER(subject) = LOWER($1)
       AND ($2::text IS NULL OR LOWER(topic) LIKE LOWER($2))
       AND ($3::int  IS NULL OR difficulty = $3)
     ORDER BY RANDOM()
     LIMIT $4`,
    [subject, topic ? `%${topic}%` : null, difficulty ?? null, limit]
  );
  return rows;
}

async function getDostConfig(type) {
  const { rows } = await pool.query(
    `SELECT config FROM dost_configs WHERE dost_type = $1`, [type]
  );
  return rows[0]?.config ?? {};
}

export async function recommendForStudent(studentId) {
  const analysis = await analyzeStudent(studentId);
  if (!analysis) return null;

  const steps = [];

  // ── Step 1: Address weakest chapter with concept/formula ──
  if (analysis.weak_chapters.length > 0) {
    const worst = analysis.weak_chapters[0];
    const profile = worst.avg_pct < 30 ? 'no_concept' : 'needs_formula';
    const dostType = pickDost(profile);
    const config   = await getDostConfig(dostType);
    const questions = await getQuestions(worst.subject, worst.chapter, null, 5);

    steps.push({
      step: 1,
      dost_type: dostType,
      target_chapter: worst.chapter,
      subject: worst.subject,
      config,
      question_ids: questions.map(q => q.question_id),
      questions_preview: questions,
      reasoning: `Your accuracy in ${worst.chapter} is ${worst.avg_pct}% — well below target. Start by ${profile === 'no_concept' ? 'building the concept from scratch' : 'revising key formulas'}.`,
      message: `Hey! Let's fix ${worst.chapter} first. ${profile === 'no_concept' ? 'Watch the concept video and understand the fundamentals.' : 'Quick formula revision — 10 minutes max.'} You'll feel the difference immediately.`
    });
  }

  // ── Step 2: Speed drill if slow ───────────────────────────
  if (analysis.speed_flag === 'slow') {
    const subject = analysis.subject_breakdown[0]?.subject ?? 'Physics';
    const dostType = 'clickingPower';
    const config   = await getDostConfig(dostType);
    const questions = await getQuestions(subject, null, 2, 10);

    steps.push({
      step: 2,
      dost_type: dostType,
      target_chapter: 'Mixed',
      subject,
      config,
      question_ids: questions.map(q => q.question_id),
      questions_preview: questions,
      reasoning: `Your average time per question is ${analysis.avg_time_per_question_sec}s — too slow for exam conditions. Speed drills build automaticity.`,
      message: `You're spending too long per question. Let's do a rapid-fire round — 10 questions, no overthinking. Train your brain to decide fast.`
    });
  }

  // ── Step 3: Targeted assignment on second weakest ─────────
  if (analysis.weak_chapters.length > 1) {
    const second = analysis.weak_chapters[1];
    const dostType = 'practiceAssignment';
    const config   = await getDostConfig(dostType);
    const questions = await getQuestions(second.subject, second.chapter, 3, 8);

    steps.push({
      step: 3,
      dost_type: dostType,
      target_chapter: second.chapter,
      subject: second.subject,
      config,
      question_ids: questions.map(q => q.question_id),
      questions_preview: questions,
      reasoning: `${second.chapter} needs targeted practice. Untimed assignment lets you think deeply without pressure.`,
      message: `Now tackle ${second.chapter} properly. No timer — just focus on understanding each question fully.`
    });
  }

  // ── Step 4: MCQ elimination on low-accuracy subject ───────
  const weakSubject = analysis.subject_breakdown
    .filter(s => s.avg_pct !== null)
    .sort((a, b) => a.avg_pct - b.avg_pct)[0];

  if (weakSubject && weakSubject.avg_pct < 60) {
    const dostType = 'pickingPower';
    const config   = await getDostConfig(dostType);
    const questions = await getQuestions(weakSubject.subject, null, 2, 6);

    steps.push({
      step: steps.length + 1,
      dost_type: dostType,
      target_chapter: 'Mixed',
      subject: weakSubject.subject,
      config,
      question_ids: questions.map(q => q.question_id),
      questions_preview: questions,
      reasoning: `${weakSubject.subject} accuracy is ${weakSubject.avg_pct}%. Option elimination practice reduces wrong guesses significantly.`,
      message: `In ${weakSubject.subject}, you're losing marks you shouldn't. Let's practice eliminating wrong options — a skill that instantly improves your score.`
    });
  }

  // ── Step 5: If strong overall → full mock test ────────────
  const overallPct = analysis.subject_breakdown
    .filter(s => s.avg_pct !== null)
    .reduce((s, x) => s + x.avg_pct, 0) / (analysis.subject_breakdown.filter(s => s.avg_pct !== null).length || 1);

  if (overallPct >= 65 || analysis.strong_chapters.length >= 3) {
    const dostType = 'practiceTest';
    const config   = await getDostConfig(dostType);

    steps.push({
      step: steps.length + 1,
      dost_type: dostType,
      target_chapter: 'Full Syllabus',
      subject: 'All',
      config,
      question_ids: [],
      questions_preview: [],
      reasoning: `Overall average is ${overallPct.toFixed(1)}% — you're ready to simulate exam conditions.`,
      message: `You've put in the work. Time for a full mock test — treat it like the real exam. Check your time management and identify any remaining gaps.`
    });
  }

  return {
    student_id: studentId,
    generated_at: new Date().toISOString(),
    analysis_summary: {
      weak_chapters: analysis.weak_chapters.map(c => c.chapter),
      strong_chapters: analysis.strong_chapters.map(c => c.chapter),
      speed_flag: analysis.speed_flag,
      completion_rate: analysis.completion_rate_pct
    },
    total_steps: steps.length,
    steps
  };
}