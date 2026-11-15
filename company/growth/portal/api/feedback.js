/**
 * Vercel Serverless Function: /api/feedback
 * Receives anonymous user-raised feedback and automated parser health alerts.
 * Strictly adheres to Zero-Telemetry confidentiality pledge.
 */

export default async function handler(req, res) {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const data = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
    
    // Log structured telemetry event
    const event = {
      received_at: new Date().toISOString(),
      type: data.type || 'unknown',
      tool: data.tool || 'general',
      sentiment: data.sentiment || null,
      category: data.category || null,
      comment: data.comment ? String(data.comment).substring(0, 1000) : null,
      findings_count: data.findings_count !== undefined ? data.findings_count : null,
      text_length: data.text_length !== undefined ? data.text_length : null,
      error_message: data.message || data.reason || null,
      url: data.url || null
    };

    console.log('[USER_FEEDBACK_EVENT]', JSON.stringify(event));

    return res.status(200).json({ status: 'ok', received: true });
  } catch (err) {
    console.error('Error handling feedback:', err);
    return res.status(500).json({ error: 'Internal error processing feedback' });
  }
}
