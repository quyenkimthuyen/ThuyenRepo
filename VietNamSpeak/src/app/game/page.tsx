import { IpaAdventure } from "@/components/ipa-adventure";
import { Badge } from "@/components/ui/badge";

export default function GamePage() {
  return (
    <div className="space-y-6">
      <section>
        <Badge>Ôn vui</Badge>
        <h1 className="mt-3 text-4xl font-black tracking-tight">IPA Adventure</h1>
        <p className="mt-2 max-w-2xl text-[var(--muted-foreground)]">
          Luyện nhanh nhiều dạng câu hỏi: IPA, cách đọc kiểu Việt, nghĩa tiếng Việt, từ tiếng Anh
          và lỗi phát âm thường gặp.
        </p>
      </section>
      <IpaAdventure />
    </div>
  );
}
