export function parseMarks(marks) {
  if (marks === null || marks === undefined)
    return { score: null, total: null, pct: null };

  const s = String(marks).trim();

  // "+52 -8"  →  net score
  const signed = s.match(/^\+(\d+(?:\.\d+)?)\s*-(\d+(?:\.\d+)?)$/);
  if (signed)
    return { score: +signed[1] - +signed[2], total: null, pct: null };

  // "34/75 (45.3%)"
  const withPct = s.match(/^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)\s*\([\d.]+%\)/);
  if (withPct) {
    const score = +withPct[1], total = +withPct[2];
    return { score, total, pct: +((score / total) * 100).toFixed(2) };
  }

  // "68/100"
  const fraction = s.match(/^(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/);
  if (fraction) {
    const score = +fraction[1], total = +fraction[2];
    return { score, total, pct: +((score / total) * 100).toFixed(2) };
  }

  // plain number
  const plain = s.match(/^-?\d+(?:\.\d+)?$/);
  if (plain) return { score: +s, total: null, pct: null };

  return { score: null, total: null, pct: null };
}