import { Router } from 'express';
import { buildLeaderboard } from '../services/scorer.js';

const router = Router();

router.get('/', async (_req, res) => {
  try {
    const board = await buildLeaderboard();
    res.json({ leaderboard: board, total: board.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;