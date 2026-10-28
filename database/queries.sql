-- Example analytical SQL queries for EduPilot AI (PostgreSQL)

-- 1. Weighted average % per student per course
SELECT u.name, c.course_name,
       ROUND((SUM(g.score / g.max_score * 100 * g.weight) / SUM(g.weight))::numeric, 1) AS weighted_avg
FROM grades g
JOIN users u   ON u.user_id = g.user_id
JOIN courses c ON c.course_id = g.course_id
GROUP BY u.name, c.course_name
ORDER BY weighted_avg;

-- 2. Attendance rate per course (late = 0.75, excused excluded)
SELECT c.course_name,
       ROUND(100.0 * SUM(CASE a.status WHEN 'present' THEN 1 WHEN 'late' THEN 0.75 ELSE 0 END)
             / NULLIF(COUNT(*) FILTER (WHERE a.status <> 'excused'), 0), 1) AS attendance_pct
FROM attendance a JOIN courses c ON c.course_id = a.course_id
WHERE a.status <> 'excused'
GROUP BY c.course_name;

-- 3. Students at risk: latest prediction per student/course below 60
SELECT DISTINCT ON (p.user_id, p.course_id)
       u.name, c.course_name, p.predicted_score, p.risk_level, p.created_at
FROM ai_predictions p
JOIN users u   ON u.user_id = p.user_id
JOIN courses c ON c.course_id = p.course_id
ORDER BY p.user_id, p.course_id, p.created_at DESC;
-- (wrap in a subquery and filter predicted_score < 60 to list only at-risk students)

-- 4. Study hours per week for one student (last 8 weeks)
SELECT date_trunc('week', session_date)::date AS week, ROUND(SUM(duration_minutes) / 60.0, 1) AS hours
FROM study_sessions
WHERE user_id = 1 AND session_date >= CURRENT_DATE - INTERVAL '8 weeks'
GROUP BY 1 ORDER BY 1;

-- 5. Upcoming and overdue assignments
SELECT a.title, c.course_name, a.due_date,
       CASE WHEN a.due_date < CURRENT_DATE THEN 'overdue' ELSE 'upcoming' END AS state
FROM assignments a JOIN courses c ON c.course_id = a.course_id
WHERE a.status <> 'completed'
ORDER BY a.due_date;

-- 6. Semantic search over lecture notes (pgvector cosine distance); :query_embedding is a 384-dim vector
SELECT d.filename, ch.page_number, LEFT(ch.content, 120) AS preview,
       1 - (ch.embedding <=> :query_embedding) AS similarity
FROM document_chunks ch JOIN documents d ON d.document_id = ch.document_id
WHERE d.user_id = 1
ORDER BY ch.embedding <=> :query_embedding
LIMIT 5;
