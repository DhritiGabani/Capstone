import DatabaseService from './DatabaseService';
import { v4 as uuidv4 } from 'react-native-uuid';
import * as Crypto from 'expo-crypto';

class UserService {
    async hashPassword(password) {
        const hash = await Crypto.digestStringAsync(
            Crypto.CryptoDigestAlgorithm.SHA256,
            password
        );
        return hash;
    }

    async register(userData) {
        const { email, password, name, age, injury_type, baseline_rom } = userData;

        // Check if user already exists
        const existingUser = await DatabaseService.queryOne(
            'SELECT user_id FROM users WHERE email = ?',
            [email]
        );

        if (existingUser) {
            throw new Error('Email already registered');
        }

        // Generate anonymous ID
        const userCount = await DatabaseService.queryOne('SELECT COUNT(*) as count FROM users');
        const anonymous_id = `P${String(userCount.count + 1).padStart(3, '0')}`;

        const user_id = uuidv4();
        const password_hash = await this.hashPassword(password);
        const timestamp = new Date().toISOString();

        await DatabaseService.execute(
            `INSERT INTO users (
        user_id, anonymous_id, email, password_hash, name, 
        age, injury_type, baseline_rom, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
            [user_id, anonymous_id, email, password_hash, name, age, injury_type, baseline_rom, timestamp, timestamp]
        );

        const user = await this.getUserById(user_id);
        return user;
    }

    async login(email, password) {
        const password_hash = await this.hashPassword(password);

        const user = await DatabaseService.queryOne(
            'SELECT * FROM users WHERE email = ? AND password_hash = ?',
            [email, password_hash]
        );

        if (!user) {
            throw new Error('Invalid email or password');
        }

        return user;
    }

    async getUserById(user_id) {
        const user = await DatabaseService.queryOne(
            'SELECT user_id, anonymous_id, email, name, age, injury_type, baseline_rom, created_at FROM users WHERE user_id = ?',
            [user_id]
        );

        if (!user) {
            throw new Error('User not found');
        }

        return user;
    }

    async getUserByEmail(email) {
        const user = await DatabaseService.queryOne(
            'SELECT user_id, anonymous_id, email, name, age, injury_type, baseline_rom, created_at FROM users WHERE email = ?',
            [email]
        );

        return user;
    }

    async updateUser(user_id, updates) {
        const allowedFields = ['name', 'age', 'injury_type', 'baseline_rom'];
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
        values.push(user_id);

        await DatabaseService.execute(
            `UPDATE users SET ${fields.join(', ')} WHERE user_id = ?`,
            values
        );

        return await this.getUserById(user_id);
    }

    async deleteUser(user_id) {
        await DatabaseService.execute('DELETE FROM users WHERE user_id = ?', [user_id]);
        return { deleted: true };
    }
}

export default new UserService();