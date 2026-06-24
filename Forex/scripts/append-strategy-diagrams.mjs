#!/usr/bin/env node
/**
 * Append new strategy diagram entries to strategyDiagrams.js (ASCII-safe labels).
 */
import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const target = join(root, 'src/content/strategyDiagrams.js');

/** @param {string[]} lines */
function pack(lines) {
  return lines.join('\\n');
}

const insideBarLong = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Inside Bar Breakout &mdash; LONG</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">Trend tang &rarr; nen me + inside bar &rarr; break len</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<path d="M35,290 C90,275 150,250 210,220 270,195 330,175" fill="none" stroke="#a855f7" stroke-width="2.5" stroke-dasharray="6 4"/>',
  '<text x="334" y="172" fill="#c4b5fd" font-size="9">EMA50</text>',
  '  <line x1="55" y1="248" x2="55" y2="272" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="255" width="14" height="12" fill="#22c55e"/>',
  '  <line x1="88" y1="235" x2="88" y2="260" stroke="#8b9cb3" stroke-width="2"/><rect x="81" y="240" width="14" height="14" fill="#22c55e"/>',
  '  <line x1="121" y1="222" x2="121" y2="248" stroke="#8b9cb3" stroke-width="2"/><rect x="114" y="228" width="14" height="14" fill="#22c55e"/>',
  '  <line x1="154" y1="210" x2="154" y2="238" stroke="#8b9cb3" stroke-width="2"/><rect x="147" y="216" width="14" height="16" fill="#22c55e"/>',
  '  <line x1="187" y1="198" x2="187" y2="228" stroke="#8b9cb3" stroke-width="2"/><rect x="180" y="205" width="14" height="17" fill="#22c55e"/>',
  '  <line x1="220" y1="155" x2="220" y2="210" stroke="#8b9cb3" stroke-width="2"/><rect x="213" y="168" width="14" height="38" fill="#22c55e"/>',
  '<rect x="205" y="155" width="30" height="58" fill="rgba(245,158,11,0.08)" stroke="#f59e0b" stroke-dasharray="4 3" rx="3"/>',
  '<text x="248" y="168" fill="#fbbf24" font-size="10" font-weight="600">Nen me</text>',
  '  <line x1="253" y1="178" x2="253" y2="198" stroke="#8b9cb3" stroke-width="2"/><rect x="246" y="182" width="14" height="12" fill="#94a3b8"/>',
  '<rect x="238" y="178" width="30" height="22" fill="rgba(148,163,184,0.1)" stroke="#94a3b8" stroke-dasharray="3 3" rx="2"/>',
  '<text x="248" y="212" fill="#94a3b8" font-size="9">Inside bar</text>',
  '  <line x1="286" y1="145" x2="286" y2="175" stroke="#8b9cb3" stroke-width="2"/><rect x="279" y="152" width="14" height="18" fill="#22c55e"/>',
  '<line x1="28" y1="155" x2="372" y2="155" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="148" fill="#f59e0b" font-size="10" font-weight="600">Mother high</text>',
  '<line x1="28" y1="210" x2="240" y2="210" stroke="#f59e0b" stroke-width="1" stroke-dasharray="5 4" opacity="0.7"/>',
  '<text x="32" y="218" fill="#f59e0b" font-size="10">Mother low</text>',
  '<rect x="268" y="72" width="110" height="36" rx="4" fill="rgba(34,197,94,0.25)" stroke="#22c55e" stroke-width="2"/>',
  '<text x="323" y="88" text-anchor="middle" fill="#bbf7d0" font-size="10" font-weight="700">TIN HIEU</text>',
  '<text x="323" y="100" text-anchor="middle" fill="#94a3b8" font-size="9">Close &gt; mother high + EMA</text>',
  '<line x1="250" y1="168" x2="360" y2="168" stroke="#3b82f6" stroke-width="2"/><text x="362" y="172" fill="#3b82f6" font-size="10">Entry</text>',
  '<line x1="250" y1="212" x2="360" y2="212" stroke="#ef4444" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="216" fill="#ef4444" font-size="10">SL</text>',
  '<line x1="250" y1="125" x2="360" y2="125" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="129" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Cach doc</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- Nen me du rong (motherMinRangePips)</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Nen ke la inside bar (nen trong nen me)</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- Close pha mother high, gia tren EMA &rarr; LONG</text>',
  '<text x="24" y="506" fill="#94a3b8" font-size="11">- SL duoi mother low | TP = entry + RR x risk</text>',
  '<text x="24" y="530" fill="#64748b" font-size="10">SHORT: doi xung break mother low duoi EMA</text>',
  '</svg>',
]);

const insideBarShort = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Inside Bar Breakout &mdash; SHORT</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">Trend giam &rarr; nen me + inside bar &rarr; break xuong</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<path d="M35,175 C90,190 150,215 210,240 270,265 330,285" fill="none" stroke="#a855f7" stroke-width="2.5" stroke-dasharray="6 4"/>',
  '  <line x1="55" y1="195" x2="55" y2="220" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="200" width="14" height="14" fill="#ef4444"/>',
  '  <line x1="88" y1="208" x2="88" y2="232" stroke="#8b9cb3" stroke-width="2"/><rect x="81" y="214" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="121" y1="218" x2="121" y2="242" stroke="#8b9cb3" stroke-width="2"/><rect x="114" y="224" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="154" y1="228" x2="154" y2="252" stroke="#8b9cb3" stroke-width="2"/><rect x="147" y="234" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="187" y1="238" x2="187" y2="262" stroke="#8b9cb3" stroke-width="2"/><rect x="180" y="244" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="220" y1="248" x2="220" y2="305" stroke="#8b9cb3" stroke-width="2"/><rect x="213" y="262" width="14" height="38" fill="#ef4444"/>',
  '<rect x="205" y="248" width="30" height="58" fill="rgba(245,158,11,0.08)" stroke="#f59e0b" stroke-dasharray="4 3" rx="3"/>',
  '  <line x1="253" y1="268" x2="253" y2="288" stroke="#8b9cb3" stroke-width="2"/><rect x="246" y="272" width="14" height="12" fill="#94a3b8"/>',
  '<rect x="238" y="268" width="30" height="22" fill="rgba(148,163,184,0.1)" stroke="#94a3b8" stroke-dasharray="3 3" rx="2"/>',
  '  <line x1="286" y1="305" x2="286" y2="335" stroke="#8b9cb3" stroke-width="2"/><rect x="279" y="312" width="14" height="18" fill="#ef4444"/>',
  '<line x1="28" y1="305" x2="372" y2="305" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="298" fill="#f59e0b" font-size="10" font-weight="600">Mother low</text>',
  '<rect x="268" y="72" width="110" height="36" rx="4" fill="rgba(239,68,68,0.2)" stroke="#ef4444" stroke-width="2"/>',
  '<text x="323" y="88" text-anchor="middle" fill="#fecaca" font-size="10" font-weight="700">TIN HIEU</text>',
  '<line x1="250" y1="318" x2="360" y2="318" stroke="#ef4444" stroke-width="2"/><text x="362" y="322" fill="#ef4444" font-size="10">Entry</text>',
  '<line x1="250" y1="248" x2="360" y2="248" stroke="#f87171" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="252" fill="#f87171" font-size="10">SL</text>',
  '<line x1="250" y1="355" x2="360" y2="355" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="359" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Cach doc</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- Close duoi EMA trend</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Inside bar trong nen me</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- Close pha mother low &rarr; SHORT tai close</text>',
  '</svg>',
]);

const pinShort = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Pin Bar Rejection &mdash; SHORT</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">Cham swing high &rarr; pin bar rau tren &rarr; SHORT</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<line x1="28" y1="155" x2="372" y2="155" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="148" fill="#f59e0b" font-size="10" font-weight="600">Swing High</text>',
  '  <line x1="55" y1="168" x2="55" y2="192" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="175" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="88" y1="165" x2="88" y2="188" stroke="#8b9cb3" stroke-width="2"/><rect x="81" y="170" width="14" height="12" fill="#ef4444"/>',
  '  <line x1="121" y1="168" x2="121" y2="190" stroke="#8b9cb3" stroke-width="2"/><rect x="114" y="172" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="154" y1="162" x2="154" y2="185" stroke="#8b9cb3" stroke-width="2"/><rect x="147" y="168" width="14" height="12" fill="#ef4444"/>',
  '  <line x1="187" y1="165" x2="187" y2="188" stroke="#8b9cb3" stroke-width="2"/><rect x="180" y="170" width="14" height="13" fill="#22c55e"/>',
  '<line x1="215" y1="118" x2="215" y2="188" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="208" y="158" width="14" height="28" fill="#ef4444"/>',
  '<rect x="200" y="118" width="30" height="42" fill="rgba(239,68,68,0.12)" stroke="#ef4444" stroke-dasharray="3 3" rx="3"/>',
  '<text x="248" y="130" fill="#fca5a5" font-size="10">Rau tren dai (pin)</text>',
  '<text x="248" y="146" fill="#94a3b8" font-size="9">Cham vung swing &mdash; khong can quet</text>',
  '  <line x1="258" y1="172" x2="258" y2="195" stroke="#8b9cb3" stroke-width="2"/><rect x="251" y="178" width="14" height="12" fill="#ef4444"/>',
  '  <line x1="291" y1="185" x2="291" y2="208" stroke="#8b9cb3" stroke-width="2"/><rect x="284" y="190" width="14" height="13" fill="#ef4444"/>',
  '<rect x="188" y="72" width="120" height="36" rx="4" fill="rgba(239,68,68,0.2)" stroke="#ef4444" stroke-width="2"/>',
  '<text x="248" y="88" text-anchor="middle" fill="#fecaca" font-size="10" font-weight="700">TIN HIEU SHORT</text>',
  '<line x1="200" y1="186" x2="360" y2="186" stroke="#ef4444" stroke-width="2"/><text x="362" y="190" fill="#ef4444" font-size="10">Entry</text>',
  '<line x1="200" y1="118" x2="360" y2="118" stroke="#f87171" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="122" fill="#f87171" font-size="10">SL</text>',
  '<line x1="200" y1="235" x2="360" y2="235" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="239" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Khac Liquidity Grab</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- Chi can cham swing zone (khong grabPips)</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Wick lon + than nho + nen giam xac nhan</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- Entry ngay tai close pin bar</text>',
  '</svg>',
]);

const pinLong = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Pin Bar Rejection &mdash; LONG</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">Cham swing low &rarr; pin bar rau duoi &rarr; LONG</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<line x1="28" y1="245" x2="372" y2="245" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="238" fill="#f59e0b" font-size="10" font-weight="600">Swing Low</text>',
  '  <line x1="55" y1="198" x2="55" y2="222" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="203" width="14" height="14" fill="#ef4444"/>',
  '  <line x1="88" y1="200" x2="88" y2="225" stroke="#8b9cb3" stroke-width="2"/><rect x="81" y="205" width="14" height="15" fill="#22c55e"/>',
  '  <line x1="121" y1="202" x2="121" y2="226" stroke="#8b9cb3" stroke-width="2"/><rect x="114" y="207" width="14" height="14" fill="#ef4444"/>',
  '  <line x1="154" y1="205" x2="154" y2="228" stroke="#8b9cb3" stroke-width="2"/><rect x="147" y="210" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="187" y1="208" x2="187" y2="230" stroke="#8b9cb3" stroke-width="2"/><rect x="180" y="213" width="14" height="12" fill="#ef4444"/>',
  '<line x1="220" y1="268" x2="220" y2="185" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="208" y="228" width="14" height="26" fill="#22c55e"/>',
  '<rect x="200" y="255" width="30" height="45" fill="rgba(34,197,94,0.12)" stroke="#22c55e" stroke-dasharray="3 3" rx="3"/>',
  '<text x="248" y="278" fill="#86efac" font-size="10">Rau duoi dai (hammer)</text>',
  '<text x="248" y="294" fill="#94a3b8" font-size="9">Cham vung ho tro &mdash; khong can quet</text>',
  '  <line x1="258" y1="198" x2="258" y2="222" stroke="#8b9cb3" stroke-width="2"/><rect x="251" y="203" width="14" height="14" fill="#22c55e"/>',
  '  <line x1="291" y1="185" x2="291" y2="208" stroke="#8b9cb3" stroke-width="2"/><rect x="284" y="190" width="14" height="13" fill="#22c55e"/>',
  '<rect x="188" y="72" width="110" height="36" rx="4" fill="rgba(34,197,94,0.2)" stroke="#22c55e" stroke-width="2"/>',
  '<text x="243" y="88" text-anchor="middle" fill="#bbf7d0" font-size="10" font-weight="700">TIN HIEU LONG</text>',
  '<line x1="200" y1="228" x2="360" y2="228" stroke="#22c55e" stroke-width="2"/><text x="362" y="232" fill="#22c55e" font-size="10">Entry</text>',
  '<line x1="200" y1="272" x2="360" y2="272" stroke="#ef4444" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="276" fill="#ef4444" font-size="10">SL</text>',
  '<line x1="200" y1="175" x2="360" y2="175" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="179" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Dieu kien LONG</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- Cham swing low zone + pin bar rejection</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Nen tang xac nhan tai close</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- SL duoi duoi pin | TP theo RR</text>',
  '</svg>',
]);

const newEntries = {
  'inside-bar-breakout-long': insideBarLong,
  'inside-bar-breakout-short': insideBarShort,
  'pin-bar-rejection-short': pinShort,
  'pin-bar-rejection-long': pinLong,
};

let src = readFileSync(target, 'utf8');
if (src.includes('inside-bar-breakout-long')) {
  console.log('Diagrams already present, skipping');
  process.exit(0);
}

const insert = Object.entries(newEntries)
  .map(([id, svg]) => `  '${id}': '${svg}',`)
  .join('\n');

src = src.replace(/',\n};\n\n\/\*\*/, `',\n${insert}\n};\n\n/**`);
writeFileSync(target, src);
console.log('Appended', Object.keys(newEntries).length, 'diagrams');
