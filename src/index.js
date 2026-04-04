import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
dotenv.config();

import analyzeRouter    from './routes/analyze.js';
import recommendRouter  from './routes/recommend.js';
import questionRouter   from './routes/question.js';
import leaderboardRouter from './routes/leaderboard.js';

const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => res.json({ status: 'ok' }));

app.use('/analyze',     analyzeRouter);
app.use('/recommend',   recommendRouter);
app.use('/question',    questionRouter);
app.use('/leaderboard', leaderboardRouter);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));