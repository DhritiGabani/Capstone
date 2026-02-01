import DatabaseService from './DatabaseService';
import { v4 as uuidv4 } from 'react-native-uuid';

class SessionService {
    async createSession(user_id, sessionData) {
        const { duration_minutes, exercises } = sessionData;

        // Calculate aggregate metrics
        const total_reps = exercises.reduce((sum, ex) => sum + ex.rep_count, 0);
        const avg_rom = exercises.reduce((sum, ex) => sum + ex.avg_rom, 0) / exercises.length;
        const quality_scores = exercises.map(ex => (ex.tempo_consistency + ex.movement_consistency) / 2);
        const session_quality_score = quality_scores.reduce((sum, s) => sum + s, 0) / quality_scores.length;

        const session_id = uuidv4();
        const timestamp = new Date().toISOString();

        await DatabaseService.transaction(async () => {
            // Insert session
            await DatabaseService.execute(
                `INSERT INTO sessions (
          session_id, user_id, timestamp, duration_minutes,
          total_reps, avg_rom, session_quality_score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
                [session_id, user_id, timestamp, duration_minutes, total_reps, avg_rom, session_quality_score, timestamp]
            );

            // Insert metrics for each exercise
            for (const exercise of exercises) {
                const metric_id = uuidv4();
                await DatabaseService.execute(
                    `INSERT INTO metrics (
            metric_id, session_id, exercise_type, rep_count,
            avg_rom, max_rom, min_rom, tempo_consistency, movement_consistency
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                    [
                        metric_id, session_id, exercise.exercise_type, exercise.rep_count,
                        exercise.avg_rom, exercise.max_rom, exercise.min_rom,
                        exercise.tempo_consistency, exercise.movement_consistency
                    ]
                );
            }
        });

        return {
            session_id,
            timestamp,
            total_reps,
            avg_rom,
            session_quality_score,
        };
    }

    async getUserSessions(user_id, filters = {}) {
        let sql = `
      SELECT 
        s.*,
        GROUP_CONCAT(m.exercise_type) as exercises
      FROM sessions s
      LEFT JOIN metrics m ON s.session_id = m.session_id
      WHERE s.user_id = ?
    `;

        const params = [user_id];

        if (filters.start_date) {
            sql += ' AND s.timestamp >= ?';
            params.push(filters.start_date);
        }

        if (filters.end_date) {
            sql += ' AND s.timestamp <= ?';
            params.push(filters.end_date);
        }

        if (filters.exercise_type) {
            sql += ' AND m.exercise_type = ?';
            params.push(filters.exercise_type);
        }

        sql += ' GROUP BY s.session_id ORDER BY s.timestamp DESC';

        if (filters.limit) {
            sql += ' LIMIT ?';
            params.push(filters.limit);
        }

        const sessions = await DatabaseService.query(sql, params);

        return sessions.map(session => ({
            ...session,
            exercises: session.exercises ? session.exercises.split(',') : [],
        }));
    }

    async getSessionDetails(session_id) {
        const session = await DatabaseService.queryOne(
            'SELECT * FROM sessions WHERE session_id = ?',
            [session_id]
        );

        if (!session) {
            throw new Error('Session not found');
        }

        const exercises = await DatabaseService.query(
            'SELECT * FROM metrics WHERE session_id = ?',
            [session_id]
        );

        return {
            ...session,
            exercises,
        };
    }

    async deleteSession(session_id, user_id) {
        const session = await DatabaseService.queryOne(
            'SELECT user_id FROM sessions WHERE session_id = ?',
            [session_id]
        );

        if (!session) {
            throw new Error('Session not found');
        }

        if (session.user_id !== user_id) {
            throw new Error('Unauthorized');
        }

        await DatabaseService.transaction(async () => {
            await DatabaseService.execute('DELETE FROM metrics WHERE session_id = ?', [session_id]);
            await DatabaseService.execute('DELETE FROM sessions WHERE session_id = ?', [session_id]);
        });

        return { deleted: true };
    }

    async getSessionCount(user_id, filters = {}) {
        let sql = 'SELECT COUNT(*) as count FROM sessions WHERE user_id = ?';
        const params = [user_id];

        if (filters.start_date) {
            sql += ' AND timestamp >= ?';
            params.push(filters.start_date);
        }

        if (filters.end_date) {
            sql += ' AND timestamp <= ?';
            params.push(filters.end_date);
        }

        const result = await DatabaseService.queryOne(sql, params);
        return result.count;
    }
}

export default new SessionService();