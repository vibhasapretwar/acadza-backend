import { Router } from 'express';
import { analyzeStudent } from '../services/analyzer.js';

const router = Router();

router.post('/:studentId', async (req, res) => {
  try {
    const result = await analyzeStudent(req.params.studentId);
    if (!result) return res.status(404).json({ error: 'Student not found' });
    res.json(result);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

export default router;