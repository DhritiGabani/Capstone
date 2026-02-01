import * as SQLite from 'expo-sqlite';

class DatabaseService {
    constructor() {
        this.db = null;
    }

    async open() {
        try {
            this.db = await SQLite.openDatabaseAsync('dorsiflexx.db');
            console.log('✅ Database opened successfully');
            await this.createTables();
            await this.createIndexes();
        } catch (error) {
            console.error('❌ Error opening database:', error);
            throw error;
        }
    }

    async createTables() {
        const tables = [
            // Users table
            `CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        anonymous_id TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        age INTEGER NOT NULL CHECK (age > 0 AND age < 150),
        injury_type TEXT NOT NULL,
        baseline_rom REAL NOT NULL CHECK (baseline_rom >= 0 AND baseline_rom <= 90),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )`,

            // Sessions table
            `CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
        total_reps INTEGER NOT NULL CHECK (total_reps >= 0),
        avg_rom REAL NOT NULL CHECK (avg_rom >= 0 AND avg_rom <= 90),
        session_quality_score REAL NOT NULL CHECK (session_quality_score >= 0 AND session_quality_score <= 1),
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
      )`,

            // Metrics table
            `CREATE TABLE IF NOT EXISTS metrics (
        metric_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        exercise_type TEXT NOT NULL CHECK (exercise_type IN ('calf_raises', 'ankle_rotations', 'heel_walking')),
        rep_count INTEGER NOT NULL CHECK (rep_count >= 0),
        avg_rom REAL NOT NULL CHECK (avg_rom >= 0 AND avg_rom <= 90),
        max_rom REAL NOT NULL CHECK (max_rom >= 0 AND max_rom <= 90),
        min_rom REAL NOT NULL CHECK (min_rom >= 0 AND min_rom <= 90),
        tempo_consistency REAL NOT NULL CHECK (tempo_consistency >= 0 AND tempo_consistency <= 1),
        movement_consistency REAL NOT NULL CHECK (movement_consistency >= 0 AND movement_consistency <= 1),
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
      )`,

            // Goals table
            `CREATE TABLE IF NOT EXISTS goals (
        goal_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        goal_type TEXT NOT NULL CHECK (goal_type IN ('rom_target', 'session_count', 'rep_target', 'streak')),
        target_value REAL NOT NULL CHECK (target_value > 0),
        current_value REAL NOT NULL DEFAULT 0 CHECK (current_value >= 0),
        target_date TEXT NOT NULL,
        description TEXT NOT NULL,
        exercise_type TEXT CHECK (exercise_type IN ('calf_raises', 'ankle_rotations', 'heel_walking')),
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
      )`,

            // KTW Tests table
            `CREATE TABLE IF NOT EXISTS ktw_tests (
        test_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        left_ankle_angle REAL NOT NULL CHECK (left_ankle_angle >= 0 AND left_ankle_angle <= 90),
        right_ankle_angle REAL NOT NULL CHECK (right_ankle_angle >= 0 AND right_ankle_angle <= 90),
        distance_from_wall_cm REAL NOT NULL CHECK (distance_from_wall_cm > 0),
        test_duration_seconds INTEGER NOT NULL CHECK (test_duration_seconds > 0),
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
      )`,

            // Session data table (optional - for raw IMU data)
            `CREATE TABLE IF NOT EXISTS session_data (
        data_id TEXT PRIMARY KEY,
        session_id TEXT UNIQUE NOT NULL,
        imu1_data TEXT NOT NULL,
        imu2_data TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
      )`,
        ];

        try {
            for (const table of tables) {
                await this.db.execAsync(table);
            }
            console.log('✅ All tables created successfully');
        } catch (error) {
            console.error('❌ Error creating tables:', error);
            throw error;
        }
    }

    async createIndexes() {
        const indexes = [
            'CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)',
            'CREATE INDEX IF NOT EXISTS idx_users_anonymous_id ON users(anonymous_id)',
            'CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_sessions_user_timestamp ON sessions(user_id, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_metrics_session_id ON metrics(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_metrics_exercise_type ON metrics(exercise_type)',
            'CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)',
            'CREATE INDEX IF NOT EXISTS idx_goals_user_status ON goals(user_id, status)',
            'CREATE INDEX IF NOT EXISTS idx_ktw_tests_user_id ON ktw_tests(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_ktw_tests_timestamp ON ktw_tests(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_ktw_tests_user_timestamp ON ktw_tests(user_id, timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_session_data_session_id ON session_data(session_id)',
        ];

        try {
            for (const index of indexes) {
                await this.db.execAsync(index);
            }
            console.log('✅ All indexes created successfully');
        } catch (error) {
            console.error('❌ Error creating indexes:', error);
        }
    }

    async execute(sql, params = []) {
        try {
            const result = await this.db.runAsync(sql, params);
            return result;
        } catch (error) {
            console.error('❌ Database query error:', error);
            throw error;
        }
    }

    async query(sql, params = []) {
        try {
            const result = await this.db.getAllAsync(sql, params);
            return result;
        } catch (error) {
            console.error('❌ Database query error:', error);
            throw error;
        }
    }

    async queryOne(sql, params = []) {
        try {
            const result = await this.db.getFirstAsync(sql, params);
            return result;
        } catch (error) {
            console.error('❌ Database query error:', error);
            throw error;
        }
    }

    async transaction(callback) {
        try {
            await this.db.withTransactionAsync(callback);
        } catch (error) {
            console.error('❌ Transaction error:', error);
            throw error;
        }
    }

    async close() {
        if (this.db) {
            await this.db.closeAsync();
            console.log('Database closed');
        }
    }

    async dropAllTables() {
        const tables = ['session_data', 'metrics', 'sessions', 'ktw_tests', 'goals', 'users'];
        try {
            for (const table of tables) {
                await this.db.execAsync(`DROP TABLE IF EXISTS ${table}`);
            }
            console.log('✅ All tables dropped');
        } catch (error) {
            console.error('❌ Error dropping tables:', error);
            throw error;
        }
    }
}

export default new DatabaseService();