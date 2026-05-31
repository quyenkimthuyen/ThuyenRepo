export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  public: {
    Tables: {
      words: {
        Row: {
          id: string;
          word: string;
          ipa: string;
          vn_pronunciation: string;
          meaning_vi: string;
          example_en: string;
          example_vi: string;
          audio_url: string | null;
          topic: string;
          level: string;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<Database["public"]["Tables"]["words"]["Row"], "created_at" | "updated_at"> & {
          created_at?: string;
          updated_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["words"]["Insert"]>;
      };
      profiles: {
        Row: {
          id: string;
          display_name: string | null;
          xp: number;
          coins: number;
          streak_count: number;
          current_level: number;
          created_at: string;
          updated_at: string;
        };
        Insert: Partial<Database["public"]["Tables"]["profiles"]["Row"]> & { id: string };
        Update: Partial<Database["public"]["Tables"]["profiles"]["Row"]>;
      };
    };
  };
};
