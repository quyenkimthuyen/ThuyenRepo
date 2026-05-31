import { IpaVisualizer } from "@/components/ipa-visualizer";
import { IpaSoundTable } from "@/components/ipa-sound-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { groupIpaSounds } from "@/data/ipa-sounds";

export default function IpaCenterPage() {
  const groups = groupIpaSounds();
  const totalSounds = groups.reduce((sum, group) => sum + group.sounds.length, 0);

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-br from-emerald-500 to-blue-600 p-6 text-white sm:p-8">
        <Badge className="bg-white/20 text-white">Bảng âm IPA cho người Việt</Badge>
        <h1 className="mt-3 max-w-3xl text-4xl font-black tracking-tight sm:text-5xl">
          Học IPA bằng cách “đánh vần âm”, không học ký hiệu khô khan.
        </h1>
        <p className="mt-3 max-w-3xl text-lg text-emerald-50">
          Có {totalSounds} âm/cụm âm quan trọng, chia theo nhóm dễ học. Mỗi âm có gợi ý kiểu
          Việt, ví dụ, mẹo đặt miệng và lỗi cần tránh.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["1", "Nghe âm", "Ấn Listen để nghe ví dụ bằng giọng máy."],
          ["2", "Đọc gợi ý Việt", "Dùng gợi ý để nhớ vị trí miệng."],
          ["3", "Tránh lỗi Việt hóa", "Không thêm âm 'ờ', không đọc theo mặt chữ."]
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

      <IpaSoundTable groups={groups} />

      {groups.map((group) => (
        <section key={group.group} className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <Badge>{group.sounds.length} âm</Badge>
              <h2 className="mt-2 text-3xl font-black tracking-tight">{group.label}</h2>
            </div>
            <p className="max-w-xl text-sm text-[var(--muted-foreground)]">
              {group.group === "short-vowel" &&
                "Nền tảng quan trọng nhất: người Việt hay đọc dài hoặc đọc theo chữ viết."}
              {group.group === "long-vowel" &&
                "Các âm cần kéo dài có kiểm soát, đặc biệt là /iː/ và /uː/."}
              {group.group === "diphthong" &&
                "Nguyên âm đôi là âm trượt: miệng chuyển từ âm đầu sang âm cuối."}
              {group.group === "consonant" &&
                "Tập phụ âm đầu và cuối thật gọn, không thêm âm 'ờ'."}
              {group.group === "hard-for-vietnamese" &&
                "Các âm dễ sai nhất với người Việt: th, sh, j, r, v, z, ng cuối."}
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {group.sounds.map((sound) => (
              <Card key={sound.id} className="space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <Badge>{sound.level}</Badge>
                    <CardTitle className="mt-3 font-mono text-4xl">{sound.symbol}</CardTitle>
                    <p className="text-lg font-black text-blue-600 dark:text-blue-300">
                      {sound.vietnameseHint}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl bg-emerald-50 p-3 text-sm text-emerald-950 dark:bg-emerald-950 dark:text-emerald-50">
                  <b>Mẹo miệng:</b> {sound.mouthTip}
                </div>
                <div className="rounded-2xl bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950 dark:text-amber-50">
                  <b>Tránh:</b> {sound.avoid}
                </div>

                <div className="space-y-2">
                  {sound.examples.map((example) => (
                    <div
                      key={example.word}
                      className="flex justify-between gap-3 rounded-2xl bg-[var(--background)] p-3"
                    >
                      <span className="font-bold">{example.word}</span>
                      <span className="text-right font-black text-blue-600 dark:text-blue-300">
                        {example.hint}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <Button variant="secondary" size="sm">
                    Listen
                  </Button>
                  <Button variant="secondary" size="sm">
                    Practice
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </section>
      ))}

      <IpaVisualizer ipa="/ˈbjuːtəfəl/" />
    </div>
  );
}
