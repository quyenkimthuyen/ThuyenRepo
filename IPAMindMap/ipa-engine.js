(function () {
  "use strict";

  const symbolMap = {
    "iː": "ii",
    "ɪ": "i",
    "e": "e",
    "æ": "ea",
    "ɑː": "aa",
    "ɔː": "oo",
    "uː": "uu",
    "ʌ": "â",
    "ə": "ơ",
    "ʃ": "sh",
    "tʃ": "ch",
    "dʒ": "j",
    "ŋ": "ng",
    "θ": "th",
    "ð": "dh",
    "ɡ": "g",
    "j": "i",
    "r": "r",
    "l": "l",
    "w": "u",
    "aʊ": "au",
    "oʊ": "âu",
    "er": "ơ",
    "ər": "ờ"
  };

  const exactHints = {
    "/skuːl/": "skuul",
    "/ɪˈnʌf/": "i-nâf",
    "/ˈbjuːtəfəl/": "biu-tờ-phồ",
    "/ˈlæŋɡwɪdʒ/": "leang-quịch"
  };

  const orderedSymbols = Object.keys(symbolMap).sort((a, b) => b.length - a.length);

  function stripIpaMarks(ipa) {
    return ipa.replace(/[\/\[\]]/g, "").trim();
  }

  function normalizeHint(hint) {
    return hint
      .replace(/ˈ|ˌ/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function convert(ipa) {
    if (!ipa || typeof ipa !== "string") {
      return "";
    }

    if (exactHints[ipa]) {
      return exactHints[ipa];
    }

    let source = stripIpaMarks(ipa);
    let result = "";

    while (source.length > 0) {
      const matched = orderedSymbols.find((symbol) => source.startsWith(symbol));

      if (matched) {
        result += symbolMap[matched];
        source = source.slice(matched.length);
        continue;
      }

      const char = source[0];
      if (/^[a-zpbsdtkgfvzmn h]$/i.test(char)) {
        result += char;
      } else if (char === "ˈ" || char === "ˌ" || char === ".") {
        result += "-";
      }

      source = source.slice(1);
    }

    return normalizeHint(result);
  }

  function getMapping() {
    return { ...symbolMap };
  }

  window.IPAEngine = {
    convert,
    getMapping
  };
})();
