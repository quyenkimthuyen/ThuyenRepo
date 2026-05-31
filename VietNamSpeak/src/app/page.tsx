import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { WORDS, getTopics } from "@/data/words";

export default function DashboardPage() {
  const todayWords = WORDS.slice(0, 9);
  const topics = getTopics().slice(0, 10);

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-br from-blue-600 to-indigo-700 p-6 text-white shadow-xl shadow-blue-500/20 sm:p-8">
        <div className="max-w-3xl space-y-5">
          <Badge className="w-fit bg-white/20 text-white">Dễ học cho người mới bắt đầu</Badge>
          <h1 className="text-4xl font-black tracking-tight sm:text-6xl">
            Nhìn từ tiếng Anh, biết cách đọc ngay.
          </h1>
          <p className="text-lg text-blue-50 sm:text-xl">
            App biến IPA thành gợi ý phát âm quen thuộc với người Việt: <b>school</b> {"->"}{" "}
            <b>skuul</b>. Bạn chỉ cần nghe, nhại lại, rồi luyện mỗi ngày.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" variant="success">
              <Link href="/learn/see">Bắt đầu học 1 từ</Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <Link href="/learn">Xem kho từ</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["1", "Nhìn từ", "Đừng đọc theo mặt chữ tiếng Anh."],
          ["2", "Đọc gợi ý Việt", "Dùng 'skuul', 'biu-tờ-phồ', 'i-nâf' để hình dung âm."],
          ["3", "Nghe và nói", "Nghe chậm, ghi âm, nghe lại, sửa lỗi từng âm."]
        ].map(([step, title, detail]) => (
          <Card key={step} className="space-y-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-lg font-black text-white">
              {step}
            </span>
            <CardTitle>{title}</CardTitle>
            <p className="text-[var(--muted-foreground)]">{detail}</p>
          </Card>
        ))}
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <Card className="space-y-4">
          <CardTitle>Bài học hôm nay</CardTitle>
          <p className="text-[var(--muted-foreground)]">
            Học ít nhưng đúng: 9 từ phổ biến, nghe mỗi từ 3 lần, tự ghi âm 1 lần.
          </p>
          <Progress value={30} />
          <div className="flex flex-wrap gap-2">
            {topics.map((topic) => (
              <span key={topic} className="rounded-full bg-[var(--muted)] px-3 py-1 text-xs font-bold">
                {topic}
              </span>
            ))}
          </div>
          <Button asChild className="w-full">
            <Link href={`/learn/${todayWords[0].id}`}>Học từ đầu tiên</Link>
          </Button>
        </Card>

        <div className="grid gap-3 sm:grid-cols-2">
          {todayWords.map((word) => (
          <Card key={word.id} className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <Badge>{word.topic}</Badge>
                <span className="text-xs font-bold text-[var(--muted-foreground)]">{word.level}</span>
              </div>
              <CardTitle>{word.word}</CardTitle>
              <p className="font-mono text-sm">{word.ipa}</p>
              <p className="text-2xl font-black text-blue-600 dark:text-blue-300">
                {word.vnPronunciation}
              </p>
              <p className="text-sm text-[var(--muted-foreground)]">{word.meaningVi}</p>
            <Button asChild variant="secondary" className="w-full">
                <Link href={`/learn/${word.id}`}>Học từ này</Link>
            </Button>
          </Card>
        ))}
        </div>
      </section>
    </div>
  );
}
