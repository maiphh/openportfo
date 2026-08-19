import { TOP_STORIES } from "@/lib/mock-data";

export default function TopStories() {
  return (
    <div className="w-full">
      <h3 className="mb-5 text-2xl font-semibold text-gray-100">Top Stories</h3>
      <div className="min-h-[480px] overflow-y-auto rounded-lg border border-gray-600 bg-gray-800 p-4 xl:h-[560px]">
        <ul className="space-y-5">
          {TOP_STORIES.map((story) => (
            <li key={story.id} className="flex gap-3">
              <span
                className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
                style={{ background: story.sourceColor }}
              >
                {story.source}
              </span>
              <div className="min-w-0">
                <p className="mb-1 text-xs text-gray-500">{story.timeAgo}</p>
                <p className="text-[15px] leading-snug text-gray-200">{story.headline}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
