import DatabaseService from './DatabaseService';
import { v4 as uuidv4 } from 'react-native-uuid';

class KTWTestService {
    async createTest(user_id, testData) {
        const {
            left_ankle_angle,
            right_ankle_angle,
            distance_from_wall_cm,
            test_duration_seconds,
            notes,
        } = testData;

        const test_id = uuidv4();
        const timestamp = new Date().toISOString();

        await DatabaseService.execute(
            `INSERT INTO ktw_tests (
        test_id, user_id, timestamp, left_ankle_angle, right_ankle_angle,
        distance_from_wall_cm, test_duration_seconds, notes, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            [
                test_id, user_id, timestamp, left_ankle_angle, right_ankle_angle,
                distance_from_wall_cm, test_duration_seconds, notes, timestamp
            ]
        );

        return await this.getTestWithComparison(test_id, user_id);
    }

    async getUserTests(user_id, filters = {}) {
        let sql = 'SELECT * FROM ktw_tests WHERE user_id = ?';
        const params = [user_id];

        if (filters.start_date) {
            sql += ' AND timestamp >= ?';
            params.push(filters.start_date);
        }

        if (filters.end_date) {
            sql += ' AND timestamp <= ?';
            params.push(filters.end_date);
        }

        sql += ' ORDER BY timestamp DESC';

        if (filters.limit) {
            sql += ' LIMIT ?';
            params.push(filters.limit);
        }

        const tests = await DatabaseService.query(sql, params);

        // Get baseline for comparison
        const baseline = await this.getBaselineTest(user_id);

        return tests.map(test => ({
            ...test,
            comparison_to_baseline: baseline ? {
                left_ankle_improvement: test.left_ankle_angle - baseline.left_ankle_angle,
                right_ankle_improvement: test.right_ankle_angle - baseline.right_ankle_angle,
                baseline_left: baseline.left_ankle_angle,
                baseline_right: baseline.right_ankle_angle,
            } : null,
        }));
    }

    async getTestById(test_id) {
        const test = await DatabaseService.queryOne(
            'SELECT * FROM ktw_tests WHERE test_id = ?',
            [test_id]
        );

        if (!test) {
            throw new Error('Test not found');
        }

        return test;
    }

    async getTestWithComparison(test_id, user_id) {
        const test = await this.getTestById(test_id);
        const baseline = await this.getBaselineTest(user_id);

        return {
            ...test,
            comparison_to_baseline: baseline ? {
                left_ankle_improvement: test.left_ankle_angle - baseline.left_ankle_angle,
                right_ankle_improvement: test.right_ankle_angle - baseline.right_ankle_angle,
                baseline_left: baseline.left_ankle_angle,
                baseline_right: baseline.right_ankle_angle,
            } : null,
        };
    }

    async getBaselineTest(user_id) {
        const baseline = await DatabaseService.queryOne(
            'SELECT * FROM ktw_tests WHERE user_id = ? ORDER BY timestamp ASC LIMIT 1',
            [user_id]
        );

        return baseline;
    }

    async getTrendData(user_id) {
        const tests = await DatabaseService.query(
            'SELECT timestamp, left_ankle_angle, right_ankle_angle FROM ktw_tests WHERE user_id = ? ORDER BY timestamp ASC',
            [user_id]
        );

        return {
            left_ankle_progression: tests.map(t => ({
                date: t.timestamp,
                angle: t.left_ankle_angle,
            })),
            right_ankle_progression: tests.map(t => ({
                date: t.timestamp,
                angle: t.right_ankle_angle,
            })),
        };
    }

    async deleteTest(test_id, user_id) {
        const test = await DatabaseService.queryOne(
            'SELECT user_id FROM ktw_tests WHERE test_id = ?',
            [test_id]
        );

        if (!test) {
            throw new Error('Test not found');
        }

        if (test.user_id !== user_id) {
            throw new Error('Unauthorized');
        }

        await DatabaseService.execute('DELETE FROM ktw_tests WHERE test_id = ?', [test_id]);
        return { deleted: true };
    }
}

export default new KTWTestService();