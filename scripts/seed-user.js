// Seed a default demo user into MongoDB for LibreChat
// Run with: node seed-user.js
// Requires MONGO_URI env var

const crypto = require('crypto');

const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/librechat';
const DEMO_EMAIL = 'demo@example.com';
const DEMO_PASSWORD = 'demodemo123';
const DEMO_NAME = 'Demo User';
const DEMO_USERNAME = 'demo';

async function seedUser() {
  const { MongoClient } = require('mongodb');
  const bcrypt = require('bcryptjs');

  const client = new MongoClient(MONGO_URI);
  try {
    await client.connect();
    const db = client.db();
    const users = db.collection('users');

    const existing = await users.findOne({ email: DEMO_EMAIL });
    if (existing) {
      console.log('Demo user already exists, skipping seed.');
      return;
    }

    const salt = await bcrypt.genSalt(10);
    const hash = await bcrypt.hash(DEMO_PASSWORD, salt);

    await users.insertOne({
      name: DEMO_NAME,
      username: DEMO_USERNAME,
      email: DEMO_EMAIL,
      password: hash,
      avatar: null,
      role: 'USER',
      provider: 'local',
      emailVerified: true,
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    console.log(`Demo user seeded: ${DEMO_EMAIL} / ${DEMO_PASSWORD}`);
  } finally {
    await client.close();
  }
}

seedUser().catch(console.error);
