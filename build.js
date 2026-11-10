/**
 * TamilVoice Kirana AI - Vercel / Production Build Script
 * Injects BACKEND_URL into frontend/js/env.js at build time without exposing secrets.
 */
const fs = require('fs');
const path = require('path');

const envFilePath = path.join(__dirname, 'frontend', 'js', 'env.js');

let backendUrl = process.env.BACKEND_URL || process.env.API_BASE_URL || '';
backendUrl = backendUrl.trim().replace(/\/+$/, '');

if (backendUrl && !backendUrl.endsWith('/api') && !backendUrl.includes('/api/')) {
  backendUrl = `${backendUrl}/api`;
}

const fileContent = `/**
 * TamilVoice Kirana AI - Runtime Environment Config
 * Automatically injected by build.js during deployment.
 * Local development defaults to http://127.0.0.1:8000/api when blank.
 */
window.__API_BASE_URL__ = "${backendUrl}";
`;

fs.writeFileSync(envFilePath, fileContent, 'utf-8');
console.log(`[build.js] Generated frontend/js/env.js with BACKEND_URL: ${backendUrl ? backendUrl : '(empty - auto-detect)'}`);
