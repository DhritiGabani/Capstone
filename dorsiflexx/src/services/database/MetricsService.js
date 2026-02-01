import DatabaseService from './DatabaseService';

class MetricsService {
  async getProgressSummary(user_id, period_days = 30) {
    const start_date = new Date();
    start_date.setDate(start_date.getDate() - period_days);
    const start_date_str = start_date.toISOString();

    // Get aggregate session stats
    const summary = await DatabaseService.queryOne(
      `SELECT 
        COUNT(*) as total_sessions,
        SUM(duration_minutes) as total_duration_minutes,
        SUM(total_reps) as total_reps,
        AVG(avg_rom) as avg_rom,
        AVG(session_quality_score) as avg_quality
      FROM sessions
      WHERE user_id = ? AND timestamp >= ?`,
      [user_id, start_date_str]
    );

    // Get exercise breakdown
    const exerciseBreakdown = await DatabaseService.query(
      `SELECT 
        m.exercise_type,
        COUNT(DISTINCT m.session_id) as session_count,
        SUM(m.rep_count) as total_reps,
        AVG(m.avg_rom) as avg_rom,
        MAX(m.max_rom) as best_rom
      FROM metrics m
      JOIN sessions s ON m.session_id = s.session_id
      WHERE s.user_id = ? AND s.timestamp >= ?
      GROUP BY m.exercise_type`,
      [user_id, start_date_str]
    );

    const exercises = {};
    exerciseBreakdown.forEach(ex => {
      exercises[ex.exercise_type] = {
        session_count: ex.session_count,
        total_reps: ex.total_reps,
        avg_rom: ex.avg_rom,
        best_rom: ex.best_rom,
      };
    });

    // Get user baseline
    const user = await DatabaseService.queryOne(
      'SELECT baseline_rom FROM users WHERE user_id = ?',
      [user_id]
    );

    const improvement = {
      start: user.baseline_rom,
      end: summary.avg_rom || user.baseline_rom,
      change: (summary.avg_rom || user.baseline_rom) - user.baseline_rom,
      percent_change: user.baseline_rom > 0
        ? (((summary.avg_rom || user.baseline_rom) - user.baseline_rom) / user.baseline_rom) * 100
        : 0,
    };

    // Calculate streaks
    const streaks = await this.calculateStreaks(user_id);

    return {
      period: `${period_days}days`,
      total_sessions: summary.total_sessions || 0,
      total_duration_minutes: summary.total_duration_minutes || 0,
      total_reps: summary.total_reps || 0,
      avg_rom: summary.avg_rom || 0,
      exercises,
      improvement,
      streaks,
    };
  }

  async calculateStreaks(user_id) {
    const sessions = await DatabaseService.query(
      `SELECT DATE(timestamp) as session_date
       FROM sessions
       WHERE user_id = ?
       ORDER BY timestamp DESC`,
      [user_id]
    );

    if (sessions.length === 0) {
      return { current_streak_days: 0, longest_streak_days: 0 };
    }

    const today = new Date().toISOString().split('T')[0];
    const uniqueDates = [...new Set(sessions.map(s => s.session_date))];

    let current_streak = 0;
    let longest_streak = 0;
    let temp_streak = 1;

    // Calculate current streak
    if (uniqueDates[0] === today || this.isYesterday(uniqueDates[0])) {
      current_streak = 1;
      for (let i = 1; i < uniqueDates.length; i++) {
        if (this.isConsecutiveDay(uniqueDates[i - 1], uniqueDates[i])) {
          current_streak++;
        } else {
          break;
        }
      }
    }

    // Calculate longest streak
    for (let i = 1; i < uniqueDates.length; i++) {
      if (this.isConsecutiveDay(uniqueDates[i - 1], uniqueDates[i])) {
        temp_streak++;
        longest_streak = Math.max(longest_streak, temp_streak);
      } else {
        temp_streak = 1;
      }
    }

    return {
      current_streak_days: current_streak,
      longest_streak_days: Math.max(longest_streak, current_streak),
    };
  }

  isYesterday(dateString) {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    return dateString === yesterday.toISOString().split('T')[0];
  }

  isConsecutiveDay(date1, date2) {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    const diffDays = Math.abs((d1 - d2) / (1000 * 60 * 60 * 24));
    return diffDays === 1;
  }

  async getTrendData(user_id, metric, period_days, granularity = 'weekly') {
    const start_date = new Date();
    start_date.setDate(start_date.getDate() - period_days);
    const start_date_str = start_date.toISOString();

    let dateFormat;
    if (granularity === 'daily') {
      dateFormat = '%Y-%m-%d';
    } else if (granularity === 'weekly') {
      dateFormat = '%Y-W%W';
    } else {
      dateFormat = '%Y-%m';
    }

    const column = metric === 'rom' ? 'avg_rom' : 'total_reps';

    const data = await DatabaseService.query(
      `SELECT 
        strftime('${dateFormat}', timestamp) as period,
        AVG(${column}) as value,
        COUNT(*) as session_count
      FROM sessions
      WHERE user_id = ? AND timestamp >= ?
      GROUP BY period
      ORDER BY timestamp ASC`,
      [user_id, start_date_str]
    );

    const values = data.map(d => d.value);
    const statistics = {
      min: values.length > 0 ? Math.min(...values) : 0,
      max: values.length > 0 ? Math.max(...values) : 0,
      avg: values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0,
      trend: this.determineTrend(values),
    };

    return {
      metric,
      period: `${period_days}days`,
      granularity,
      data_points: data.map(d => ({
        date: d.period,
        value: d.value,
        session_count: d.session_count,
      })),
      statistics,
    };
  }

  determineTrend(values) {
    if (values.length < 2) return 'stable';

    const firstHalf = values.slice(0, Math.floor(values.length / 2));
    const secondHalf = values.slice(Math.floor(values.length / 2));

    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;

    const change = ((secondAvg - firstAvg) / firstAvg) * 100;

    if (change > 5) return 'improving';
    if (change < -5) return 'declining';
    return 'stable';
  }
}

export default new MetricsService();