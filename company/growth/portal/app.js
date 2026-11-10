/**
 * IT Solutions Global - Production Portal Application Engine
 * Pure Vanilla JavaScript • Zero External Dependencies • Sub-16ms Execution
 */

(function () {
  'use strict';

  // 1. Multi-Platform Install Commands
  const installCommands = {
    pip: "pip install it-solutions-suite",
    ps: "irm https://it-solutions-global.vercel.app/install.ps1 | iex",
    sh: "curl -fsSL https://it-solutions-global.vercel.app/install.sh | bash",
    docker: "docker run -d -p 8080:8080 itsolutionsglobal/corepulse:latest",
    git: "git clone https://github.com/itsolutions-global/it-solutions-suite.git"
  };

  let currentCliPlatform = 'pip';

  window.setCliPlatform = function (platform) {
    currentCliPlatform = platform;
    document.querySelectorAll('.tab-btn-cli').forEach(tab => {
      tab.classList.toggle('active', tab.getAttribute('data-cli') === platform);
    });
    const cmdEl = document.getElementById('cliCommandText');
    if (cmdEl) {
      cmdEl.textContent = installCommands[platform];
    }
    resetCopyBtn();
  };

  window.copyCliCommand = function () {
    const textToCopy = installCommands[currentCliPlatform];
    navigator.clipboard.writeText(textToCopy).then(() => {
      const copyBtn = document.getElementById('copyCliBtn');
      const copyBtnText = document.getElementById('copyCliBtnText');
      if (copyBtn && copyBtnText) {
        copyBtn.classList.add('copied');
        copyBtnText.textContent = "Copied to Clipboard!";
        setTimeout(resetCopyBtn, 2500);
      }
    }).catch(err => {
      console.error('Clipboard copy failed: ', err);
    });
  };

  function resetCopyBtn() {
    const copyBtn = document.getElementById('copyCliBtn');
    const copyBtnText = document.getElementById('copyCliBtnText');
    if (copyBtn && copyBtnText) {
      copyBtn.classList.remove('copied');
      copyBtnText.textContent = "Copy Command";
    }
  }

  // 2. Product Showcase Tab Switcher
  window.switchProductTab = function (pillar) {
    const tabs = ['action', 'defense', 'perception', 'federation'];
    tabs.forEach(t => {
      const card = document.getElementById(`tab-${t}`);
      const panel = document.getElementById(`panel-${t}`);
      if (t === pillar) {
        if (card) {
          card.classList.add('active');
          if (t === 'defense') card.classList.add('defense');
          if (t === 'perception') card.classList.add('perception');
          if (t === 'federation') card.classList.add('federation');
        }
        if (panel) panel.classList.add('active');
      } else {
        if (card) card.classList.remove('active', 'defense', 'perception', 'federation');
        if (panel) panel.classList.remove('active');
      }
    });
  };

  // 4. Animated Metric Counter Engine
  function animateValue(id, start, end, duration, suffix = '') {
    const el = document.getElementById(id);
    if (!el) return;
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const val = Math.floor(progress * (end - start) + start);
      el.textContent = val + suffix;
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        el.textContent = end + suffix;
      }
    };
    window.requestAnimationFrame(step);
  }

  // 5. Initialize on DOM Load
  document.addEventListener('DOMContentLoaded', () => {
    // Run live counter animation
    setTimeout(() => {
      animateValue('metricTests', 0, 175, 1200, '/175');
      animateValue('metricDeps', 10, 0, 800, '');
      animateValue('metricLatency', 60, 15, 1000, 'ms');
      animateValue('metricLocal', 0, 100, 1200, '%');
    }, 200);

    // Initial CLI display
    window.setCliPlatform('pip');
  });

})();
