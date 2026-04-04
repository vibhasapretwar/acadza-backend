import { Router } from 'express';
import pool from '../db/index.js';

const router = Router();

router.get('/:questionId', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT * FROM questions WHERE question_id = $1`,
      [req.params.questionId]
    );
    if (!rows.length) return res.status(404).json({ error: 'Question not found' });

    const q = rows[0];
    res.json({
      question_id:   q.question_id,
      question_type: q.question_type,
      subject:       q.subject,
      topic:         q.topic,
      subtopic:      q.subtopic,
      difficulty:    q.difficulty,
      question_text: q.question_text,
      answer:        q.answer,
      has_issues:    q.has_issues
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;