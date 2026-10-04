import { DownloadSimple, Plus } from "@phosphor-icons/react";
import { downloadUrl } from "../api";
import Button from "./Button";
import "./VideoResult.css";

function timecode(totalSeconds) {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function VideoResult({ video, onQueue }) {
  if (!video) return null;

  const sourceUrl = video.format_id.startsWith("http")
    ? video.format_id
    : `https://www.tiktok.com/@x/video/${video.id}`;
  const dlUrl = downloadUrl(sourceUrl, video.format_id);

  return (
    <article className="result panel">
      <div className="result-body">
        <div className="result-thumb">
          {video.thumbnail && <img src={video.thumbnail} alt="" loading="lazy" />}
        </div>

        <div className="result-meta">
          <div className="result-tags">
            <span className="chip">MP4</span>
            {video.duration > 0 && <span className="chip">{timecode(video.duration)}</span>}
          </div>
          <h2 className="result-author">{video.author || "TikTok video"}</h2>
          <p className="result-caption">{video.caption || "No description"}</p>
          <p className="result-id mono">{video.id}</p>
        </div>

        <div className="result-actions">
          <Button as="a" variant="primary" href={dlUrl}>
            <DownloadSimple size={16} weight="bold" />
            <span>Download</span>
          </Button>
          <Button variant="secondary" onClick={() => onQueue(video.format_id)}>
            <Plus size={16} weight="bold" />
            <span>Queue</span>
          </Button>
        </div>
      </div>
    </article>
  );
}
