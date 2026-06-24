#!/usr/bin/env node
/**
 * Append Wyckoff strategy diagrams to strategyDiagrams.js (ASCII-safe).
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

const springLong = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<defs>',
  '<marker id="wy-arr-g" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#22c55e"/></marker>',
  '</defs>',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Wyckoff Spring &mdash; LONG</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">Range tich luy &rarr; quet day &rarr; dong lai trong range</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<rect x="28" y="168" width="344" height="78" fill="rgba(148,163,184,0.06)" stroke="#64748b" stroke-dasharray="4 4" rx="4"/>',
  '<line x1="28" y1="168" x2="372" y2="168" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="162" fill="#f59e0b" font-size="10" font-weight="600">Range high</text>',
  '<line x1="28" y1="246" x2="372" y2="246" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="260" fill="#f59e0b" font-size="10" font-weight="600">Range low (ho tro)</text>',
  '  <line x1="55" y1="195" x2="55" y2="218" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="200" width="14" height="12" fill="#22c55e"/>',
  '  <line x1="82" y1="205" x2="82" y2="228" stroke="#8b9cb3" stroke-width="2"/><rect x="75" y="210" width="14" height="12" fill="#ef4444"/>',
  '  <line x1="109" y1="192" x2="109" y2="215" stroke="#8b9cb3" stroke-width="2"/><rect x="102" y="197" width="14" height="12" fill="#22c55e"/>',
  '  <line x1="136" y1="208" x2="136" y2="232" stroke="#8b9cb3" stroke-width="2"/><rect x="129" y="213" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="163" y1="198" x2="163" y2="222" stroke="#8b9cb3" stroke-width="2"/><rect x="156" y="203" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="190" y1="210" x2="190" y2="234" stroke="#8b9cb3" stroke-width="2"/><rect x="183" y="215" width="14" height="13" fill="#ef4444"/>',
  '<line x1="218" y1="268" x2="218" y2="188" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="211" y="228" width="14" height="28" fill="#22c55e"/>',
  '<rect x="203" y="255" width="30" height="48" fill="rgba(34,197,94,0.12)" stroke="#22c55e" stroke-dasharray="3 3" rx="3"/>',
  '<text x="248" y="278" fill="#86efac" font-size="10" font-weight="600">Spring (quet day)</text>',
  '<text x="248" y="292" fill="#94a3b8" font-size="9">Close TREN range low</text>',
  '  <line x1="252" y1="200" x2="252" y2="222" stroke="#8b9cb3" stroke-width="2"/><rect x="245" y="205" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="286" y1="185" x2="286" y2="208" stroke="#8b9cb3" stroke-width="2"/><rect x="279" y="190" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="320" y1="172" x2="320" y2="195" stroke="#8b9cb3" stroke-width="2"/><rect x="313" y="177" width="14" height="13" fill="#22c55e"/>',
  '<rect x="38" y="72" width="100" height="36" rx="4" fill="rgba(148,163,184,0.12)" stroke="#64748b"/>',
  '<text x="88" y="88" text-anchor="middle" fill="#cbd5e1" font-size="10" font-weight="600">1. Range</text>',
  '<text x="88" y="100" text-anchor="middle" fill="#94a3b8" font-size="9">Sideway trong bien</text>',
  '<rect x="168" y="72" width="100" height="36" rx="4" fill="rgba(34,197,94,0.25)" stroke="#22c55e" stroke-width="2"/>',
  '<text x="218" y="88" text-anchor="middle" fill="#bbf7d0" font-size="10" font-weight="700">2. TIN HIEU</text>',
  '<text x="218" y="100" text-anchor="middle" fill="#94a3b8" font-size="9">Spring + nen xanh</text>',
  '<path d="M218 182 L218 168" stroke="#22c55e" stroke-width="2" marker-end="url(#wy-arr-g)"/>',
  '<line x1="235" y1="238" x2="360" y2="238" stroke="#22c55e" stroke-width="2"/><text x="362" y="242" fill="#22c55e" font-size="10">Entry</text>',
  '<line x1="235" y1="272" x2="360" y2="272" stroke="#ef4444" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="276" fill="#ef4444" font-size="10">SL</text>',
  '<line x1="235" y1="175" x2="360" y2="175" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="179" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Cach doc</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- Range du cao (minRangePips) + close trong range</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Low quet duoi range low + sweepPips</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- Close quay lai TRONG range + rau duoi &rarr; LONG</text>',
  '<text x="24" y="512" fill="#f59e0b" font-size="11">! Khac Liquidity Grab: bat buoc co range truoc</text>',
  '<text x="24" y="534" fill="#64748b" font-size="10">UTAD SHORT: doi xung o range high</text>',
  '</svg>',
]);

const utadShort = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Wyckoff UTAD &mdash; SHORT</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">Range phan phoi &rarr; quet dinh &rarr; dong lai trong range</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<rect x="28" y="168" width="344" height="78" fill="rgba(148,163,184,0.06)" stroke="#64748b" stroke-dasharray="4 4" rx="4"/>',
  '<line x1="28" y1="168" x2="372" y2="168" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="162" fill="#f59e0b" font-size="10" font-weight="600">Range high (khang cu)</text>',
  '<line x1="28" y1="246" x2="372" y2="246" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<text x="32" y="260" fill="#f59e0b" font-size="10" font-weight="600">Range low</text>',
  '  <line x1="55" y1="210" x2="55" y2="234" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="215" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="82" y1="198" x2="82" y2="222" stroke="#8b9cb3" stroke-width="2"/><rect x="75" y="203" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="109" y1="212" x2="109" y2="236" stroke="#8b9cb3" stroke-width="2"/><rect x="102" y="217" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="136" y1="200" x2="136" y2="224" stroke="#8b9cb3" stroke-width="2"/><rect x="129" y="205" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="163" y1="215" x2="163" y2="238" stroke="#8b9cb3" stroke-width="2"/><rect x="156" y="220" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="190" y1="205" x2="190" y2="228" stroke="#8b9cb3" stroke-width="2"/><rect x="183" y="210" width="14" height="13" fill="#22c55e"/>',
  '<line x1="218" y1="118" x2="218" y2="200" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="211" y="158" width="14" height="30" fill="#ef4444"/>',
  '<rect x="203" y="118" width="30" height="45" fill="rgba(239,68,68,0.12)" stroke="#ef4444" stroke-dasharray="3 3" rx="3"/>',
  '<text x="248" y="130" fill="#fca5a5" font-size="10" font-weight="600">UTAD (quet dinh)</text>',
  '<text x="248" y="146" fill="#94a3b8" font-size="9">Close DUOI range high</text>',
  '  <line x1="252" y1="218" x2="252" y2="242" stroke="#8b9cb3" stroke-width="2"/><rect x="245" y="223" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="286" y1="232" x2="286" y2="258" stroke="#8b9cb3" stroke-width="2"/><rect x="279" y="237" width="14" height="15" fill="#ef4444"/>',
  '  <line x1="320" y1="248" x2="320" y2="272" stroke="#8b9cb3" stroke-width="2"/><rect x="313" y="253" width="14" height="14" fill="#ef4444"/>',
  '<rect x="168" y="72" width="110" height="36" rx="4" fill="rgba(239,68,68,0.2)" stroke="#ef4444" stroke-width="2"/>',
  '<text x="223" y="88" text-anchor="middle" fill="#fecaca" font-size="10" font-weight="700">TIN HIEU SHORT</text>',
  '<text x="223" y="100" text-anchor="middle" fill="#94a3b8" font-size="9">UTAD + nen do</text>',
  '<line x1="235" y1="188" x2="360" y2="188" stroke="#ef4444" stroke-width="2"/><text x="362" y="192" fill="#ef4444" font-size="10">Entry</text>',
  '<line x1="235" y1="118" x2="360" y2="118" stroke="#f87171" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="122" fill="#f87171" font-size="10">SL</text>',
  '<line x1="235" y1="255" x2="360" y2="255" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="259" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Dieu kien UTAD</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- High quet tren range high + sweepPips</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Close quay lai duoi range high</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- Rau tren lon + nen giam &rarr; SHORT tai close</text>',
  '<text x="24" y="512" fill="#f59e0b" font-size="11">! Vao lenh NGAY tai nen UTAD (khong cho test)</text>',
  '</svg>',
]);

const rangeTestLong = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<defs>',
  '<marker id="wy-rt-g" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#22c55e"/></marker>',
  '<marker id="wy-rt-b" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#3b82f6"/></marker>',
  '</defs>',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Wyckoff Range Test &mdash; LONG</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">Spring &rarr; rally &rarr; test higher low &rarr; entry</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<line x1="28" y1="168" x2="372" y2="168" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<line x1="28" y1="246" x2="372" y2="246" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '  <line x1="55" y1="200" x2="55" y2="224" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="205" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="88" y1="210" x2="88" y2="234" stroke="#8b9cb3" stroke-width="2"/><rect x="81" y="215" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="121" y1="198" x2="121" y2="222" stroke="#8b9cb3" stroke-width="2"/><rect x="114" y="203" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="154" y1="212" x2="154" y2="236" stroke="#8b9cb3" stroke-width="2"/><rect x="147" y="217" width="14" height="13" fill="#ef4444"/>',
  '<line x1="178" y1="268" x2="178" y2="192" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="171" y="232" width="14" height="26" fill="#94a3b8"/>',
  '<line x1="170" y1="268" x2="186" y2="268" stroke="#64748b" stroke-width="1" stroke-dasharray="2 2"/>',
  '<text x="192" y="272" fill="#94a3b8" font-size="9">Spring low</text>',
  '  <line x1="208" y1="175" x2="208" y2="200" stroke="#8b9cb3" stroke-width="2"/><rect x="201" y="180" width="14" height="14" fill="#22c55e"/>',
  '  <line x1="238" y1="148" x2="238" y2="172" stroke="#8b9cb3" stroke-width="2"/><rect x="231" y="152" width="14" height="15" fill="#22c55e"/>',
  '  <line x1="268" y1="132" x2="268" y2="155" stroke="#8b9cb3" stroke-width="2"/><rect x="261" y="136" width="14" height="14" fill="#22c55e"/>',
  '<path d="M178 210 C210,185 240,155 268,140" fill="none" stroke="#3b82f6" stroke-width="1.5" stroke-dasharray="4 3"/>',
  '<text x="220" y="148" fill="#93c5fd" font-size="9">Rally</text>',
  '<line x1="298" y1="238" x2="298" y2="262" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="291" y="243" width="14" height="14" fill="#22c55e"/>',
  '<line x1="286" y1="255" x2="310" y2="255" stroke="#22c55e" stroke-width="1" stroke-dasharray="2 2"/>',
  '<text x="314" y="258" fill="#86efac" font-size="9">Higher low</text>',
  '<rect x="38" y="72" width="72" height="32" rx="4" fill="rgba(148,163,184,0.1)" stroke="#64748b"/>',
  '<text x="74" y="92" text-anchor="middle" fill="#cbd5e1" font-size="9" font-weight="600">1. Spring</text>',
  '<rect x="118" y="72" width="72" height="32" rx="4" fill="rgba(59,130,246,0.12)" stroke="#3b82f6"/>',
  '<text x="154" y="92" text-anchor="middle" fill="#93c5fd" font-size="9" font-weight="600">2. Rally</text>',
  '<rect x="248" y="72" width="100" height="32" rx="4" fill="rgba(34,197,94,0.25)" stroke="#22c55e" stroke-width="2"/>',
  '<text x="298" y="92" text-anchor="middle" fill="#bbf7d0" font-size="9" font-weight="700">3. TIN HIEU</text>',
  '<path d="M178 200 L178 185" stroke="#64748b" stroke-width="1.5"/>',
  '<path d="M298 248 L298 235" stroke="#22c55e" stroke-width="2" marker-end="url(#wy-rt-g)"/>',
  '<line x1="280" y1="250" x2="360" y2="250" stroke="#22c55e" stroke-width="2"/><text x="362" y="254" fill="#22c55e" font-size="10">Entry</text>',
  '<line x1="280" y1="268" x2="360" y2="268" stroke="#ef4444" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="272" fill="#ef4444" font-size="10">SL</text>',
  '<line x1="280" y1="165" x2="360" y2="165" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="169" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Cach doc</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- Nen 1: spring hop le &mdash; CHUA vao lenh</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Nen 2-3: rally &gt;= rallyMinPips phia tren range low</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- Nen 4: test cham range low, low &gt; spring low</text>',
  '<text x="24" y="506" fill="#94a3b8" font-size="11">- Nen xanh xac nhan &rarr; LONG tai close test</text>',
  '<text x="24" y="530" fill="#f59e0b" font-size="11">! Conservative hon Spring/UTAD (vao muon hon)</text>',
  '</svg>',
]);

const rangeTestShort = pack([
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 620" role="img">',
  '<rect fill="#0f1419" width="400" height="620" rx="8"/>',
  '<text x="200" y="26" text-anchor="middle" fill="#f1f5f9" font-size="15" font-weight="700">Wyckoff Range Test &mdash; SHORT</text>',
  '<text x="200" y="46" text-anchor="middle" fill="#94a3b8" font-size="11">UTAD &rarr; giam &rarr; test lower high &rarr; entry</text>',
  '<rect x="12" y="58" width="376" height="340" rx="8" fill="#121a24" stroke="#2a3548"/>',
  '<line x1="28" y1="168" x2="372" y2="168" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '<line x1="28" y1="246" x2="372" y2="246" stroke="#f59e0b" stroke-width="2" stroke-dasharray="7 5"/>',
  '  <line x1="55" y1="210" x2="55" y2="234" stroke="#8b9cb3" stroke-width="2"/><rect x="48" y="215" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="88" y1="200" x2="88" y2="224" stroke="#8b9cb3" stroke-width="2"/><rect x="81" y="205" width="14" height="13" fill="#22c55e"/>',
  '  <line x1="121" y1="215" x2="121" y2="238" stroke="#8b9cb3" stroke-width="2"/><rect x="114" y="220" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="154" y1="205" x2="154" y2="228" stroke="#8b9cb3" stroke-width="2"/><rect x="147" y="210" width="14" height="13" fill="#22c55e"/>',
  '<line x1="178" y1="118" x2="178" y2="198" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="171" y="158" width="14" height="28" fill="#94a3b8"/>',
  '<line x1="170" y1="118" x2="186" y2="118" stroke="#64748b" stroke-width="1" stroke-dasharray="2 2"/>',
  '<text x="192" y="122" fill="#94a3b8" font-size="9">UTAD high</text>',
  '  <line x1="208" y1="218" x2="208" y2="242" stroke="#8b9cb3" stroke-width="2"/><rect x="201" y="223" width="14" height="13" fill="#ef4444"/>',
  '  <line x1="238" y1="248" x2="238" y2="272" stroke="#8b9cb3" stroke-width="2"/><rect x="231" y="253" width="14" height="14" fill="#ef4444"/>',
  '  <line x1="268" y1="268" x2="268" y2="292" stroke="#8b9cb3" stroke-width="2"/><rect x="261" y="273" width="14" height="14" fill="#ef4444"/>',
  '<path d="M178 175 C210,210 240,245 268,268" fill="none" stroke="#3b82f6" stroke-width="1.5" stroke-dasharray="4 3"/>',
  '<text x="220" y="248" fill="#93c5fd" font-size="9">Rally xuong</text>',
  '<line x1="298" y1="168" x2="298" y2="192" stroke="#8b9cb3" stroke-width="2"/>',
  '<rect x="291" y="173" width="14" height="14" fill="#ef4444"/>',
  '<line x1="286" y1="168" x2="310" y2="168" stroke="#ef4444" stroke-width="1" stroke-dasharray="2 2"/>',
  '<text x="314" y="172" fill="#fca5a5" font-size="9">Lower high</text>',
  '<rect x="248" y="72" width="100" height="32" rx="4" fill="rgba(239,68,68,0.2)" stroke="#ef4444" stroke-width="2"/>',
  '<text x="298" y="92" text-anchor="middle" fill="#fecaca" font-size="9" font-weight="700">TIN HIEU</text>',
  '<line x1="280" y1="186" x2="360" y2="186" stroke="#ef4444" stroke-width="2"/><text x="362" y="190" fill="#ef4444" font-size="10">Entry</text>',
  '<line x1="280" y1="168" x2="360" y2="168" stroke="#f87171" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="172" fill="#f87171" font-size="10">SL</text>',
  '<line x1="280" y1="255" x2="360" y2="255" stroke="#22c55e" stroke-width="2" stroke-dasharray="5 4"/><text x="362" y="259" fill="#22c55e" font-size="10">TP</text>',
  '<rect x="12" y="408" width="376" height="200" rx="8" fill="#151c26" stroke="#2a3548"/>',
  '<text x="24" y="432" fill="#e2e8f0" font-size="12" font-weight="600">Doi xung LONG</text>',
  '<text x="24" y="452" fill="#94a3b8" font-size="11">- UTAD arm setup, khong vao lenh</text>',
  '<text x="24" y="470" fill="#94a3b8" font-size="11">- Gia giam &gt;= rallyMinPips</text>',
  '<text x="24" y="488" fill="#94a3b8" font-size="11">- Test range high, high &lt; UTAD high &rarr; SHORT</text>',
  '</svg>',
]);

const newEntries = {
  'wyckoff-spring-utad-long': springLong,
  'wyckoff-spring-utad-short': utadShort,
  'wyckoff-range-test-long': rangeTestLong,
  'wyckoff-range-test-short': rangeTestShort,
};

let src = readFileSync(target, 'utf8');
if (src.includes('wyckoff-spring-utad-long')) {
  console.log('Wyckoff diagrams already present, skipping');
  process.exit(0);
}

const insert = Object.entries(newEntries)
  .map(([id, svg]) => `  '${id}': '${svg}',`)
  .join('\n');

src = src.replace(/',\n};\n\n\/\*\*/, `',\n${insert}\n};\n\n/**`);
writeFileSync(target, src);
console.log('Appended', Object.keys(newEntries).length, 'Wyckoff diagrams');
