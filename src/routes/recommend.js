import { Router } from 'express';
import { recommendForStudent } from '../services/recommender.js';

const router = Router();

router.post('/:studentId', async (req, res) => {
  try {
    const result = await recommendForStudent(req.params.studentId);
    if (!result) return res.status(404).json({ error: 'Student not found' });
    res.json(result);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

export default router;