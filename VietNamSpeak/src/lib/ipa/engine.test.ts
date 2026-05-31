import { describe, expect, it } from "vitest";

import { convertIpaToVietnamese, explainIpa } from "./engine";

describe("convertIpaToVietnamese", () => {
  it.each([
    ["/skuːl/", "skuul"],
    ["/ɪˈnʌf/", "i-nâf"],
    ["/ˈbjuːtəfəl/", "biu-tờ-phồ"],
    ["/ˈlæŋɡwɪdʒ/", "leang-quịch"]
  ])("converts %s to %s", (ipa, expected) => {
    expect(convertIpaToVietnamese(ipa).hint).toBe(expected);
  });

  it("keeps a token-level explanation for the visualizer", () => {
    expect(explainIpa("/skuːl/")).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ ipa: "s", vietnamese: "s" }),
        expect.objectContaining({ ipa: "k", vietnamese: "k" }),
        expect.objectContaining({ ipa: "uː", vietnamese: "uu" }),
        expect.objectContaining({ ipa: "l", vietnamese: "l" })
      ])
    );
  });
});
