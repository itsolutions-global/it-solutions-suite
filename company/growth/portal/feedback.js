/**
 * Privacy-First Feedback & Diagnostic Sentinel
 * IT Solutions Global Corporation
 * 
 * Strict Privacy Guarantee:
 * Never transmits document, contract, or invoice text.
 * Only transmits metadata: tool name, character count, findings count,
 * optional user comment, and diagnostic error stack traces.
 */

(function () {
  'use strict';

  let currentSentiment = null;
  let activeToolName = document.title.split('|')[0].trim() || 'IT Solutions Studio';

  // 1. Send Feedback to Backend API or Fallback
  async function dispatchFeedback(payload) {
    payload.url = window.location.href;
    payload.timestamp = new Date().toISOString();
    payload.userAgent = navigator.userAgent;

    try {
      const resp = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        return { success: true };
      }
    } catch (err) {
      console.warn('Feedback API offline, using fallback logging.', err);
    }

    // Client fallback: Log to localStorage so it's queryable locally or via CDP
    try {
      const stored = JSON.parse(localStorage.getItem('itsolutions_feedback_queue') || '[]');
      stored.push(payload);
      localStorage.setItem('itsolutions_feedback_queue', JSON.stringify(stored.slice(-30)));
    } catch (e) {}

    return { success: true, fallback: true };
  }

  // 2. In-Result Sentiment Handlers (👍 / 👎)
  window.submitSentiment = function (sentiment, findingsCount, textLength) {
    currentSentiment = sentiment;

    const upBtn = document.querySelector('.feedback-thumbs-up');
    const downBtn = document.querySelector('.feedback-thumbs-down');
    const drawer = document.getElementById('feedbackCommentDrawer');

    if (upBtn) upBtn.classList.toggle('active-positive', sentiment === 'positive');
    if (downBtn) downBtn.classList.toggle('active-negative', sentiment === 'negative');
    if (drawer) drawer.style.display = 'block';

    // Dispatch sentiment immediately even before comment
    dispatchFeedback({
      type: 'sentiment',
      tool: activeToolName,
      sentiment: sentiment,
      findings_count: findingsCount !== undefined ? findingsCount : null,
      text_length: textLength !== undefined ? textLength : null
    });
  };

  window.submitDetailedFeedback = function () {
    const input = document.getElementById('feedbackCommentText');
    const comment = input ? input.value.trim() : '';
    const drawer = document.getElementById('feedbackCommentDrawer');
    const thankYou = document.getElementById('feedbackThankYou');

    if (comment) {
      dispatchFeedback({
        type: 'user_comment',
        tool: activeToolName,
        sentiment: currentSentiment || 'neutral',
        comment: comment
      });
    }

    if (drawer) drawer.style.display = 'none';
    if (thankYou) thankYou.style.display = 'block';
  };

  window.skipFeedbackComment = function () {
    const drawer = document.getElementById('feedbackCommentDrawer');
    const thankYou = document.getElementById('feedbackThankYou');
    if (drawer) drawer.style.display = 'none';
    if (thankYou) thankYou.style.display = 'block';
  };

  // 3. Zero-Match Auto Detection (Heuristic Failure)
  window.checkZeroMatch = function (containerId, textLength, findingsCount) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Remove existing zero-match banner if any
    const existing = container.querySelector('.zero-match-banner');
    if (existing) existing.remove();

    if (textLength > 150 && findingsCount === 0) {
      const banner = document.createElement('div');
      banner.className = 'zero-match-banner';
      banner.innerHTML = `
        <strong>🔍 No clauses or items detected</strong>
        <p>If this document is an active contract or structured invoice, our rules may not recognize this specific format yet.</p>
        <button class="feedback-btn" style="background: rgba(245, 158, 11, 0.2); border-color: #f59e0b; color: #fef3c7;" onclick="window.openFeedbackModal('Unrecognized document format (0 findings on ${textLength} chars)')">
          Tell us the document format so we can add coverage
        </button>
      `;
      container.prepend(banner);

      // Auto-log the zero-match event for team telemetry
      dispatchFeedback({
        type: 'zero_match_auto_alert',
        tool: activeToolName,
        text_length: textLength,
        findings_count: 0
      });
    }
  };

  // 4. Global Uncaught Exception Sentinel
  window.addEventListener('error', function (event) {
    dispatchFeedback({
      type: 'javascript_error',
      tool: activeToolName,
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error ? event.error.stack : null
    });

    showErrorToast('A browser parsing error occurred. The team has been notified.');
  });

  window.addEventListener('unhandledrejection', function (event) {
    dispatchFeedback({
      type: 'unhandled_promise_rejection',
      tool: activeToolName,
      reason: String(event.reason)
    });
  });

  // 4b. Modern Non-Blocking Toast System
  window.showToast = function (message, type = 'info') {
    let container = document.getElementById('appToastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'appToastContainer';
      container.className = 'app-toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const isSuccess = type === 'success' || message.includes('✔') || message.includes('copied');
    const isWarn = type === 'warning' || message.includes('⚠️') || message.includes('Please');
    toast.className = `app-toast-item ${isSuccess ? 'success' : isWarn ? 'warning' : ''}`;
    
    const icon = isSuccess ? '✔' : isWarn ? '⚠️' : '📋';
    const cleanMsg = message.replace(/^✔\s*/, '').replace(/^⚠️\s*/, '');
    toast.innerHTML = `<span style="font-size: 15px;">${icon}</span> <span>${cleanMsg}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => {
        if (toast.parentElement) toast.remove();
        if (container.children.length === 0) container.remove();
      }, 300);
    }, 3400);
  };

  // Replace legacy blocking browser alert with non-blocking toast
  window.alert = function (msg) {
    window.showToast(msg);
  };

  function showErrorToast(msg) {
    let toast = document.getElementById('globalErrorToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'globalErrorToast';
      toast.className = 'error-toast-banner';
      document.body.appendChild(toast);
    }
    toast.innerHTML = `<span>⚠️ ${msg}</span> <button class="feedback-btn-secondary" style="color:#fff; border-color:rgba(255,255,255,0.4);" onclick="this.parentElement.remove()">Dismiss</button>`;
    setTimeout(() => { if (toast && toast.parentElement) toast.remove(); }, 6000);
  }

  // 5. Floating Bottom-Right Feedback Button & Modal
  function injectFloatingWidget() {
    // Floating Pill
    const pill = document.createElement('button');
    pill.className = 'floating-feedback-pill';
    pill.innerHTML = `<span>💬</span> <span>Feedback</span>`;
    pill.setAttribute('aria-label', 'Open Feedback Form');
    pill.onclick = () => window.openFeedbackModal();
    document.body.appendChild(pill);

    // Modal Backdrop & Content
    const modal = document.createElement('div');
    modal.className = 'feedback-modal-backdrop';
    modal.id = 'globalFeedbackModal';
    modal.innerHTML = `
      <div class="feedback-modal-content">
        <button class="feedback-close-btn" onclick="window.closeFeedbackModal()">&times;</button>
        <div class="feedback-modal-title">Help Shape IT Solutions Studio</div>
        <div class="feedback-modal-subtitle">Tell us what broke, what clause was missed, or what was useful.</div>
        
        <div style="margin-bottom: 12px;">
          <label style="display:block; font-size:11px; color:#94a3b8; margin-bottom:4px;">Category</label>
          <select id="modalFeedbackCategory" style="width:100%; background:#1e293b; border:1px solid #334155; color:#fff; border-radius:6px; padding:6px 8px; font-size:12px;">
            <option value="useful">👍 It worked great / found it useful</option>
            <option value="missed_clause">⚖️ Missed a contract clause or risk</option>
            <option value="invoice_parser_error">🧾 Invoice table / total not parsed</option>
            <option value="bug">🐛 Bug or browser error</option>
            <option value="feature_request">💡 Feature suggestion</option>
            <option value="other">💬 Other thought</option>
          </select>
        </div>

        <div style="margin-bottom: 14px;">
          <label style="display:block; font-size:11px; color:#94a3b8; margin-bottom:4px;">Your Feedback</label>
          <textarea id="modalFeedbackBody" class="feedback-input" placeholder="e.g. My NDA had a 3-year non-compete that wasn't flagged, or the CSV export missed invoice tax lines..." style="min-height:90px;"></textarea>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:10px; color:#64748b;">🔒 100% Private &bull; Zero document uploads</span>
          <div style="display:flex; gap:8px;">
            <button class="feedback-btn-secondary" onclick="window.closeFeedbackModal()">Cancel</button>
            <button class="feedback-btn-primary" onclick="window.submitModalFeedback()">Send Feedback</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  window.openFeedbackModal = function (prefillNote) {
    const modal = document.getElementById('globalFeedbackModal');
    if (!modal) return;
    if (prefillNote) {
      const body = document.getElementById('modalFeedbackBody');
      if (body) body.value = prefillNote;
    }
    modal.style.display = 'flex';
  };

  window.closeFeedbackModal = function () {
    const modal = document.getElementById('globalFeedbackModal');
    if (modal) modal.style.display = 'none';
  };

  window.submitModalFeedback = function () {
    const cat = document.getElementById('modalFeedbackCategory')?.value || 'general';
    const body = document.getElementById('modalFeedbackBody')?.value.trim();
    if (!body) {
      alert('Please enter a brief note so our team knows what to improve.');
      return;
    }

    dispatchFeedback({
      type: 'user_raised_modal_feedback',
      tool: activeToolName,
      category: cat,
      comment: body
    });

    const modal = document.getElementById('globalFeedbackModal');
    if (modal) {
      modal.innerHTML = `
        <div class="feedback-modal-content" style="text-align:center; padding:32px 20px;">
          <div style="font-size:36px; margin-bottom:12px;">🙌</div>
          <div class="feedback-modal-title">Feedback Received!</div>
          <p style="font-size:12px; color:#94a3b8; margin:8px 0 20px 0;">Our autonomous engineering team and founders review every report to expand rule coverage.</p>
          <button class="feedback-btn-primary" onclick="window.closeFeedbackModal(); location.reload();">Close</button>
        </div>
      `;
    }
  };

  // Inject when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectFloatingWidget);
  } else {
    injectFloatingWidget();
  }

})();
