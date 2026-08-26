/**
 * AURA Commerce - Lightweight WhatsApp Service (Baileys Engine)
 * Pure WebSocket implementation (Zero Chromium, <35MB RAM).
 * Persists session state to MongoDB `whatsapp_sessions` collection.
 */

require('dotenv').config();
const express = require('express');
const { MongoClient } = require('mongodb');
const pino = require('pino');
const qrcodeTerminal = require('qrcode-terminal');
const {
  default: makeWASocket,
  DisconnectReason,
  fetchLatestBaileysVersion,
  proto,
  initAuthCreds,
  BufferJSON
} = require('@whiskeysockets/baileys');

const PORT = parseInt(process.env.WHATSAPP_BAILEYS_PORT || '5001', 10);
const HOST = '127.0.0.1'; // Strictly internal loopback - never exposed publicly
const MONGO_URI = process.env.MONGODB_URI || (
  process.env.MONGODB_PASSWORD
    ? `mongodb+srv://chaitanyavedansh_db_user:${encodeURIComponent(process.env.MONGODB_PASSWORD)}@cluster0.gdjxqnz.mongodb.net/?appName=Cluster0`
    : ''
);
const DB_NAME = process.env.MONGODB_DB_NAME || 'ecommerce_catalog';
const SESSION_COLLECTION = process.env.WHATSAPP_SESSION_COLLECTION || 'whatsapp_sessions';
const SESSION_ID = process.env.WHATSAPP_SESSION_ID || 'default_session';

const logger = pino({ level: process.env.LOG_LEVEL || 'warn' });

let sock = null;
let currentQR = null;
let isAuthenticated = false;
let isConnected = false;
let myJid = null;
let mongoClient = null;
let sessionsColl = null;

// =====================================================================
// Custom MongoDB Authentication State Store for Baileys
// =====================================================================

async function useMongoAuthState(collection, sessionId) {
  // Read creds
  const credsDoc = await collection.findOne({ session_id: sessionId, key: 'creds' });
  let creds;
  if (credsDoc && credsDoc.data) {
    try {
      creds = JSON.parse(credsDoc.data, BufferJSON.reviver);
    } catch (e) {
      creds = initAuthCreds();
    }
  } else {
    creds = initAuthCreds();
  }

  return {
    state: {
      creds,
      keys: {
        get: async (type, ids) => {
          const data = {};
          for (const id of ids) {
            const key = `${type}-${id}`;
            const doc = await collection.findOne({ session_id: sessionId, key });
            if (doc && doc.data) {
              try {
                let value = JSON.parse(doc.data, BufferJSON.reviver);
                if (type === 'app-state-sync-key' && value) {
                  value = proto.Message.AppStateSyncKeyData.fromObject(value);
                }
                data[id] = value;
              } catch (err) {}
            }
          }
          return data;
        },
        set: async (data) => {
          const operations = [];
          for (const category in data) {
            for (const id in data[category]) {
              const value = data[category][id];
              const key = `${category}-${id}`;
              if (value) {
                operations.push({
                  updateOne: {
                    filter: { session_id: sessionId, key },
                    update: {
                      $set: {
                        session_id: sessionId,
                        key,
                        data: JSON.stringify(value, BufferJSON.replacer),
                        updated_at: new Date()
                      }
                    },
                    upsert: true
                  }
                });
              } else {
                operations.push({
                  deleteOne: {
                    filter: { session_id: sessionId, key }
                  }
                });
              }
            }
          }
          if (operations.length > 0) {
            await collection.bulkWrite(operations, { ordered: false }).catch(() => {});
          }
        }
      }
    },
    saveCreds: async () => {
      await collection.updateOne(
        { session_id: sessionId, key: 'creds' },
        {
          $set: {
            session_id: sessionId,
            key: 'creds',
            data: JSON.stringify(creds, BufferJSON.replacer),
            updated_at: new Date()
          }
        },
        { upsert: true }
      );
    }
  };
}

// =====================================================================
// Baileys WhatsApp Socket Initialization
// =====================================================================

async function initBaileysSocket() {
  try {
    if (!sessionsColl) {
      if (!MONGO_URI) {
        logger.warn('No MongoDB URI found. Running Baileys in ephemeral memory mode.');
      } else {
        mongoClient = new MongoClient(MONGO_URI);
        await mongoClient.connect();
        const db = mongoClient.db(DB_NAME);
        sessionsColl = db.collection(SESSION_COLLECTION);
        await sessionsColl.createIndex({ session_id: 1, key: 1 }, { unique: true }).catch(() => {});
      }
    }

    let authState;
    if (sessionsColl) {
      authState = await useMongoAuthState(sessionsColl, SESSION_ID);
    } else {
      authState = { state: { creds: initAuthCreds(), keys: { get: () => ({}), set: () => {} } }, saveCreds: () => {} };
    }

    const { version } = await fetchLatestBaileysVersion().catch(() => ({ version: [2, 3000, 1015901307] }));

    sock = makeWASocket({
      version,
      logger,
      printQRInTerminal: false, // We render manually with qrcode-terminal
      auth: authState.state,
      browser: ['AURA Luxury Concierge', 'Chrome', '1.0.0'],
      syncFullHistory: false,
      generateHighQualityLinkPreview: false,
      markOnlineOnConnect: false
    });

    sock.ev.on('creds.update', authState.saveCreds);

    sock.ev.on('connection.update', (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        currentQR = qr;
        isAuthenticated = false;
        isConnected = false;
        console.log('\n========================================================');
        console.log('  SCAN WHATSAPP QR CODE TO LINK AURA CONCIERGE');
        console.log('========================================================');
        qrcodeTerminal.generate(qr, { small: true });
        console.log('========================================================\n');
      }

      if (connection === 'close') {
        isConnected = false;
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
        console.log(`WhatsApp connection closed (Status ${statusCode}). Reconnecting: ${shouldReconnect}`);

        if (statusCode === DisconnectReason.loggedOut) {
          isAuthenticated = false;
          currentQR = null;
          if (sessionsColl) {
            sessionsColl.deleteMany({ session_id: SESSION_ID }).catch(() => {});
          }
        }

        if (shouldReconnect) {
          setTimeout(initBaileysSocket, 5000);
        }
      } else if (connection === 'open') {
        isConnected = true;
        isAuthenticated = true;
        currentQR = null;
        myJid = sock.user?.id || '';
        console.log(`✓ WhatsApp Baileys Engine connected successfully! User: ${myJid}`);
      }
    });

  } catch (err) {
    console.error('Notice on initializing Baileys WhatsApp socket:', err.message);
    setTimeout(initBaileysSocket, 10000);
  }
}

// =====================================================================
// Internal Express IPC Server (Bound to 127.0.0.1 only)
// =====================================================================

const app = express();
app.use(express.json());

// Send message endpoint
app.post('/send', async (req, res) => {
  const { phone, message } = req.body;

  if (!phone || !message) {
    return res.status(400).json({ success: false, error: 'Phone and message are required.' });
  }

  // Dry run / simulation mode
  if (process.env.WHATSAPP_DRY_RUN === 'true') {
    return res.json({
      success: true,
      simulated: true,
      messageId: `SIM_${Date.now()}`,
      phone: phone.substring(0, 5) + '****'
    });
  }

  if (!sock || !isConnected) {
    return res.status(503).json({
      success: false,
      error: 'WhatsApp Baileys socket is not connected or QR code not yet linked.',
      authenticated: isAuthenticated,
      connected: isConnected,
      hasQr: !!currentQR
    });
  }

  try {
    // Format phone to WhatsApp JID: +919876543210 -> 919876543210@s.whatsapp.net
    const cleanDigits = phone.replace(/\D/g, '');
    const jid = `${cleanDigits}@s.whatsapp.net`;

    const sent = await sock.sendMessage(jid, { text: message.trim() });
    
    return res.json({
      success: true,
      messageId: sent.key.id,
      timestamp: sent.messageTimestamp,
      recipient: cleanDigits.substring(0, 4) + '****' + cleanDigits.slice(-4)
    });
  } catch (err) {
    return res.status(500).json({
      success: false,
      error: err.message || 'Failed to send WhatsApp message.'
    });
  }
});

// Status endpoint
app.get('/status', (req, res) => {
  res.json({
    connected: isConnected,
    authenticated: isAuthenticated,
    hasQr: !!currentQR,
    phone: myJid ? myJid.split(':')[0] : null,
    engine: 'baileys',
    dryRun: process.env.WHATSAPP_DRY_RUN === 'true'
  });
});

// QR endpoint (Internal)
app.get('/qr', (req, res) => {
  if (isAuthenticated) {
    return res.json({ authenticated: true, qr: null, message: 'WhatsApp already connected.' });
  }
  res.json({ authenticated: false, qr: currentQR });
});

// Start service
app.listen(PORT, HOST, () => {
  console.log(`AURA WhatsApp Baileys Service listening internally on http://${HOST}:${PORT}`);
  initBaileysSocket();
});
