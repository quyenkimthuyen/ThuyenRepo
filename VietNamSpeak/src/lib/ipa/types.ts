export type IpaRule = {
  ipa: string;
  vietnamese: string;
  priority: number;
  category: "vowel" | "consonant" | "diphthong" | "marker" | "cluster";
  description?: string;
};

export type IpaToken = {
  ipa: string;
  vietnamese: string;
  index: number;
  rule?: IpaRule;
  unknown?: boolean;
};

export type IpaConversionResult = {
  input: string;
  normalized: string;
  tokens: IpaToken[];
  hint: string;
};

export type ConversionOptions = {
  joiner?: string;
  syllableJoiner?: string;
};
