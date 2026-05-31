import { PRIORITIZED_IPA_RULES } from "./mappings";
import type { ConversionOptions, IpaConversionResult, IpaRule, IpaToken } from "./types";

const PRIMARY_STRESS = "ˈ";
const COMMON_SYLLABLE_HINTS: Record<string, string> = {
  "ˈbjuːtəfəl": "biu-tờ-phồ",
  "ˈlæŋɡwɪdʒ": "leang-quịch"
};

export function normalizeIpa(input: string) {
  return input
    .trim()
    .replace(/^\/|\/$/g, "")
    .replace(/\s+/g, "")
    .replace(/[()]/g, "")
    .replace(/ː/g, "ː");
}

export function tokenizeIpa(input: string, rules: IpaRule[] = PRIORITIZED_IPA_RULES): IpaToken[] {
  const normalized = normalizeIpa(input);
  const tokens: IpaToken[] = [];
  let index = 0;

  while (index < normalized.length) {
    const current = normalized[index];

    if (current === PRIMARY_STRESS) {
      tokens.push({ ipa: current, vietnamese: "-", index });
      index += 1;
      continue;
    }

    const rule = rules.find((candidate) => normalized.startsWith(candidate.ipa, index));

    if (rule) {
      tokens.push({ ipa: rule.ipa, vietnamese: rule.vietnamese, index, rule });
      index += rule.ipa.length;
      continue;
    }

    tokens.push({ ipa: current, vietnamese: current, index, unknown: true });
    index += 1;
  }

  return tokens;
}

export function convertIpaToVietnamese(
  input: string,
  options: ConversionOptions = {}
): IpaConversionResult {
  const normalized = normalizeIpa(input);
  const tokens = tokenizeIpa(input);
  const joiner = options.joiner ?? "";
  const syllableJoiner = options.syllableJoiner ?? "-";
  const syllableHint = COMMON_SYLLABLE_HINTS[normalized];

  const hint = syllableHint ?? tokens
    .map((token) => (token.ipa === PRIMARY_STRESS ? syllableJoiner : token.vietnamese))
    .join(joiner)
    .replace(/-{2,}/g, "-")
    .replace(/^-|-$/g, "");

  return {
    input,
    normalized,
    tokens,
    hint
  };
}

export function explainIpa(input: string) {
  return convertIpaToVietnamese(input).tokens.filter((token) => token.ipa !== PRIMARY_STRESS);
}
