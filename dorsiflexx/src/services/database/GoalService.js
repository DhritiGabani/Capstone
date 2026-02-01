import DatabaseService from './DatabaseService';
import { v4 as uuidv4 } from 'react-native-uuid';

class GoalService {
    async createGoal(user_id, goalData) {
        const { goal_type, target_value, target_date, description, exercise_type } = goalData;

        const goal_id = uuidv4();
        const timestamp = new Date().toISOString();
        const current_value = 0;

        await DatabaseService.execute(
            `INSERT INTO goals (
        goal_id, user_id, goal_type, target_value, current_value,
        target_date, description, exercise_type, status, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)`,
            [goal_id, user_id, goal_type, target_value, current_value, target_date, description, exercise_type, timestamp, timestamp]
        );

        return await this.getGoalById(goal_id);
    }

    async getUserGoals(user_id, status = null) {
        let sql = 'SELECT * FROM goals WHERE user_id = ?';
        const params = [user_id];

        if (status) {
            sql += ' AND status = ?';
            params.push(status);
        }

        sql += ' ORDER BY created_at DESC';

        const goals = await DatabaseService.query(sql, params);

        return goals.map(goal => this.enrichGoalWithProgress(goal));
    }

    async getGoalById(goal_id) {
        const goal = await DatabaseService.queryOne(
            'SELECT * FROM goals WHERE goal_id = ?',
            [goal_id]
        );

        if (!goal) {
            throw new Error('Goal not found');
        }

        return this.enrichGoalWithProgress(goal);
    }

    enrichGoalWithProgress(goal) {
        const progress_percent = Math.min(100, Math.round((goal.current_value / goal.target_value) * 100));
        const target_date = new Date(goal.target_date);
        const now = new Date();
        const days_remaining = Math.ceil((target_date - now) / (1000 * 60 * 60 * 24));

        const created_date = new Date(goal.created_at);
        const total_days = Math.ceil((target_date - created_date) / (1000 * 60 * 60 * 24));
        const days_elapsed = total_days - days_remaining;
        const expected_progress = total_days > 0 ? (days_elapsed / total_days) * 100 : 0;
        const on_track = progress_percent >= expected_progress;

        return {
            ...goal,
            progress_percent,
            days_remaining,
            on_track,
        };
    }

    async updateGoal(goal_id, updates) {
        const allowedFields = ['target_value', 'target_date', 'description', 'current_value', 'status'];
        const fields = [];
        const values = [];

        Object.keys(updates).forEach(key => {
            if (allowedFields.includes(key)) {
                fields.push(`${key} = ?`);
                values.push(updates[key]);
            }
        });

        if (fields.length === 0) {
            throw new Error('No valid fields to update');
        }

        fields.push('updated_at = ?');
        values.push(new Date().toISOString());

        if (updates.status === 'completed' && !updates.completed_at) {
            fields.push('completed_at = ?');
            values.push(new Date().toISOString());
        }

        values.push(goal_id);

        await DatabaseService.execute(
            `UPDATE goals SET ${fields.join(', ')} WHERE goal_id = ?`,
            values
        );

        return await this.getGoalById(goal_id);
    }

    async updateGoalProgress(user_id, progressData) {
        const { total_reps, avg_rom, session_count } = progressData;

        const activeGoals = await this.getUserGoals(user_id, 'active');

        for (const goal of activeGoals) {
            let newValue = goal.current_value;

            if (goal.goal_type === 'rom_target') {
                newValue = Math.max(newValue, avg_rom);
            } else if (goal.goal_type === 'rep_target') {
                newValue += total_reps;
            } else if (goal.goal_type === 'session_count') {
                newValue += session_count;
            }

            await this.updateGoal(goal.goal_id, { current_value: newValue });

            // Auto-complete if target reached
            if (newValue >= goal.target_value) {
                await this.updateGoal(goal.goal_id, { status: 'completed' });
            }
        }
    }

    async completeGoal(goal_id) {
        return await this.updateGoal(goal_id, {
            status: 'completed',
            completed_at: new Date().toISOString(),
        });
    }

    async deleteGoal(goal_id, user_id) {
        const goal = await DatabaseService.queryOne(
            'SELECT user_id FROM goals WHERE goal_id = ?',
            [goal_id]
        );

        if (!goal) {
            throw new Error('Goal not found');
        }

        if (goal.user_id !== user_id) {
            throw new Error('Unauthorized');
        }

        await DatabaseService.execute('DELETE FROM goals WHERE goal_id = ?', [goal_id]);
        return { deleted: true };
    }
}

export default new GoalService();